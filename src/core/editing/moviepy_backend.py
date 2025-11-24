"""MoviePy ベースの編集バックエンド"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import settings
from ..interfaces import IEditingBackend
from ..timeline.models import TimelinePlan
from video_editor.video_composer import VideoComposer, VideoInfo
from notebook_lm.audio_generator import AudioInfo
from slides.slide_generator import SlidesPackage
from notebook_lm.transcript_processor import TranscriptInfo


class MoviePyEditingBackend(IEditingBackend):
    """既存 VideoComposer をラップするバックエンド実装"""

    def __init__(self) -> None:
        self.video_composer = VideoComposer()

    async def render(
        self,
        timeline_plan: Dict[str, Any],
        audio: AudioInfo,
        slides: SlidesPackage,
        transcript: TranscriptInfo,
        quality: str = "1080p",
        extras: Optional[Dict[str, Any]] = None,
    ) -> VideoInfo:
        plan = self._parse_plan(timeline_plan)
        # TODO: plan 情報を VideoComposer に反映（シーン長・エフェクト適用など）
        return await self.video_composer.compose_video(
            audio_file=audio,
            slides_file=slides,
            transcript=transcript,
            quality=quality,
        )

    def _parse_plan(self, plan_dict: Dict[str, Any]) -> TimelinePlan:
        segments = []
        for raw in plan_dict.get("segments", []):
            segments.append(raw)
        return TimelinePlan(
            total_duration=float(plan_dict.get("total_duration", 0.0) or 0.0),
            segments=segments,  # 型ヒント用、詳細反映は今後実装
            notes=plan_dict.get("notes"),
        )
