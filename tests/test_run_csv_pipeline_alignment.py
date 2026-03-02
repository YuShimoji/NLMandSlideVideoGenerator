"""Tests for alignment pre-check integration in run_csv_pipeline.py."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import sys

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from scripts.run_csv_pipeline import _run
import argparse


@pytest.fixture
def mock_pipeline_args(tmp_path):
    """Create minimal args namespace with a package.json fixture."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("Speaker,Text\nTest,ここはテストです。", encoding="utf-8")
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    package_file = tmp_path / "package.json"
    package_data = {
        "package_id": "test_pkg",
        "topic": "test",
        "created_at": "2026-01-01T00:00:00",
        "sources": [],
    }
    package_file.write_text(json.dumps(package_data), encoding="utf-8")

    args = argparse.Namespace(
        csv=str(csv_file),
        audio_dir=str(audio_dir),
        topic="test_topic",
        video_quality="1080p",
        max_chars_per_slide=None,
        upload=False,
        public_upload=False,
        export_ymm4=False,
        package=str(package_file),
        strict_alignment=False,
    )
    return args


def _build_analyzer_mock(summary: dict) -> MagicMock:
    """Return a mock ScriptAlignmentAnalyzer with async methods."""
    mock_analyzer = MagicMock()
    mock_report = MagicMock()
    mock_report.summary = summary

    mock_analyzer.load_script = AsyncMock(return_value={"segments": []})
    mock_analyzer.analyze = AsyncMock(return_value=mock_report)
    return mock_analyzer


# ── Test 1: alignment passes → pipeline runs ──────────────────────


@pytest.mark.asyncio
@patch("scripts.run_csv_pipeline.build_default_pipeline")
@patch("scripts.run_csv_pipeline.ScriptAlignmentAnalyzer")
async def test_alignment_pass_then_pipeline_runs(
    mock_analyzer_cls, mock_build, mock_pipeline_args
):
    analyzer = _build_analyzer_mock(
        {"supported": 1, "orphaned": 0, "missing": 0, "conflict": 0}
    )
    mock_analyzer_cls.return_value = analyzer

    mock_pipeline = MagicMock()
    mock_pipeline.run_csv_timeline = AsyncMock(
        return_value={"success": True, "artifacts": None, "youtube_url": None}
    )
    mock_build.return_value = mock_pipeline

    result = await _run(mock_pipeline_args)

    assert result == 0, "Pipeline should succeed when alignment has no missing items"
    analyzer.analyze.assert_awaited_once()
    mock_pipeline.run_csv_timeline.assert_awaited_once()


# ── Test 2: alignment has missing + strict → pipeline blocked ─────


@pytest.mark.asyncio
@patch("scripts.run_csv_pipeline.build_default_pipeline")
@patch("scripts.run_csv_pipeline.ScriptAlignmentAnalyzer")
async def test_strict_alignment_blocks_pipeline(
    mock_analyzer_cls, mock_build, mock_pipeline_args
):
    mock_pipeline_args.strict_alignment = True

    analyzer = _build_analyzer_mock(
        {"supported": 0, "orphaned": 0, "missing": 2, "conflict": 0}
    )
    mock_analyzer_cls.return_value = analyzer

    mock_pipeline = MagicMock()
    mock_pipeline.run_csv_timeline = AsyncMock()
    mock_build.return_value = mock_pipeline

    result = await _run(mock_pipeline_args)

    assert result == 1, "Pipeline must abort when strict_alignment is set and missing > 0"
    analyzer.analyze.assert_awaited_once()
    mock_pipeline.run_csv_timeline.assert_not_awaited()


# ── Test 3: alignment has missing but NOT strict → pipeline runs ──


@pytest.mark.asyncio
@patch("scripts.run_csv_pipeline.build_default_pipeline")
@patch("scripts.run_csv_pipeline.ScriptAlignmentAnalyzer")
async def test_non_strict_continues_despite_missing(
    mock_analyzer_cls, mock_build, mock_pipeline_args
):
    mock_pipeline_args.strict_alignment = False

    analyzer = _build_analyzer_mock(
        {"supported": 0, "orphaned": 1, "missing": 1, "conflict": 0}
    )
    mock_analyzer_cls.return_value = analyzer

    mock_pipeline = MagicMock()
    mock_pipeline.run_csv_timeline = AsyncMock(
        return_value={"success": True, "artifacts": None, "youtube_url": None}
    )
    mock_build.return_value = mock_pipeline

    result = await _run(mock_pipeline_args)

    assert result == 0, "Pipeline should proceed when strict_alignment is off even with missing"
    analyzer.analyze.assert_awaited_once()
    mock_pipeline.run_csv_timeline.assert_awaited_once()
