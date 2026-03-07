"""
エフェクト処理モジュール (NO-OP STUB)

Path B (MoviePy-based Python video generation) has been removed.
YMM4 is now the sole renderer for video output.

This stub preserves import paths and type definitions for compatibility.
"""
from typing import List, Tuple
from pathlib import Path
from dataclasses import dataclass

from notebook_lm.transcript_processor import TranscriptInfo


@dataclass
class EffectSettings:
    """エフェクト設定"""
    effect_type: str
    start_scale: float
    end_scale: float
    start_position: Tuple[float, float]
    end_position: Tuple[float, float]
    duration: float
    easing: str


@dataclass
class ProcessedSlide:
    """処理済みスライド"""
    slide_id: int
    original_path: Path
    processed_frames: List[Path]
    effect_applied: str
    duration: float


class EffectProcessor:
    """エフェクト処理クラス (NO-OP STUB)"""

    def __init__(self):
        pass

    async def apply_effects(
        self,
        slide_images: List[Path],
        transcript: TranscriptInfo
    ) -> List[ProcessedSlide]:
        """エフェクト適用 (STUB)"""
        raise NotImplementedError("Path B (MoviePy) has been removed. Use YMM4 for rendering.")

    def add_transition_effects(
        self,
        processed_slides: List[ProcessedSlide]
    ) -> List[ProcessedSlide]:
        """トランジションエフェクト追加 (STUB)"""
        raise NotImplementedError("Path B (MoviePy) has been removed. Use YMM4 for rendering.")

    def optimize_for_video_codec(self, processed_slides: List[ProcessedSlide]) -> List[ProcessedSlide]:
        """動画コーデック向け最適化 (STUB)"""
        raise NotImplementedError("Path B (MoviePy) has been removed. Use YMM4 for rendering.")
