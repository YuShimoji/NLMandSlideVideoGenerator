#!/usr/bin/env python3
"""
YouTube アップローダー (SP-038 Phase 3)

YouTube Data API v3 を使用した動画アップロード・管理。
認証情報がない場合はモックモードにフォールバックする。
"""
import asyncio
import json
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Optional, Dict, Any, Union, Callable
from dataclasses import dataclass

from core.utils.logger import logger
from core.exceptions import UploadError, QuotaExceededError, APIAuthenticationError


@dataclass
class UploadResult:
    """アップロード結果"""
    video_id: str
    video_url: str
    upload_status: str
    processing_status: str
    privacy_status: str
    uploaded_at: Optional[datetime] = None


@dataclass
class UploadMetadata:
    """YouTubeアップロード用メタデータ"""
    title: str
    description: str
    tags: list
    category_id: str
    language: str
    privacy_status: str = "private"
    thumbnail_path: Optional[Path] = None
    publish_at: Optional[str] = None  # ISO 8601 (例: "2026-03-25T18:00:00Z")


def _normalize_metadata(metadata: Union[UploadMetadata, Dict[str, Any]]) -> UploadMetadata:
    """dict を UploadMetadata に正規化する"""
    if isinstance(metadata, UploadMetadata):
        return metadata
    return UploadMetadata(
        title=metadata.get("title", "Untitled"),
        description=metadata.get("description", ""),
        tags=list(metadata.get("tags", [])),
        category_id=str(metadata.get("category_id", "27")),
        language=str(metadata.get("language", "ja")),
        privacy_status=str(metadata.get("privacy_status", "private")),
        thumbnail_path=Path(metadata["thumbnail_path"]) if metadata.get("thumbnail_path") else None,
        publish_at=metadata.get("publish_at") or metadata.get("publishAt"),
    )


def _normalize_video_path(video: Union[Path, Any]) -> Path:
    """video 引数を Path に正規化する"""
    if isinstance(video, Path):
        return video
    if hasattr(video, "file_path"):
        return Path(getattr(video, "file_path"))
    raise TypeError("video には Path か file_path 属性を持つオブジェクトを渡してください")


