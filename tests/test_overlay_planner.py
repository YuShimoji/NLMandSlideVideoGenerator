"""Tests for SP-052 OverlayPlanner."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.overlay.overlay_planner import OverlayEntry, OverlayPlan, OverlayPlanner


# ---- Fixtures ----


@pytest.fixture
def sample_script():
    """Gemini-structured script with multiple sections and key_points."""
    return {
        "title": "AIの歴史と未来",
        "segments": [
            {
                "section": "導入",
                "speaker": "れいむ",
                "content": "今日はAIの歴史について解説するよ！",
                "duration_estimate": 8.0,
                "key_points": ["AI解説シリーズ第1回"],
            },
            {
                "section": "導入",
                "speaker": "まりさ",
                "content": "楽しみだぜ！最近話題だよな",
                "duration_estimate": 6.0,
                "key_points": [],
            },
            {
                "section": "第1章: AI黎明期",
                "speaker": "れいむ",
                "content": "1956年のダートマス会議でAIという言葉が生まれたんだ",
                "duration_estimate": 12.0,
                "key_points": ["1956年ダートマス会議", "AI概念の誕生"],
            },
            {
                "section": "第1章: AI黎明期",
                "speaker": "まりさ",
                "content": "そんな昔からあったのか！",
                "duration_estimate": 5.0,
                "key_points": [],
            },
            {
                "section": "第2章: 現代AI",
                "speaker": "れいむ",
                "content": "GPT-4は2023年3月に公開され、利用者数は約1億人を突破した",
                "duration_estimate": 15.0,
                "key_points": ["GPT-4の公開"],
            },
            {
                "section": "第2章: 現代AI",
                "speaker": "まりさ",
                "content": "出典: OpenAI Technical Report 2023によると性能が大幅に向上したらしい",
                "duration_estimate": 10.0,
                "key_points": [],
            },
        ],
    }


@pytest.fixture
def planner():
    return OverlayPlanner()


# ---- Tests ----


class TestOverlayPlanner:
    def test_empty_segments(self, planner):
        result = planner.plan({"segments": []})
        assert len(result.overlays) == 0

    def test_empty_script(self, planner):
        result = planner.plan({})
        assert len(result.overlays) == 0

    def test_chapter_titles_on_section_change(self, planner, sample_script):
        result = planner.plan(sample_script)
        chapter_titles = [o for o in result.overlays if o.type == "chapter_title"]

        assert len(chapter_titles) == 3
        assert chapter_titles[0].text == "導入"
        assert chapter_titles[0].segment_index == 0
        assert chapter_titles[1].text == "第1章: AI黎明期"
        assert chapter_titles[1].segment_index == 2
        assert chapter_titles[2].text == "第2章: 現代AI"
        assert chapter_titles[2].segment_index == 4

    def test_no_duplicate_chapter_for_same_section(self, planner, sample_script):
        result = planner.plan(sample_script)
        chapter_titles = [o for o in result.overlays if o.type == "chapter_title"]
        # "導入" appears in seg 0 and 1, but only one chapter_title
        intro_titles = [t for t in chapter_titles if t.text == "導入"]
        assert len(intro_titles) == 1

    def test_key_points_extracted(self, planner, sample_script):
        result = planner.plan(sample_script)
        key_points = [o for o in result.overlays if o.type == "key_point"]

        # seg0: 1, seg2: 1 (max_key_points_per_segment=1), seg4: 1
        assert len(key_points) >= 3
        assert key_points[0].text == "AI解説シリーズ第1回"
        assert key_points[0].position == "lower_third"

    def test_max_key_points_per_segment(self, sample_script):
        planner = OverlayPlanner(max_key_points_per_segment=1)
        result = planner.plan(sample_script)
        key_points = [o for o in result.overlays if o.type == "key_point"]

        # Segment 2 has 2 key_points but max_key_points_per_segment=1
        seg2_kps = [kp for kp in key_points if kp.segment_index == 2]
        assert len(seg2_kps) == 1

    def test_statistics_detection(self, planner, sample_script):
        result = planner.plan(sample_script)
        stats = [o for o in result.overlays if o.type == "statistic"]

        # Segment 2 has "1956年", segment 4 has "約1億人"
        assert len(stats) >= 2
        seg4_stats = [s for s in stats if s.segment_index == 4]
        assert len(seg4_stats) >= 1
        assert seg4_stats[0].style == "emphasis"

    def test_source_citation_detection(self, planner, sample_script):
        result = planner.plan(sample_script)
        citations = [o for o in result.overlays if o.type == "source_citation"]

        # Segment 5 has "出典: OpenAI Technical Report 2023"
        assert len(citations) >= 1
        assert "OpenAI" in citations[0].text

    def test_duration_defaults(self, planner, sample_script):
        result = planner.plan(sample_script)

        for overlay in result.overlays:
            if overlay.type == "chapter_title":
                assert overlay.duration_sec == 4.0
            elif overlay.type == "key_point":
                assert overlay.duration_sec == 7.0
            elif overlay.type == "statistic":
                assert overlay.duration_sec == 4.0
            elif overlay.type == "source_citation":
                assert overlay.duration_sec == 5.0

    def test_custom_durations(self, sample_script):
        planner = OverlayPlanner(
            chapter_title_duration=5.0,
            key_point_duration=8.0,
            statistic_duration=3.0,
            citation_duration=6.0,
        )
        result = planner.plan(sample_script)

        chapter = next(o for o in result.overlays if o.type == "chapter_title")
        assert chapter.duration_sec == 5.0


class TestOverlayPlan:
    def test_to_dict(self):
        plan = OverlayPlan(
            overlays=[
                OverlayEntry(
                    type="chapter_title",
                    text="導入",
                    segment_index=0,
                    duration_sec=4.0,
                    position="top_center",
                )
            ]
        )
        d = plan.to_dict()
        assert d["version"] == "1.0"
        assert len(d["overlays"]) == 1
        assert d["overlays"][0]["type"] == "chapter_title"
        assert d["overlays"][0]["text"] == "導入"

    def test_save_and_load(self):
        plan = OverlayPlan(
            overlays=[
                OverlayEntry(
                    type="key_point",
                    text="テストポイント",
                    segment_index=3,
                    duration_sec=7.0,
                    position="lower_third",
                )
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "overlay_plan.json"
            plan.save(path)

            assert path.exists()
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data["version"] == "1.0"
            assert len(data["overlays"]) == 1
            assert data["overlays"][0]["text"] == "テストポイント"

    def test_save_creates_parent_dirs(self):
        plan = OverlayPlan(overlays=[])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sub" / "deep" / "overlay_plan.json"
            plan.save(path)
            assert path.exists()


class TestStatisticsDetection:
    def test_japanese_number_with_unit(self):
        planner = OverlayPlanner()
        script = {
            "segments": [
                {
                    "section": "テスト",
                    "speaker": "A",
                    "content": "市場規模は300万ドルに達した",
                    "duration_estimate": 10.0,
                    "key_points": [],
                }
            ]
        }
        result = planner.plan(script)
        stats = [o for o in result.overlays if o.type == "statistic"]
        assert len(stats) >= 1

    def test_percentage(self):
        planner = OverlayPlanner()
        script = {
            "segments": [
                {
                    "section": "テスト",
                    "speaker": "A",
                    "content": "成功率は42%を記録している",
                    "duration_estimate": 10.0,
                    "key_points": [],
                }
            ]
        }
        result = planner.plan(script)
        stats = [o for o in result.overlays if o.type == "statistic"]
        assert len(stats) >= 1

    def test_no_stat_in_plain_text(self):
        planner = OverlayPlanner()
        script = {
            "segments": [
                {
                    "section": "テスト",
                    "speaker": "A",
                    "content": "これは普通のテキストです",
                    "duration_estimate": 10.0,
                    "key_points": [],
                }
            ]
        }
        result = planner.plan(script)
        stats = [o for o in result.overlays if o.type == "statistic"]
        assert len(stats) == 0


class TestCitationDetection:
    def test_japanese_citation(self):
        planner = OverlayPlanner()
        script = {
            "segments": [
                {
                    "section": "テスト",
                    "speaker": "A",
                    "content": "出典: 総務省情報通信白書2025。詳しいデータがある",
                    "duration_estimate": 10.0,
                    "key_points": [],
                }
            ]
        }
        result = planner.plan(script)
        citations = [o for o in result.overlays if o.type == "source_citation"]
        assert len(citations) == 1
        assert "総務省" in citations[0].text

    def test_report_reference(self):
        planner = OverlayPlanner()
        script = {
            "segments": [
                {
                    "section": "テスト",
                    "speaker": "A",
                    "content": "「McKinsey Global Report」の報告によると大きな変化がある",
                    "duration_estimate": 10.0,
                    "key_points": [],
                }
            ]
        }
        result = planner.plan(script)
        citations = [o for o in result.overlays if o.type == "source_citation"]
        assert len(citations) == 1
