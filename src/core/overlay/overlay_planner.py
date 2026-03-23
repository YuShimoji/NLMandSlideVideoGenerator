"""SP-052: Generate overlay_plan.json from structured script JSON.

Extracts chapter titles, key points, statistics, and source citations
from Gemini-structured script segments and produces an overlay plan
for YMM4 TextItem placement on Layer 7.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class OverlayEntry:
    """Single overlay instruction for YMM4."""

    type: str  # chapter_title | key_point | statistic | source_citation
    text: str
    segment_index: int
    duration_sec: float
    position: str
    style: str = "default"
    value: str | None = None  # for statistic type


@dataclass
class OverlayPlan:
    """Complete overlay plan for a video."""

    version: str = "1.0"
    overlays: list[OverlayEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "overlays": [asdict(e) for e in self.overlays],
        }

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


# Regex for numbers with optional units/suffixes (e.g. "1億人", "300万", "$5.2B", "42%")
_STAT_RE = re.compile(
    r"(?:約|over\s+|more than\s+)?"
    r"[\$￥€]?\d[\d,\.]*\s*"
    r"(?:億|万|千|兆|百万|%|人|件|回|円|ドル|[KMBT](?:illion)?)?",
    re.IGNORECASE,
)


class OverlayPlanner:
    """Generate overlay_plan.json from structured script segments.

    Expects script_data in the Gemini-structured format:
        {
            "title": "...",
            "segments": [
                {
                    "section": "導入",
                    "speaker": "Host1",
                    "content": "...",
                    "duration_estimate": 20.0,
                    "key_points": ["point1", "point2"]
                },
                ...
            ]
        }
    """

    def __init__(
        self,
        chapter_title_duration: float = 4.0,
        key_point_duration: float = 7.0,
        statistic_duration: float = 4.0,
        citation_duration: float = 5.0,
        max_key_points_per_segment: int = 1,
    ) -> None:
        self.chapter_title_duration = chapter_title_duration
        self.key_point_duration = key_point_duration
        self.statistic_duration = statistic_duration
        self.citation_duration = citation_duration
        self.max_key_points_per_segment = max_key_points_per_segment

    def plan(self, script_data: dict[str, Any]) -> OverlayPlan:
        """Generate an overlay plan from structured script data."""
        segments = script_data.get("segments", [])
        if not segments:
            return OverlayPlan()

        overlays: list[OverlayEntry] = []

        # Track section changes for chapter titles
        prev_section: str | None = None

        for i, seg in enumerate(segments):
            section = seg.get("section", "")
            content = seg.get("content", "")
            key_points = seg.get("key_points", [])

            # Chapter title on section change
            if section and section != prev_section:
                overlays.append(
                    OverlayEntry(
                        type="chapter_title",
                        text=section,
                        segment_index=i,
                        duration_sec=self.chapter_title_duration,
                        position="top_center",
                    )
                )
                prev_section = section

            # Key points
            for kp in key_points[: self.max_key_points_per_segment]:
                if kp and isinstance(kp, str) and len(kp.strip()) > 0:
                    overlays.append(
                        OverlayEntry(
                            type="key_point",
                            text=kp.strip(),
                            segment_index=i,
                            duration_sec=self.key_point_duration,
                            position="lower_third",
                        )
                    )

            # Statistics detection in content
            stat_match = _STAT_RE.search(content)
            if stat_match:
                stat_text = self._extract_stat_context(content, stat_match)
                if stat_text:
                    overlays.append(
                        OverlayEntry(
                            type="statistic",
                            text=stat_text,
                            segment_index=i,
                            duration_sec=self.statistic_duration,
                            position="center_upper",
                            style="emphasis",
                            value=stat_match.group(0).strip(),
                        )
                    )

            # Source citation detection
            citation = self._extract_citation(content)
            if citation:
                overlays.append(
                    OverlayEntry(
                        type="source_citation",
                        text=citation,
                        segment_index=i,
                        duration_sec=self.citation_duration,
                        position="above_subtitle",
                        style="small",
                    )
                )

        return OverlayPlan(overlays=overlays)

    def _extract_stat_context(self, content: str, match: re.Match) -> str | None:
        """Extract a short phrase around a statistic for display."""
        start = max(0, match.start() - 20)
        end = min(len(content), match.end() + 10)

        # Find sentence/clause boundaries
        snippet = content[start:end]

        # Trim to nearest punctuation or clause boundary
        for sep in ["、", "。", "，", "．", ",", ".", "！", "？"]:
            idx = snippet.find(sep)
            if idx > 0 and idx > len(snippet) // 3:
                snippet = snippet[:idx]
                break

        # Remove leading partial characters
        if start > 0:
            for j, c in enumerate(snippet):
                if c in "はがをにでもの" or c.isalnum():
                    snippet = snippet[j:]
                    break

        snippet = snippet.strip()
        if len(snippet) < 3:
            return None
        return snippet

    def _extract_citation(self, content: str) -> str | None:
        """Detect source citations in content text."""
        patterns = [
            r"出典[:：]\s*(.+?)(?:[。、]|$)",
            r"(?:according to|出所[:：]?|ソース[:：]?|参照[:：]?)\s*(.+?)(?:[。、]|$)",
            r"「(.+?)」(?:によると|の(?:報告|調査|データ|レポート))",
        ]
        for pat in patterns:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                citation = m.group(1).strip()
                if len(citation) > 5:
                    return f"出典: {citation}"
        return None
