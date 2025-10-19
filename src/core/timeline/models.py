"""Timeline planning data models"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TimelineSegment:
    """Individual segment metadata for timeline rendering."""

    segment_id: str
    start: float
    end: float
    script_ref: Optional[Dict[str, Any]] = None
    assets: List[Dict[str, Any]] = field(default_factory=list)
    effects: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TimelinePlan:
    """Aggregated plan to hand over to an `IEditingBackend`."""

    total_duration: float
    segments: List[TimelineSegment] = field(default_factory=list)
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_duration": self.total_duration,
            "segments": [
                {
                    "segment_id": segment.segment_id,
                    "start": segment.start,
                    "end": segment.end,
                    "script_ref": segment.script_ref,
                    "assets": segment.assets,
                    "effects": segment.effects,
                }
                for segment in self.segments
            ],
            "notes": self.notes,
        }
