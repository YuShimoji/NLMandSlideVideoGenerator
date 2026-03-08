"""動画関連データモデル."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


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
