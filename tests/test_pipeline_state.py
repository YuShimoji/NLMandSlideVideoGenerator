"""PipelineState テスト — ステップ再開機能。"""
import json
from pathlib import Path

import pytest

from core.pipeline_state import PipelineState, StepInfo, STEP_NAMES


class TestStepInfo:
    def test_default_values(self) -> None:
        info = StepInfo()
        assert info.status == "pending"
        assert info.output is None
        assert info.error is None

    def test_all_fields(self) -> None:
        info = StepInfo(
            status="done", output="package.json",
            started_at="2026-01-01T00:00:00", finished_at="2026-01-01T00:00:05",
            duration_sec=5.0,
        )
        assert info.status == "done"
        assert info.output == "package.json"
        assert info.duration_sec == 5.0


class TestPipelineStatePersistence:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        state = PipelineState(topic="AI 2026", urls=["https://example.com"])
        state.mark_done("collect", "package.json")
        state.mark_failed("script", "Gemini quota exceeded")
        state.save(tmp_path)

        loaded = PipelineState.load(tmp_path)
        assert loaded.topic == "AI 2026"
        assert loaded.urls == ["https://example.com"]
        assert loaded.is_step_done("collect")
        assert not loaded.is_step_done("script")
        assert loaded.steps["script"].error == "Gemini quota exceeded"

    def test_load_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        state = PipelineState.load(tmp_path / "nonexistent")
        assert state.topic == ""
        assert all(info.status == "pending" for info in state.steps.values())

    def test_state_file_is_valid_json(self, tmp_path: Path) -> None:
        state = PipelineState(topic="test")
        state.save(tmp_path)

        state_file = tmp_path / "pipeline_state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["topic"] == "test"
        assert "steps" in data


class TestStepTracking:
    def test_all_step_names_initialized(self) -> None:
        state = PipelineState()
        for name in STEP_NAMES:
            assert name in state.steps
            assert state.steps[name].status == "pending"

    def test_mark_running(self) -> None:
        state = PipelineState()
        state.mark_running("collect")
        assert state.steps["collect"].status == "running"
        assert state.steps["collect"].started_at is not None

    def test_mark_done(self) -> None:
        state = PipelineState()
        state.mark_running("collect")
        state.mark_done("collect", "package.json")
        assert state.is_step_done("collect")
        assert state.steps["collect"].output == "package.json"
        assert state.steps["collect"].finished_at is not None

    def test_mark_failed(self) -> None:
        state = PipelineState()
        state.mark_running("script")
        state.mark_failed("script", "API error")
        assert state.steps["script"].status == "failed"
        assert state.steps["script"].error == "API error"
        assert not state.is_step_done("script")


class TestResumeLogic:
    def test_first_incomplete_all_pending(self) -> None:
        state = PipelineState()
        assert state.first_incomplete_step() == "collect"

    def test_first_incomplete_some_done(self) -> None:
        state = PipelineState()
        state.mark_done("collect", "package.json")
        state.mark_done("script", "generated_script.json")
        assert state.first_incomplete_step() == "align"

    def test_first_incomplete_with_failure(self) -> None:
        state = PipelineState()
        state.mark_done("collect", "package.json")
        state.mark_failed("script", "quota")
        assert state.first_incomplete_step() == "script"

    def test_first_incomplete_all_done(self) -> None:
        state = PipelineState()
        for name in STEP_NAMES:
            state.mark_done(name, f"{name}_output")
        assert state.first_incomplete_step() is None

    def test_output_exists_checks_file(self, tmp_path: Path) -> None:
        state = PipelineState()
        state.mark_done("collect", "package.json")

        assert not state.output_exists("collect", tmp_path)

        (tmp_path / "package.json").write_text("{}")
        assert state.output_exists("collect", tmp_path)


class TestSummary:
    def test_summary_contains_all_steps(self) -> None:
        state = PipelineState()
        state.mark_done("collect", "package.json")
        state.mark_failed("script", "error msg here")
        summary = state.summary()
        assert "collect" in summary
        assert "script" in summary
        assert "[OK]" in summary
        assert "[NG]" in summary

    def test_summary_shows_duration(self) -> None:
        state = PipelineState()
        state.steps["collect"] = StepInfo(
            status="done", duration_sec=3.5
        )
        summary = state.summary()
        assert "3.5s" in summary
