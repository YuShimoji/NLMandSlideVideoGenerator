"""YouTube platform adapter implementation"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from config.settings import settings
from youtube.uploader import YouTubeUploader
from ..interfaces import IPlatformAdapter

logger = logging.getLogger(__name__)


class YouTubePlatformAdapter(IPlatformAdapter):
    """YouTubeへの投稿を抽象化するアダプター"""

    def __init__(self) -> None:
        self.uploader = YouTubeUploader()
        self._authenticated = False

    async def upload(self, video, metadata, thumbnail=None, schedule=None):
        """互換性用ラッパー: 従来の upload 風シグネチャを publish に委譲する"""
        package = {
            "video": video,
            "metadata": metadata,
            "thumbnail": thumbnail,
            "schedule": schedule,
        }
        return await self.publish(package)

    async def publish(
        self,
        package: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        YouTubeへ動画を投稿
        package: {
            "video": VideoInfo,
            "metadata": Dict[str, Any],
            "thumbnail": Optional[Path],
            "schedule": Optional[str]
        }
        """
        options = options or {}
        mode = options.get("mode", "auto")

        if not self._authenticated:
            await self.uploader.authenticate()
            self._authenticated = True

        video = package["video"]
        metadata = package["metadata"]
        thumbnail = package.get("thumbnail")
        schedule = package.get("schedule")

        # スケジュール対応は後日実装
        if schedule:
            logger.warning("Scheduled posting not yet implemented, posting immediately")

        upload_result = await self.uploader.upload_video(
            video=video,
            metadata=metadata,
            thumbnail_path=thumbnail,
        )

        result = {
            "platform": "youtube",
            "success": upload_result is not None,
            "url": upload_result.video_url if upload_result else None,
            "video_id": upload_result.video_id if upload_result else None,
            "upload_status": upload_result.upload_status if upload_result else "failed",
        }

        logger.info(f"YouTube投稿完了: {result['url']}")
        return result
