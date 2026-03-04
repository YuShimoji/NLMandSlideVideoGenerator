from __future__ import annotations
from typing import Optional, Dict, Any, Callable
from pathlib import Path
from ..utils.logger import logger
from ..interfaces import (
    IMetadataGenerator,
    IPlatformAdapter,
    IUploader,
    IPublishingQueue,
)
from video_editor.video_composer import VideoInfo
from notebook_lm.transcript_processor import TranscriptInfo
from youtube.uploader import UploadResult
from config.settings import settings

class Stage3PublishProcessor:
    def __init__(
        self,
        metadata_generator: IMetadataGenerator,
        platform_adapter: Optional[IPlatformAdapter] = None,
        uploader: Optional[IUploader] = None,
        publishing_queue: Optional[IPublishingQueue] = None,
    ):
        self.metadata_generator = metadata_generator
        self.platform_adapter = platform_adapter
        self.uploader = uploader
        self.publishing_queue = publishing_queue

    async def process(
        self,
        video_info: VideoInfo,
        transcript: TranscriptInfo,
        thumbnail_path: Optional[Path],
        private_upload: bool,
        stage3_mode: str,
        user_preferences: Optional[Dict[str, Any]],
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
    ) -> tuple[Optional[UploadResult], Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Stage3: 投稿・配信処理"""
        if progress_callback:
            progress_callback("アップロード準備", 0.9, "メタデータを生成します...")

        metadata = await self.metadata_generator.generate_metadata(transcript)
        metadata["privacy_status"] = "private" if private_upload else "public"
        metadata["language"] = settings.YOUTUBE_SETTINGS.get("default_language", "ja")

        upload_result: Optional[UploadResult] = None
        youtube_url: Optional[str] = None
        publishing_result: Optional[Dict[str, Any]] = None

        if self.platform_adapter:
            if progress_callback:
                progress_callback("YouTubeアップロード", 0.95, "YouTubeに動画をアップロードします...")
            logger.info(f"Stage3モード: {stage3_mode}")

            package = {
                "video": video_info,
                "metadata": metadata,
                "thumbnail": thumbnail_path,
                "schedule": user_preferences.get("schedule") if user_preferences else None,
            }

            if self.publishing_queue:
                queue_id = await self.publishing_queue.enqueue(
                    package,
                    schedule=package.get("schedule"),
                )
                logger.info(f"投稿キューに登録しました: {queue_id}")

            publishing_result = await self.platform_adapter.publish(
                package,
                options={"mode": stage3_mode},
            )
            youtube_url = publishing_result.get("url") if publishing_result else None
        else:
            if progress_callback:
                progress_callback("YouTubeアップロード", 0.95, "YouTube APIでアップロードします...")
            
            if self.uploader:
                await self.uploader.authenticate()
                upload_result = await self.uploader.upload_video(
                    video=video_info,
                    metadata=metadata,
                    thumbnail_path=thumbnail_path,
                )
                youtube_url = upload_result.video_url if upload_result else None
                logger.success(f"アップロード完了: {youtube_url}")

        return upload_result, youtube_url, metadata, publishing_result