class YouTubeUploader:
    """YouTube アップローダー

    認証情報が有効な場合は YouTube Data API v3 経由でアップロードし、
    認証情報がない場合はモックモードで動作する。
    """

    UPLOAD_QUOTA_COST = 1600  # 動画アップロード1回あたりのクォータコスト

    def __init__(self, credentials_path: Optional[Path] = None):
        self.credentials_path = credentials_path
        self.youtube_service = None
        self._mock_mode = False
        self.upload_quota_used = 0
        self.max_daily_quota = 10000  # YouTube API v3 の1日あたりのクォータ制限

    @property
    def is_mock_mode(self) -> bool:
        return self._mock_mode

    async def authenticate(self) -> bool:
        """YouTube API認証。GoogleAuthHelper を使用してサービスを構築する。"""
        try:
            logger.info("YouTube API認証を開始")

            # GoogleAuthHelper で認証情報を取得
            creds = self._get_credentials()

            if creds is None:
                logger.warning("OAuth認証情報がありません。モックモードで動作します")
                self._mock_mode = True
                return True

            # YouTube Data API v3 サービスを構築
            try:
                from googleapiclient.discovery import build
                self.youtube_service = build(
                    "youtube", "v3",
                    credentials=creds,
                    cache_discovery=False,
                )
                self._mock_mode = False
                logger.info("YouTube API認証成功 (実APIモード)")
                return True
            except ImportError:
                logger.warning("google-api-python-client がインストールされていません。モックモードで動作します")
                self._mock_mode = True
                return True

        except (AttributeError, TypeError, OSError, ValueError, RuntimeError) as e:
            logger.error(f"YouTube API認証失敗: {e}")
            return False

    def _get_credentials(self):
        """GoogleAuthHelper 経由で認証情報を取得する"""
        try:
            from gapi.google_auth import GoogleAuthHelper
            from config.settings import settings

            helper = GoogleAuthHelper(
                client_secrets_file=self.credentials_path,
                scopes=[
                    "https://www.googleapis.com/auth/youtube.upload",
                    "https://www.googleapis.com/auth/youtube.readonly",
                ],
            )
            return helper.get_credentials()
        except ImportError:
            logger.warning("gapi.google_auth が利用できません")
            return None
        except (AttributeError, TypeError, OSError, ValueError, RuntimeError) as e:
            logger.warning(f"認証情報の取得に失敗: {e}")
            return None

    async def upload_video(
        self,
        video: Union[Path, Any],
        metadata: Union[UploadMetadata, Dict[str, Any]],
        thumbnail_path: Optional[Path] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
        verify_quality: bool = True,
    ) -> UploadResult:
        """動画をアップロードする。

        Args:
            video: 動画ファイルの Path またはファイルパス属性を持つオブジェクト
            metadata: アップロード用メタデータ (UploadMetadata or dict)
            thumbnail_path: サムネイル画像パス (任意)
            progress_callback: アップロード進捗コールバック (0.0~1.0)
            verify_quality: True の場合、アップロード前に MP4 品質を検証する (SP-039)
        """
        try:
            video_path = _normalize_video_path(video)
            meta = _normalize_metadata(metadata)

            logger.info(f"動画アップロード開始: {video_path.name}")

            # クォータチェック
            if self.upload_quota_used >= self.max_daily_quota:
                raise QuotaExceededError("YouTube APIの1日あたりのクォータ制限に達しました")

            # ファイル存在チェック
            if not video_path.exists():
                raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")

            # MP4 品質検証 (SP-039 Phase 2)
            if verify_quality:
                quality_result = self._verify_mp4_quality(video_path)
                if quality_result is not None and not quality_result.passed:
                    failures = quality_result.critical_failures
                    msg = "; ".join(f"{c.name}: {c.actual} (expected {c.expected})" for c in failures)
                    raise UploadError(f"MP4品質検証失敗 (CRITICAL): {msg}")

            # ファイルサイズチェック（YouTube制限: 256GB）
            file_size = video_path.stat().st_size
            max_size = 256 * 1024 * 1024 * 1024  # 256GB
            if file_size > max_size:
                raise UploadError(f"ファイルサイズが制限を超えています: {file_size / 1024 / 1024 / 1024:.1f}GB")

            # メタデータ検証
            self._validate_metadata(meta)

            # アップロード実行
            if self._mock_mode or self.youtube_service is None:
                upload_result = await self._mock_upload(video_path, meta, progress_callback)
            else:
                upload_result = await self._api_upload(video_path, meta, progress_callback)

            # クォータ使用量を更新
            self.upload_quota_used += self.UPLOAD_QUOTA_COST

            # サムネイルアップロード
            thumb = thumbnail_path or meta.thumbnail_path
            if thumb and thumb.exists():
                await self._upload_thumbnail(upload_result.video_id, thumb)

            logger.info(f"動画アップロード完了: {upload_result.video_id}")
            return upload_result

        except (UploadError, QuotaExceededError):
            raise
        except FileNotFoundError as e:
            raise UploadError(str(e))
        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"動画アップロード失敗: {e}")
            raise UploadError(str(e))

    def _validate_metadata(self, metadata: UploadMetadata) -> None:
        """メタデータを検証する (同期)"""
        if len(metadata.title) > 100:
            raise ValueError(f"タイトルが長すぎます: {len(metadata.title)}文字 (最大100文字)")

        if len(metadata.description) > 5000:
            raise ValueError(f"説明文が長すぎます: {len(metadata.description)}文字 (最大5000文字)")

        tags_text = ",".join(metadata.tags)
        if len(tags_text) > 500:
            raise ValueError(f"タグが長すぎます: {len(tags_text)}文字 (最大500文字)")

        valid_privacy = {"private", "public", "unlisted"}
        if metadata.privacy_status not in valid_privacy:
            raise ValueError(f"無効なプライバシー設定: {metadata.privacy_status}")

    def _verify_mp4_quality(self, video_path: Path):
        """MP4 品質を検証する (SP-039 Phase 2)。

        FFprobe がインストールされていない場合は None を返し、検証をスキップする。
        """
        try:
            from core.utils.mp4_checker import check_mp4
            result = check_mp4(video_path)
            if result.passed:
                logger.info(f"MP4品質検証: PASS ({len(result.checks)} checks)")
            else:
                critical = result.critical_failures
                warnings = result.warnings
                logger.warning(
                    f"MP4品質検証: FAIL — {len(critical)} critical, {len(warnings)} warnings"
                )
            return result
        except FileNotFoundError:
            logger.info("FFprobe が見つかりません。MP4品質検証をスキップします")
            return None
        except (RuntimeError, OSError, ValueError) as e:
            logger.warning(f"MP4品質検証でエラー: {e}")
            return None

    # ------------------------------------------------------------------ #
    #  実API アップロード (resumable upload)
    # ------------------------------------------------------------------ #

    async def _api_upload(
        self,
        video_path: Path,
        metadata: UploadMetadata,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> UploadResult:
        """YouTube Data API v3 の resumable upload で動画をアップロードする"""
        try:
            from googleapiclient.http import MediaFileUpload
        except ImportError as e:
            raise UploadError(f"google-api-python-client が必要です: {e}")

        # スケジュール投稿: publishAt 指定時は privacyStatus を "private" に強制
        # YouTube Data API v3 は publishAt + private の組み合わせでスケジュール公開を実現する
        privacy = metadata.privacy_status
        status_body: Dict[str, Any] = {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        }
        if metadata.publish_at:
            status_body["publishAt"] = metadata.publish_at
            if privacy != "private":
                logger.warning(
                    f"スケジュール投稿には privacyStatus=private が必要です。"
                    f"'{privacy}' を 'private' に変更します"
                )
                status_body["privacyStatus"] = "private"

        body = {
            "snippet": {
                "title": metadata.title,
                "description": metadata.description,
                "tags": metadata.tags,
                "categoryId": metadata.category_id,
                "defaultLanguage": metadata.language,
                "defaultAudioLanguage": metadata.language,
            },
            "status": status_body,
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/*",
            resumable=True,
            chunksize=50 * 1024 * 1024,  # 50MB chunks
        )

        request = self.youtube_service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        # resumable upload をイベントループをブロックせず実行
        loop = asyncio.get_event_loop()
        response = None

        while response is None:
            status, response = await loop.run_in_executor(
                None,
                partial(request.next_chunk),
            )
            if status is not None:
                progress = status.progress()
                logger.info(f"アップロード進行状況: {progress * 100:.1f}%")
                if progress_callback:
                    progress_callback(progress)

        video_id = response["id"]
        privacy = response.get("status", {}).get("privacyStatus", metadata.privacy_status)
        upload_status = response.get("status", {}).get("uploadStatus", "uploaded")

        return UploadResult(
            video_id=video_id,
            video_url=f"https://www.youtube.com/watch?v={video_id}",
            upload_status=upload_status,
            processing_status="processing",
            privacy_status=privacy,
            uploaded_at=datetime.now(),
        )

    # ------------------------------------------------------------------ #
    #  モック アップロード (認証情報なし時のフォールバック)
    # ------------------------------------------------------------------ #

    async def _mock_upload(
        self,
        video_path: Path,
        metadata: UploadMetadata,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> UploadResult:
        """モックアップロード — 実際の API 呼び出しなし"""
        logger.info("[MOCK] アップロード準備中...")

        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        steps = max(1, min(int(file_size_mb / 10), 5))

        for i in range(steps):
            progress = (i + 1) / steps
            logger.info(f"[MOCK] アップロード進行状況: {progress * 100:.1f}%")
            if progress_callback:
                progress_callback(progress)
            await asyncio.sleep(0.1)

        video_id = f"mock_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        privacy = metadata.privacy_status
        if metadata.publish_at:
            logger.info(f"[MOCK] スケジュール投稿: {metadata.publish_at}")
            privacy = "private"  # スケジュール投稿は private 必須

        return UploadResult(
            video_id=video_id,
            video_url=f"https://www.youtube.com/watch?v={video_id}",
            upload_status="uploaded",
            processing_status="processing",
            privacy_status=privacy,
            uploaded_at=datetime.now(),
        )

    # ------------------------------------------------------------------ #
    #  サムネイル
    # ------------------------------------------------------------------ #

    async def _upload_thumbnail(self, video_id: str, thumbnail_path: Path) -> bool:
        """サムネイルをアップロードする"""
        try:
            logger.info(f"サムネイルアップロード: {thumbnail_path.name}")

            file_size = thumbnail_path.stat().st_size
            max_thumbnail_size = 2 * 1024 * 1024  # 2MB
            if file_size > max_thumbnail_size:
                logger.warning(f"サムネイルサイズが大きすぎます: {file_size / 1024 / 1024:.1f}MB")
                return False

            if self._mock_mode or self.youtube_service is None:
                logger.info("[MOCK] サムネイルアップロード完了")
                return True

            from googleapiclient.http import MediaFileUpload
            media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.youtube_service.thumbnails().set(
                    videoId=video_id,
                    media_body=media,
                ).execute(),
            )

            logger.info("サムネイルアップロード完了")
            return True

        except (AttributeError, TypeError, OSError, ValueError, RuntimeError) as e:
            logger.error(f"サムネイルアップロード失敗: {e}")
            return False

    # ------------------------------------------------------------------ #
    #  ステータス・メタデータ更新・削除
    # ------------------------------------------------------------------ #

    async def get_upload_status(self, video_id: str) -> Dict[str, Any]:
        """アップロード・処理状況を取得する"""
        try:
            logger.info(f"アップロード状況確認: {video_id}")

            if self._mock_mode or self.youtube_service is None:
                return {
                    "video_id": video_id,
                    "upload_status": "uploaded",
                    "processing_status": "succeeded",
                    "privacy_status": "private",
                    "failure_reason": None,
                    "rejection_reason": None,
                }

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.youtube_service.videos().list(
                    part="status,processingDetails",
                    id=video_id,
                ).execute(),
            )

            items = response.get("items", [])
            if not items:
                raise UploadError(f"動画が見つかりません: {video_id}")

            item = items[0]
            status = item.get("status", {})
            processing = item.get("processingDetails", {})

            return {
                "video_id": video_id,
                "upload_status": status.get("uploadStatus"),
                "processing_status": processing.get("processingStatus"),
                "privacy_status": status.get("privacyStatus"),
                "failure_reason": status.get("failureReason"),
                "rejection_reason": status.get("rejectionReason"),
            }

        except UploadError:
            raise
        except (TypeError, ValueError, OSError, AttributeError, RuntimeError) as e:
            logger.error(f"アップロード状況取得失敗: {e}")
            raise UploadError(str(e))

    async def update_video_metadata(
        self,
        video_id: str,
        metadata: Union[UploadMetadata, Dict[str, Any]],
    ) -> bool:
        """動画メタデータを更新する"""
        try:
            meta = _normalize_metadata(metadata)
            logger.info(f"メタデータ更新: {video_id}")
            self._validate_metadata(meta)

            if self._mock_mode or self.youtube_service is None:
                logger.info("[MOCK] メタデータ更新完了")
                return True

            body = {
                "id": video_id,
                "snippet": {
                    "title": meta.title,
                    "description": meta.description,
                    "tags": meta.tags,
                    "categoryId": meta.category_id,
                },
                "status": {
                    "privacyStatus": meta.privacy_status,
                },
            }

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.youtube_service.videos().update(
                    part="snippet,status",
                    body=body,
                ).execute(),
            )

            logger.info("メタデータ更新完了")
            return True

        except (TypeError, ValueError, OSError, AttributeError, RuntimeError) as e:
            logger.error(f"メタデータ更新失敗: {e}")
            return False

    async def delete_video(self, video_id: str) -> bool:
        """動画を削除する"""
        try:
            logger.info(f"動画削除: {video_id}")

            if self._mock_mode or self.youtube_service is None:
                logger.info("[MOCK] 動画削除完了")
                return True

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.youtube_service.videos().delete(id=video_id).execute(),
            )

            logger.info("動画削除完了")
            return True

        except (TypeError, ValueError, OSError, AttributeError, RuntimeError) as e:
            logger.error(f"動画削除失敗: {e}")
            return False

    async def get_channel_info(self) -> Dict[str, Any]:
        """チャンネル情報を取得する"""
        try:
            logger.info("チャンネル情報取得")

            if self._mock_mode or self.youtube_service is None:
                return {
                    "channel_id": "UCmock_channel_id",
                    "title": "Mock Channel",
                    "description": "",
                    "subscriber_count": 0,
                    "video_count": 0,
                    "view_count": 0,
                }

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.youtube_service.channels().list(
                    part="snippet,statistics",
                    mine=True,
                ).execute(),
            )

            items = response.get("items", [])
            if not items:
                raise UploadError("チャンネル情報が見つかりません")

            ch = items[0]
            snippet = ch.get("snippet", {})
            stats = ch.get("statistics", {})

            return {
                "channel_id": ch["id"],
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "subscriber_count": int(stats.get("subscriberCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "view_count": int(stats.get("viewCount", 0)),
            }

        except UploadError:
            raise
        except (TypeError, ValueError, OSError, AttributeError, RuntimeError) as e:
            logger.error(f"チャンネル情報取得失敗: {e}")
            raise UploadError(str(e))

    def get_quota_usage(self) -> Dict[str, int]:
        """クォータ使用状況を取得する"""
        return {
            "used": self.upload_quota_used,
            "limit": self.max_daily_quota,
            "remaining": self.max_daily_quota - self.upload_quota_used,
        }

    async def batch_upload(
        self,
        video_metadata_pairs: list,
        max_concurrent: int = 3,
    ) -> Dict[str, Any]:
        """複数動画の一括アップロード"""
        try:
            logger.info(f"一括アップロード開始: {len(video_metadata_pairs)}件")

            semaphore = asyncio.Semaphore(max_concurrent)

            async def upload_single(video_path, metadata):
                async with semaphore:
                    return await self.upload_video(video_path, metadata)

            tasks = [
                upload_single(video_path, metadata)
                for video_path, metadata in video_metadata_pairs
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful_uploads = []
            failed_uploads = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_uploads.append({
                        "index": i,
                        "video_path": str(video_metadata_pairs[i][0]),
                        "error": str(result),
                    })
                else:
                    successful_uploads.append(result)

            logger.info(f"一括アップロード完了: 成功{len(successful_uploads)}件、失敗{len(failed_uploads)}件")

            return {
                "successful": successful_uploads,
                "failed": failed_uploads,
                "total": len(video_metadata_pairs),
            }

        except (TypeError, ValueError, OSError, AttributeError, RuntimeError) as e:
            logger.error(f"一括アップロード失敗: {e}")
            raise UploadError(str(e))


def load_metadata_from_json(metadata_path: Path) -> UploadMetadata:
    """metadata.json から UploadMetadata を生成する (CLI 用ヘルパー)"""
    with open(metadata_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _normalize_metadata(data)
