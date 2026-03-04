from __future__ import annotations
from typing import Optional, Dict, Any, Callable
from pathlib import Path
from ..utils.logger import logger
from ..interfaces import (
    ITimelinePlanner,
    IEditingBackend,
    IThumbnailGenerator,
    IVideoComposer,
)
from notebook_lm.audio_generator import AudioInfo
from notebook_lm.transcript_processor import TranscriptInfo
from video_editor.video_composer import VideoInfo, SlidesPackage

class Stage2RenderProcessor:
    def __init__(
        self,
        timeline_planner: Optional[ITimelinePlanner] = None,
        editing_backend: Optional[IEditingBackend] = None,
        thumbnail_generator: Optional[IThumbnailGenerator] = None,
        video_composer: Optional[IVideoComposer] = None,
    ):
        self.timeline_planner = timeline_planner
        self.editing_backend = editing_backend
        self.thumbnail_generator = thumbnail_generator
        self.video_composer = video_composer

    async def process(
        self,
        audio_info: AudioInfo,
        slides_pkg: SlidesPackage,
        transcript: TranscriptInfo,
        quality: str,
        script_bundle: Optional[Dict[str, Any]],
        user_preferences: Optional[Dict[str, Any]],
        stage2_mode: str,
        editing_extras: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
    ) -> tuple[VideoInfo, Optional[Path], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Stage2: 動画レンダリング処理"""
        thumbnail_path: Optional[Path] = None
        timeline_plan: Optional[Dict[str, Any]] = None
        editing_outputs: Optional[Dict[str, Any]] = None

        if self.timeline_planner and self.editing_backend:
            if progress_callback:
                progress_callback("タイムライン計画", 0.7, "動画のタイムラインを計画します...")
            logger.info(f"Stage2モード: {stage2_mode}")

            timeline_plan = await self.timeline_planner.build_plan(
                script=script_bundle or {"segments": transcript.segments},
                audio=audio_info,
                user_preferences=user_preferences,
            )

            if progress_callback:
                progress_callback("動画レンダリング", 0.75, "MoviePyで動画をレンダリングします...")

            if editing_extras is None:
                editing_extras = {"export_outputs": {}}
            video_info = await self.editing_backend.render(
                timeline_plan=timeline_plan,
                audio=audio_info,
                slides=slides_pkg,
                transcript=transcript,
                quality=quality,
                extras=editing_extras,
            )
            editing_outputs = editing_extras.get("export_outputs") or None

            # サムネイル生成
            if self.thumbnail_generator and user_preferences and user_preferences.get("generate_thumbnail", False):
                try:
                    thumbnail_style = user_preferences.get("thumbnail_style", "modern")
                    thumbnail_info = await self.thumbnail_generator.generate(
                        video=video_info,
                        script=script_bundle or {"title": transcript.title},
                        slides=slides_pkg,
                        style=thumbnail_style
                    )
                    thumbnail_path = thumbnail_info.file_path
                    logger.info(f"サムネイル生成完了: {thumbnail_path}")
                except Exception as thumb_err:
                    logger.warning(f"サムネイル生成に失敗しました: {thumb_err}")
                    thumbnail_path = None
        else:
            if progress_callback:
                progress_callback("動画合成", 0.7, "MoviePyで動画を合成します...")
            logger.info("Stage2拡張未設定のため従来の VideoComposer を使用")
            video_info = await self.video_composer.compose_video(audio_info, slides_pkg, transcript, quality)

        logger.info(f"動画合成完了: {video_info.file_path}")
        if progress_callback:
            progress_callback("動画合成", 0.8, f"動画合成完了: {video_info.file_path}")

        return video_info, thumbnail_path, timeline_plan, editing_outputs
