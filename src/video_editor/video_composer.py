"""
動画合成モジュール (NO-OP STUB)

Path B (MoviePy-based Python video generation) has been removed.
YMM4 is now the sole renderer for video output.

This stub preserves import paths and type definitions for compatibility.
"""
from typing import Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from notebook_lm.audio_generator import AudioInfo
from notebook_lm.transcript_processor import TranscriptInfo
from slides.slide_generator import SlidesPackage


@dataclass
class VideoInfo:
    """動画情報"""
    file_path: Path
    duration: float
    resolution: tuple
    fps: int = 30
    file_size: int = 0
    has_subtitles: bool = False
    has_effects: bool = False
    created_at: datetime = datetime.now()
    format: str = "mp4"


@dataclass
class ThumbnailInfo:
    """サムネイル情報"""
    file_path: Path
    title_text: str
    subtitle_text: str
    style: str
    resolution: tuple
    file_size: int
    has_overlay: bool
    has_text_effects: bool
    created_at: datetime


class VideoComposer:
    """動画合成クラス (NO-OP STUB)"""

    def __init__(self):
        pass

    async def compose_video(
        self,
        audio_file: AudioInfo,
        slides_file: SlidesPackage,
        transcript: TranscriptInfo,
        quality: str = "1080p",
        timeline_plan: Optional[Dict[str, Any]] = None,
        bgm_path: Optional[Path] = None,
    ) -> VideoInfo:
        """動画合成 (STUB)"""
        raise NotImplementedError("Path B (MoviePy) has been removed. Use YMM4 for rendering.")

    async def generate_thumbnail(
        self,
        title: str,
        first_slide_path: Optional[Path] = None,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """サムネイル生成 (STUB)"""
        raise NotImplementedError("Path B (MoviePy) has been removed. Use YMM4 for rendering.")

    def optimize_for_platform(self, video_info: VideoInfo, platform: str = "youtube") -> VideoInfo:
        """プラットフォーム向け最適化 (STUB)"""
        raise NotImplementedError("Path B (MoviePy) has been removed. Use YMM4 for rendering.")
