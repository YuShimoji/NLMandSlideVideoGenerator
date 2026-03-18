"""PipelineStats テスト (SP-042)"""
import json
import time
from pathlib import Path

import pytest

from core.pipeline_stats import PipelineStats, StepTimer


class TestStepTimer:
    def test_timer_measures_duration(self) -> None:
        timer = StepTimer(name="test")
        timer.start()
        time.sleep(0.05)
        timer.stop()
        assert timer.duration >= 0.04
        assert timer.duration < 1.0

    def test_timer_name(self) -> None:
        timer = StepTimer(name="collect")
        assert timer.name == "collect"


class TestPipelineStats:
    def test_start_pipeline(self) -> None:
        stats = PipelineStats()
        stats.start_pipeline("test_001", "量子コンピュータ", style="news", target_duration=1800)
        assert stats.pipeline_id == "test_001"
        assert stats.topic == "量子コンピュータ"
        assert stats.style == "news"
        assert stats.target_duration == 1800
        assert stats.timestamp != ""

    def test_step_timing(self) -> None:
        stats = PipelineStats()
        stats.start_step("collect")
        time.sleep(0.05)
        stats.stop_step("collect")
        assert "collect" in stats.step_durations
        assert stats.step_durations["collect"] >= 0.04

    def test_record_sources(self) -> None:
        stats = PipelineStats()
        stats.record_sources(5)
        assert stats.source_count == 5

    def test_record_segments(self) -> None:
        stats = PipelineStats()
        stats.record_segments(29)
        assert stats.segment_count == 29

    def test_record_alignment(self) -> None:
        stats = PipelineStats()
        stats.record_alignment(supported=24, orphaned=4, conflict=1)
        assert stats.alignment_supported == 24
        assert stats.alignment_orphaned == 4
        assert stats.alignment_conflict == 1

    def test_record_visual(self) -> None:
        stats = PipelineStats()
        stats.record_visual(stock=11, ai=0, text_slide=18)
        assert stats.stock_image_count == 11
        assert stats.ai_image_count == 0
        assert stats.text_slide_count == 18

    def test_record_validation(self) -> None:
        stats = PipelineStats()
        stats.record_validation(errors=0, warnings=2)
        assert stats.pre_export_errors == 0
        assert stats.pre_export_warnings == 2

    def test_finalize_bottleneck(self) -> None:
        stats = PipelineStats()
        stats.step_durations = {"collect": 1.0, "align": 253.0, "script": 30.0}
        stats.finalize()
        assert stats.bottleneck_step == "align"

    def test_finalize_alignment_rate(self) -> None:
        stats = PipelineStats()
        stats.record_alignment(supported=24, orphaned=4, conflict=1)
        stats.finalize()
        assert stats.alignment_rate == pytest.approx(24 / 29, abs=0.01)

    def test_finalize_image_hit_rate(self) -> None:
        stats = PipelineStats()
        stats.record_visual(stock=11, ai=2, text_slide=18)
        stats.finalize()
        assert stats.image_hit_rate == pytest.approx(13 / 31, abs=0.01)

    def test_finalize_visual_ratio(self) -> None:
        stats = PipelineStats()
        stats.record_segments(29)
        stats.record_visual(stock=11, ai=0, text_slide=18)
        stats.finalize()
        assert stats.visual_ratio == pytest.approx(29 / 29, abs=0.01)

    def test_finalize_zero_division_safe(self) -> None:
        stats = PipelineStats()
        stats.finalize()
        assert stats.alignment_rate == 0.0
        assert stats.image_hit_rate == 0.0
        assert stats.visual_ratio == 0.0
        assert stats.bottleneck_step == ""


class TestSerialization:
    def test_to_dict(self) -> None:
        stats = PipelineStats()
        stats.start_pipeline("test_002", "AI技術", style="educational")
        stats.record_sources(3)
        stats.record_segments(10)
        stats.record_alignment(8, 1, 1)
        stats.record_visual(stock=5, ai=1, text_slide=4)
        stats.record_validation(errors=0, warnings=1)
        stats.speaker_mapping_applied = True
        stats.step_durations = {"collect": 0.5, "script": 10.0}
        stats.finalize()

        d = stats.to_dict()
        assert d["pipeline_id"] == "test_002"
        assert d["topic"] == "AI技術"
        assert d["speed"]["step_durations"]["collect"] == 0.5
        assert d["density"]["alignment_rate"] == pytest.approx(0.8, abs=0.01)
        assert d["visual"]["image_hit_rate"] == pytest.approx(0.6, abs=0.01)
        assert d["consistency"]["speaker_mapping_applied"] is True

    def test_save_and_load(self, tmp_path: Path) -> None:
        stats = PipelineStats()
        stats.start_pipeline("test_003", "テスト", style="news", target_duration=600)
        stats.record_sources(5)
        stats.record_segments(15)
        stats.record_alignment(12, 2, 1)
        stats.record_visual(stock=8, ai=0, text_slide=7)
        stats.record_validation(errors=1, warnings=3)
        stats.speaker_mapping_applied = True
        stats.step_durations = {"collect": 0.5, "script": 30.0, "align": 100.0}
        stats.finalize()

        saved_path = stats.save(tmp_path)
        assert saved_path.exists()

        loaded = PipelineStats.load(tmp_path)
        assert loaded is not None
        assert loaded.pipeline_id == "test_003"
        assert loaded.topic == "テスト"
        assert loaded.source_count == 5
        assert loaded.alignment_supported == 12
        assert loaded.stock_image_count == 8
        assert loaded.pre_export_errors == 1
        assert loaded.speaker_mapping_applied is True
        assert loaded.bottleneck_step == "align"
        assert loaded.alignment_rate == pytest.approx(12 / 15, abs=0.01)

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        loaded = PipelineStats.load(tmp_path)
        assert loaded is None

    def test_json_roundtrip(self, tmp_path: Path) -> None:
        stats = PipelineStats()
        stats.start_pipeline("roundtrip", "テスト")
        stats.record_visual(stock=3, ai=1, text_slide=6)
        stats.finalize()

        stats.save(tmp_path)
        with open(tmp_path / "pipeline_stats.json", "r", encoding="utf-8") as f:
            raw = json.load(f)

        assert raw["visual"]["stock_image_count"] == 3
        assert raw["visual"]["ai_image_count"] == 1
        assert raw["visual"]["text_slide_count"] == 6


class TestSummary:
    def test_summary_output(self) -> None:
        stats = PipelineStats()
        stats.start_pipeline("summary_test", "量子コンピュータ", style="news", target_duration=1800)
        stats.record_sources(5)
        stats.record_segments(29)
        stats.record_alignment(24, 4, 1)
        stats.record_visual(stock=11, ai=0, text_slide=18)
        stats.step_durations = {"collect": 0.5, "script": 30.7, "align": 253.2}
        stats.total_duration = 338.5
        stats.finalize()

        summary = stats.summary()
        assert "summary_test" in summary
        assert "量子コンピュータ" in summary
        assert "align" in summary
        assert "338.5" in summary
