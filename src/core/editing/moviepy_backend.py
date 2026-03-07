"""
MoviePy ベースの編集バックエンド (NO-OP STUB)

Path B (MoviePy-based Python video generation) has been removed.
YMM4 is now the sole renderer for video output.

This stub preserves import paths and type definitions for compatibility.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from ..interfaces import IEditingBackend
from video_editor.video_composer import VideoInfo
from notebook_lm.audio_generator import AudioInfo
from slides.slide_generator import SlidesPackage
from notebook_lm.transcript_processor import TranscriptInfo


class MoviePyEditingBackend(IEditingBackend):
    """MoviePy バックエンド (NO-OP STUB)"""

    def __init__(self) -> None:
        pass

    async def render(
        self,
        timeline_plan: Dict[str, Any],
        audio: AudioInfo,
        slides: SlidesPackage,
        transcript: TranscriptInfo,
        quality: str = "1080p",
        extras: Optional[Dict[str, Any]] = None,
    ) -> VideoInfo:
        """レンダリング (STUB)"""
        raise NotImplementedError("Path B (MoviePy) has been removed. Use YMM4 for rendering.")
