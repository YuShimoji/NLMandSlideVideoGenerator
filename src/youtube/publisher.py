"""YouTube公開オーケストレーター (SP-038 Phase 7 統合)

Phase 7 の全ステップを一気通貫で実行する:
  MP4品質検証 → メタデータ読み込み/生成 → アップロード → 結果永続化

トピックディレクトリ構造 (SP-050) に準拠:
  data/topics/{topic_id}/
    ├── output_csv/metadata.json
    ├── final/video.mp4
    └── publish_result.json   ← 本モジュールが生成
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.utils.logger import logger
from core.utils.mp4_checker import MP4CheckResult, check_mp4

from .metadata_generator import MetadataGenerator
from .uploader import UploadResult, YouTubeUploader


@dataclass
class PublishResult:
    """Phase 7 公開結果"""

    video_id: str
    video_url: str
    upload_status: str
    privacy_status: str
    quality_passed: bool
    quality_warnings: List[str]
    metadata_source: str  # "auto" | "file" | "manual"
    topic_dir: Optional[str] = None
    published_at: Optional[str] = None
    result_file: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PublishOptions:
    """公開オプション"""

    video_path: Path
    privacy: str = "private"
    metadata_path: Optional[Path] = None
    thumbnail_path: Optional[Path] = None
    topic_dir: Optional[Path] = None
    credentials_path: Optional[Path] = None
    verify_quality: bool = True
    save_result: bool = True
    schedule: Optional[str] = None  # ISO 8601 (例: "2026-03-25T18:00:00Z")
    progress_callback: Optional[Callable[[str, float], None]] = None


class YouTubePublisher:
    """Phase 7 一気通貫オーケストレーター

    Usage:
        publisher = YouTubePublisher()
        result = await publisher.publish(PublishOptions(
            video_path=Path("final/video.mp4"),
            topic_dir=Path("data/topics/my_topic"),
        ))
    """

    def __init__(self, credentials_path: Optional[Path] = None) -> None:
        self.uploader = YouTubeUploader(credentials_path=credentials_path)
        self.metadata_generator = MetadataGenerator()

    async def publish(self, options: PublishOptions) -> PublishResult:
        """Phase 7 全ステップを実行する。

        1. MP4品質検証
        2. メタデータ読み込み (自動検出 or 指定パス)
        3. サムネイル検出
        4. YouTubeアップロード
        5. 結果永続化
        """
        self._report_progress(options, "phase7_start", 0.0)

        # --- Step 1: MP4 品質検証 ---
        quality_result = self._verify_quality(options)
        if not quality_result.passed and quality_result.critical_failures:
            failures = [f.message or f.name for f in quality_result.critical_failures]
            return PublishResult(
                video_id="",
                video_url="",
                upload_status="quality_failed",
                privacy_status=options.privacy,
                quality_passed=False,
                quality_warnings=failures,
                metadata_source="none",
                topic_dir=str(options.topic_dir) if options.topic_dir else None,
                error=f"MP4品質検証で致命的エラー: {'; '.join(failures)}",
            )
        warnings = [
            w.message or w.name for w in quality_result.warnings
        ] if quality_result.warnings else []
        self._report_progress(options, "quality_done", 0.2)

        # --- Step 2: メタデータ読み込み ---
        metadata, metadata_source = self._load_metadata(options)
        if metadata is None:
            return PublishResult(
                video_id="",
                video_url="",
                upload_status="metadata_missing",
                privacy_status=options.privacy,
                quality_passed=quality_result.passed,
                quality_warnings=warnings,
                metadata_source="none",
                topic_dir=str(options.topic_dir) if options.topic_dir else None,
                error="メタデータが見つかりません。--metadata で指定するか、topic_dir/output_csv/metadata.json を配置してください",
            )
        metadata["privacy_status"] = options.privacy
        if options.schedule:
            metadata["publish_at"] = options.schedule
            logger.info(f"スケジュール投稿: {options.schedule}")
        self._report_progress(options, "metadata_loaded", 0.3)

        # --- Step 3: サムネイル検出 ---
        thumbnail = self._resolve_thumbnail(options)
        self._report_progress(options, "thumbnail_resolved", 0.4)

        # --- Step 4: YouTube アップロード ---
        upload_result = await self._upload(options, metadata, thumbnail)
        if upload_result is None:
            return PublishResult(
                video_id="",
                video_url="",
                upload_status="upload_failed",
                privacy_status=options.privacy,
                quality_passed=quality_result.passed,
                quality_warnings=warnings,
                metadata_source=metadata_source,
                topic_dir=str(options.topic_dir) if options.topic_dir else None,
                error="YouTubeアップロードに失敗しました",
            )
        self._report_progress(options, "upload_done", 0.9)

        # --- Step 5: 結果永続化 ---
        result = PublishResult(
            video_id=upload_result.video_id,
            video_url=upload_result.video_url,
            upload_status=upload_result.upload_status,
            privacy_status=upload_result.privacy_status,
            quality_passed=quality_result.passed,
            quality_warnings=warnings,
            metadata_source=metadata_source,
            topic_dir=str(options.topic_dir) if options.topic_dir else None,
            published_at=datetime.now().isoformat(),
        )

        if options.save_result:
            result.result_file = str(self._save_result(result, options))

        self._report_progress(options, "phase7_complete", 1.0)
        return result

    # ------------------------------------------------------------------
    # Internal steps
    # ------------------------------------------------------------------

    def _verify_quality(self, options: PublishOptions) -> MP4CheckResult:
        """Step 1: MP4 品質検証"""
        if not options.verify_quality:
            logger.info("MP4品質検証をスキップ (--no-verify)")
            return MP4CheckResult(file_path=options.video_path)

        logger.info(f"MP4品質検証: {options.video_path}")
        result = check_mp4(options.video_path)
        if result.passed:
            logger.info("MP4品質検証: PASS")
        else:
            critical = len(result.critical_failures)
            warn = len(result.warnings)
            logger.warning(f"MP4品質検証: CRITICAL={critical}, WARNING={warn}")
        return result

    def _load_metadata(
        self, options: PublishOptions
    ) -> tuple[Optional[Dict[str, Any]], str]:
        """Step 2: メタデータを読み込む。優先順位:
        1. 明示指定パス (--metadata)
        2. トピックディレクトリ内 output_csv/metadata.json
        3. 動画ファイルと同ディレクトリの metadata.json
        """
        # 1. 明示指定
        if options.metadata_path and options.metadata_path.exists():
            logger.info(f"メタデータ読み込み (指定): {options.metadata_path}")
            return self._read_json(options.metadata_path), "file"

        # 2. トピックディレクトリ
        if options.topic_dir:
            topic_meta = options.topic_dir / "output_csv" / "metadata.json"
            if topic_meta.exists():
                logger.info(f"メタデータ読み込み (トピック): {topic_meta}")
                return self._read_json(topic_meta), "auto"

        # 3. 動画と同階層
        video_dir_meta = options.video_path.parent / "metadata.json"
        if video_dir_meta.exists():
            logger.info(f"メタデータ読み込み (同階層): {video_dir_meta}")
            return self._read_json(video_dir_meta), "auto"

        return None, "none"

    def _resolve_thumbnail(self, options: PublishOptions) -> Optional[Path]:
        """Step 3: サムネイルを解決する。優先順位:
        1. 明示指定 (--thumbnail)
        2. トピックディレクトリ内 final/thumbnail.*
        3. 動画と同ディレクトリの thumbnail.*
        """
        if options.thumbnail_path and options.thumbnail_path.exists():
            return options.thumbnail_path

        search_dirs: List[Path] = []
        if options.topic_dir:
            search_dirs.append(options.topic_dir / "final")
        search_dirs.append(options.video_path.parent)

        for d in search_dirs:
            if not d.exists():
                continue
            for ext in ("png", "jpg", "jpeg", "webp"):
                thumb = d / f"thumbnail.{ext}"
                if thumb.exists():
                    logger.info(f"サムネイル自動検出: {thumb}")
                    return thumb
        return None

    async def _upload(
        self,
        options: PublishOptions,
        metadata: Dict[str, Any],
        thumbnail: Optional[Path],
    ) -> Optional[UploadResult]:
        """Step 4: YouTube アップロード"""
        try:
            if options.credentials_path:
                self.uploader = YouTubeUploader(
                    credentials_path=options.credentials_path
                )

            auth_ok = await self.uploader.authenticate()
            if not auth_ok:
                logger.error("YouTube認証に失敗")
                return None

            def _progress_bridge(pct: float) -> None:
                # upload progress (0-1) を phase7 全体の 0.4-0.9 にマッピング
                if options.progress_callback:
                    mapped = 0.4 + pct * 0.5
                    options.progress_callback("uploading", mapped)

            result = await self.uploader.upload_video(
                video=options.video_path,
                metadata=metadata,
                thumbnail_path=thumbnail,
                progress_callback=_progress_bridge,
                verify_quality=False,  # 既に Step 1 で検証済み
            )
            return result
        except Exception as e:
            logger.error(f"YouTubeアップロード失敗: {e}")
            return None

    def _save_result(
        self, result: PublishResult, options: PublishOptions
    ) -> Path:
        """Step 5: 結果を publish_result.json に保存"""
        if options.topic_dir:
            save_dir = options.topic_dir
        else:
            save_dir = options.video_path.parent

        save_dir.mkdir(parents=True, exist_ok=True)
        result_path = save_dir / "publish_result.json"

        data = result.to_dict()
        result_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"公開結果を保存: {result_path}")
        return result_path

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _read_json(path: Path) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"JSON読み込み失敗: {path}: {e}")
            return None

    @staticmethod
    def _report_progress(
        options: PublishOptions, step: str, pct: float
    ) -> None:
        if options.progress_callback:
            options.progress_callback(step, pct)
