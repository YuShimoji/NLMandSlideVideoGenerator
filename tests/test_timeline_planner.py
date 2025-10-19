import sys
from pathlib import Path
from types import SimpleNamespace

import asyncio
import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.timeline.basic_planner import BasicTimelinePlanner  # noqa: E402


def test_basic_timeline_plan_alignment():
    planner = BasicTimelinePlanner()
    audio = SimpleNamespace(duration=120.0)
    script = {
        "segments": [
            {"segment_id": "s1", "duration": 30, "content": "intro"},
            {"segment_id": "s2", "duration": 60, "content": "body"},
            {"segment_id": "s3", "duration": 45, "content": "outro"},
        ]
    }

    plan = asyncio.run(planner.build_plan(script=script, audio=audio))

    assert plan["total_duration"] == pytest.approx(120.0)
    assert len(plan["segments"]) == 3
    assert plan["segments"][0]["segment_id"] == "s1"
    assert plan["segments"][0]["start"] == pytest.approx(0.0)
    assert plan["segments"][-1]["end"] == pytest.approx(120.0)


def test_basic_timeline_plan_fallback_segment():
    planner = BasicTimelinePlanner(default_segment_duration=15.0)
    audio = SimpleNamespace(duration=0.0)

    plan = asyncio.run(planner.build_plan(script={}, audio=audio))

    assert plan["total_duration"] == pytest.approx(15.0)
    assert len(plan["segments"]) == 1
    assert plan["segments"][0]["segment_id"] == "seg_1"
    assert plan["segments"][0]["end"] == pytest.approx(15.0)
