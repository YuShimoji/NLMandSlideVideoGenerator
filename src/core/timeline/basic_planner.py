"""シンプルなタイムラインプランナー実装"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional

from config.settings import settings
from ..interfaces import ITimelinePlanner
from .models import TimelinePlan, TimelineSegment


class BasicTimelinePlanner(ITimelinePlanner):
    """台本と音声長から基本的なタイムラインを生成"""

    def __init__(self, default_segment_duration: float = 15.0) -> None:
        self.default_segment_duration = default_segment_duration

    async def build_plan(
        self,
        script: Dict[str, Any],
        audio,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        total_duration = float(getattr(audio, "duration", 0.0) or 0.0)
        raw_segments = self._extract_segments(script)
        segment_count = max(len(raw_segments), 1)
        base_duration = total_duration / segment_count if total_duration else self.default_segment_duration

        segments: List[TimelineSegment] = []
        cursor = 0.0
        for index, raw in enumerate(raw_segments):
            normalized = self._normalize_segment(raw, index, base_duration)
            start = cursor
            end = start + normalized["duration"]
            if total_duration:
                if index == segment_count - 1 or end > total_duration:
                    end = total_duration
            cursor = end
            segments.append(
                TimelineSegment(
                    segment_id=normalized["segment_id"],
                    start=start,
                    end=end,
                    script_ref=normalized["script_ref"],
                    assets=normalized["assets"],
                    effects=normalized["effects"],
                )
            )

        if not segments:
            segments.append(
                TimelineSegment(
                    segment_id="seg_1",
                    start=0.0,
                    end=total_duration or base_duration,
                    script_ref={},
                    assets=[],
                    effects=[],
                )
            )
            cursor = segments[-1].end

        plan = TimelinePlan(
            total_duration=total_duration or cursor,
            segments=segments,
            notes=(user_preferences or {}).get("timeline_notes"),
        )
        return plan.to_dict()

    def _extract_segments(self, script: Optional[Dict[str, Any]]) -> List[Any]:
        if not script:
            return []
        segments = script.get("segments") or []
        if isinstance(segments, list):
            return segments
        return []

    def _normalize_segment(self, segment: Any, index: int, fallback_duration: float) -> Dict[str, Any]:
        if is_dataclass(segment):
            data = asdict(segment)
        elif hasattr(segment, "__dict__") and not isinstance(segment, dict):
            data = dict(segment.__dict__)
        else:
            data = dict(segment)

        duration = self._resolve_duration(data, fallback_duration)
        assets = data.get("assets") or data.get("media") or []
        effects = data.get("effects") or data.get("visual_tags") or []
        identifier = data.get("segment_id") or data.get("id") or f"seg_{index + 1}"

        return {
            "segment_id": str(identifier),
            "duration": duration,
            "script_ref": data,
            "assets": assets if isinstance(assets, list) else [],
            "effects": effects if isinstance(effects, list) else [],
        }

    def _resolve_duration(self, data: Dict[str, Any], fallback: float) -> float:
        for key in ("duration", "duration_hint", "estimated_duration", "duration_sec"):
            value = data.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
        return fallback
