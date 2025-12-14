"""
TikTok プラットフォームアダプター
TikTok / TikTok Shorts への動画投稿機能
"""
import asyncio
import json
from typing import Dict, Any, Optional, Union
from pathlib import Path

from core.interfaces import IPlatformAdapter
from ..utils.logger import logger


class TikTokPlatformAdapter(IPlatformAdapter):
    """TikTok 動画投稿アダプター"""

    def __init__(self, api_key: Optional[str] = None, access_token: Optional[str] = None):
        self.api_key = api_key
        self.access_token = access_token
        self.base_url = "https://open-api.tiktok.com"
        # TikTok API の初期化（実際のAPI実装時はここに）

    async def publish(self, package: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        TikTok に動画を投稿

        Args:
            package: 投稿パッケージ（video, metadata, thumbnail など）
            options: 追加オプション

        Returns:
            Dict[str, Any]: 投稿結果
        """
        options = options or {}
        is_shorts = options.get('format', 'video') == 'shorts'

        logger.info(f"TikTok {'Shorts' if is_shorts else 'Video'} 投稿を開始")

        try:
            # 動画ファイルの検証
            video_info = package.get('video')
            if not video_info or not hasattr(video_info, 'file_path'):
                raise ValueError("動画ファイルが指定されていません")

            video_path = Path(video_info.file_path)
            if not video_path.exists():
                raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")

            # メタデータの準備
            metadata = package.get('metadata', {})
            title = metadata.get('title', 'Untitled Video')
            description = metadata.get('description', '')

            # TikTok 向けにメタデータを調整
            tiktok_metadata = self._adapt_metadata_for_tiktok(metadata, is_shorts)

            # 投稿実行（モック実装）
            result = await self._upload_to_tiktok(
                video_path=video_path,
                title=tiktok_metadata['title'],
                description=tiktok_metadata['description'],
                tags=tiktok_metadata.get('tags', []),
                privacy_level=tiktok_metadata.get('privacy_level', 'public'),
                is_shorts=is_shorts
            )

            logger.info("TikTok 投稿完了")
            return result

        except (FileNotFoundError, OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"TikTok 投稿エラー: {e}")
            return {
                'success': False,
                'error': str(e),
                'platform': 'tiktok'
            }
        except Exception as e:
            logger.error(f"TikTok 投稿エラー: {e}")
            return {
                'success': False,
                'error': str(e),
                'platform': 'tiktok'
            }

    def _adapt_metadata_for_tiktok(self, metadata: Dict[str, Any], is_shorts: bool) -> Dict[str, Any]:
        """
        YouTube メタデータを TikTok 向けに適応

        Args:
            metadata: 元のメタデータ
            is_shorts: Shorts かどうか

        Returns:
            Dict[str, Any]: 適応されたメタデータ
        """
        adapted = {}

        # タイトル（TikTok は2200文字まで）
        title = metadata.get('title', '')
        if len(title) > 2200:
            title = title[:2197] + "..."
        adapted['title'] = title

        # 説明（ハッシュタグ含む）
        description = metadata.get('description', '')
        tags = metadata.get('tags', [])

        # ハッシュタグを追加
        hashtags = [f"#{tag.replace(' ', '')}" for tag in tags[:10]]  # 最大10ハッシュタグ
        hashtag_string = ' '.join(hashtags)

        # Shorts の場合はより短く
        if is_shorts:
            # 最初の文とハッシュタグのみ
            first_sentence = description.split('。')[0] if '。' in description else description[:100]
            adapted['description'] = f"{first_sentence} {hashtag_string}".strip()
        else:
            # 通常動画の場合はより詳細
            adapted['description'] = f"{description[:2000]} {hashtag_string}".strip()

        adapted['tags'] = hashtags

        # プライバシー設定
        privacy_map = {
            'public': 'public',
            'private': 'private',
            'unlisted': 'public'  # TikTok には unlisted に相当するものがない
        }
        adapted['privacy_level'] = privacy_map.get(metadata.get('privacy_status', 'private'), 'private')

        return adapted

    async def _upload_to_tiktok(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list,
        privacy_level: str,
        is_shorts: bool
    ) -> Dict[str, Any]:
        """
        TikTok API を使用して動画をアップロード

        Args:
            video_path: 動画ファイルパス
            title: タイトル
            description: 説明
            tags: ハッシュタグ
            privacy_level: プライバシー設定
            is_shorts: Shorts かどうか

        Returns:
            Dict[str, Any]: アップロード結果
        """
        # TikTok API の実際の実装はここに
        # 現在はモック実装

        logger.info(f"TikTok 動画アップロード中: {video_path.name}")

        # ファイルサイズチェック（TikTok の制限: 最大1GB）
        file_size = video_path.stat().st_size
        if file_size > 1 * 1024 * 1024 * 1024:  # 1GB
            raise ValueError("動画ファイルが大きすぎます（最大1GB）")

        # 動画長チェック
        # Shorts: 15-60秒, 通常: 3秒-10分
        # 実際のチェックは ffmpeg などで実装

        # API 呼び出し（モック）
        await asyncio.sleep(2)  # アップロードをシミュレート

        # 成功レスポンス
        mock_response = {
            'success': True,
            'platform': 'tiktok',
            'video_id': f"tiktok_{hash(str(video_path))}",
            'url': f"https://www.tiktok.com/@username/video/{hash(str(video_path))}",
            'title': title,
            'description': description,
            'tags': tags,
            'privacy_level': privacy_level,
            'is_shorts': is_shorts,
            'uploaded_at': asyncio.get_event_loop().time()
        }

        return mock_response

    async def get_video_status(self, video_id: str) -> Dict[str, Any]:
        """
        動画の投稿状況を取得

        Args:
            video_id: TikTok 動画ID

        Returns:
            Dict[str, Any]: ステータス情報
        """
        # API でステータス取得（モック）
        return {
            'video_id': video_id,
            'status': 'published',  # published, processing, failed
            'views': 0,
            'likes': 0,
            'comments': 0,
            'shares': 0
        }

    async def delete_video(self, video_id: str) -> bool:
        """
        動画を削除

        Args:
            video_id: TikTok 動画ID

        Returns:
            bool: 削除成功かどうか
        """
        # API で削除（モック）
        logger.info(f"TikTok 動画削除: {video_id}")
        return True
