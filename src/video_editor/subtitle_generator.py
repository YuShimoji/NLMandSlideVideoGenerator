"""
字幕生成モジュール (NO-OP STUB)

Path B (MoviePy-based Python video generation) has been removed.
YMM4 is now the sole renderer for video output.

This stub preserves import paths and type definitions for compatibility.
"""
from typing import Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass

from notebook_lm.transcript_processor import TranscriptInfo


@dataclass
class SubtitleSegment:
    """字幕セグメント"""
    index: int
    start_time: str
    end_time: str
    text: str
    style: Optional[Dict[str, Any]] = None


class SubtitleGenerator:
    """字幕生成クラス (NO-OP STUB)"""

    def __init__(self, preset_dir: Optional[Path] = None):
        pass

    async def generate_subtitles(
        self,
        transcript_info: TranscriptInfo,
        style: str = "default"
    ) -> Path:
        """字幕生成 (STUB)"""
        raise NotImplementedError("Path B (MoviePy) has been removed. Use YMM4 for rendering.")

    def add_styling_to_subtitles(self, srt_path: Path) -> Path:
        """字幕スタイリング追加 (STUB)"""
        raise NotImplementedError("Path B (MoviePy) has been removed. Use YMM4 for rendering.")
