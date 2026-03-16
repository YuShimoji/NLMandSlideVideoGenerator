"""Tests for src/core/pipeline.py — ModularVideoPipeline."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.pipeline import ModularVideoPipeline
from src.core.exceptions import PipelineError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_audio_info():
    ai = MagicMock()
    ai.file_path = Path("/fake/audio.wav")
    return ai


def _make_transcript():
    t = MagicMock()
    t.title = "Test"
    t.segments = []
    return t


def _make_slides_pkg():
    s = MagicMock()
    s.total_slides = 3
    s.file_path = Path("/fake/slides")
    return s


def _make_video_info():
    v = MagicMock()
    v.file_path = Path("/fake/video.mp4")
    return v


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

class TestPipelineInit:
    def test_defaults(self):
        """Pipeline can be created with default components."""
        pipeline = ModularVideoPipeline()
        assert pipeline.source_collector is not None
        assert pipeline.audio_generator is not None
        assert pipeline.stage_modes["stage1"] == "auto"

    def test_custom_components(self):
        """Pipeline accepts custom DI components."""
        mock_collector = MagicMock()
        pipeline = ModularVideoPipeline(source_collector=mock_collector)
        assert pipeline.source_collector is mock_collector


# ---------------------------------------------------------------------------
# Pipeline.run — legacy path (no script_provider/voice_pipeline)
# ---------------------------------------------------------------------------

class TestPipelineRunLegacy:
    @pytest.mark.asyncio
    async def test_run_upload_skipped(self):
        """Pipeline run with upload=False skips stage3."""
        mock_collector = AsyncMock()
        mock_collector.collect_sources.return_value = [MagicMock()]
        mock_audio = AsyncMock()
        mock_audio.generate_audio.return_value = _make_audio_info()
        mock_transcript = AsyncMock()
        mock_transcript.process_audio.return_value = _make_transcript()
        mock_slides = AsyncMock()
        mock_slides.generate_slides.return_value = _make_slides_pkg()
        mock_planner = AsyncMock()
        mock_planner.build_plan.return_value = {}
        mock_backend = AsyncMock()
        mock_backend.render.return_value = _make_video_info()

        pipeline = ModularVideoPipeline(
            source_collector=mock_collector,
            audio_generator=mock_audio,
            transcript_processor=mock_transcript,
            slide_generator=mock_slides,
            timeline_planner=mock_planner,
            editing_backend=mock_backend,
        )

        with patch("src.core.pipeline.create_directories"):
            result = await pipeline.run(
                topic="test",
                upload=False,
            )
            assert result["success"] is True
            assert result["youtube_url"] is None

    @pytest.mark.asyncio
    async def test_run_source_collection_failure(self):
        """PipelineError raised on source collection failure."""
        mock_collector = AsyncMock()
        mock_collector.collect_sources.side_effect = RuntimeError("network error")

        pipeline = ModularVideoPipeline(source_collector=mock_collector)

        with patch("src.core.pipeline.create_directories"), \
             pytest.raises(PipelineError):
            await pipeline.run(topic="test", upload=False)

    @pytest.mark.asyncio
    async def test_run_with_progress_callback(self):
        """Progress callback is called throughout the run."""
        mock_collector = AsyncMock()
        mock_collector.collect_sources.return_value = [MagicMock()]
        mock_audio = AsyncMock()
        mock_audio.generate_audio.return_value = _make_audio_info()
        mock_transcript = AsyncMock()
        mock_transcript.process_audio.return_value = _make_transcript()
        mock_slides = AsyncMock()
        mock_slides.generate_slides.return_value = _make_slides_pkg()
        mock_planner = AsyncMock()
        mock_planner.build_plan.return_value = {}
        mock_backend = AsyncMock()
        mock_backend.render.return_value = _make_video_info()
        progress_cb = MagicMock()

        pipeline = ModularVideoPipeline(
            source_collector=mock_collector,
            audio_generator=mock_audio,
            transcript_processor=mock_transcript,
            slide_generator=mock_slides,
            timeline_planner=mock_planner,
            editing_backend=mock_backend,
        )

        with patch("src.core.pipeline.create_directories"):
            result = await pipeline.run(
                topic="test",
                upload=False,
                progress_callback=progress_cb,
            )
            assert progress_cb.call_count >= 5  # Multiple progress updates

    @pytest.mark.asyncio
    async def test_run_with_stage_modes(self):
        """Stage modes are applied from kwargs."""
        mock_collector = AsyncMock()
        mock_collector.collect_sources.return_value = [MagicMock()]
        mock_audio = AsyncMock()
        mock_audio.generate_audio.return_value = _make_audio_info()
        mock_transcript = AsyncMock()
        mock_transcript.process_audio.return_value = _make_transcript()
        mock_slides = AsyncMock()
        mock_slides.generate_slides.return_value = _make_slides_pkg()
        mock_planner = AsyncMock()
        mock_planner.build_plan.return_value = {}
        mock_backend = AsyncMock()
        mock_backend.render.return_value = _make_video_info()

        pipeline = ModularVideoPipeline(
            source_collector=mock_collector,
            audio_generator=mock_audio,
            transcript_processor=mock_transcript,
            slide_generator=mock_slides,
            timeline_planner=mock_planner,
            editing_backend=mock_backend,
        )

        with patch("src.core.pipeline.create_directories"):
            await pipeline.run(
                topic="test",
                upload=False,
                stage_modes={"stage1": "manual", "stage2": "fast"},
            )
            assert pipeline.stage_modes["stage1"] == "manual"
            assert pipeline.stage_modes["stage2"] == "fast"


# ---------------------------------------------------------------------------
# Pipeline.run — modular path (with script_provider + voice_pipeline)
# ---------------------------------------------------------------------------

class TestPipelineRunModular:
    @pytest.mark.asyncio
    async def test_run_modular_path(self):
        """When script_provider and voice_pipeline are set, uses modular path."""
        mock_collector = AsyncMock()
        mock_collector.collect_sources.return_value = [MagicMock()]
        mock_script = AsyncMock()
        mock_script.generate_script.return_value = {"title": "test", "segments": []}
        mock_voice = AsyncMock()
        mock_voice.synthesize.return_value = _make_audio_info()
        mock_transcript = AsyncMock()
        mock_transcript.process_audio.return_value = _make_transcript()
        mock_slides = AsyncMock()
        mock_slides.generate_slides.return_value = _make_slides_pkg()
        mock_planner = AsyncMock()
        mock_planner.build_plan.return_value = {}
        mock_backend = AsyncMock()
        mock_backend.render.return_value = _make_video_info()
        mock_adapter_mgr = AsyncMock()
        mock_adapter_mgr.normalize_script.return_value = {"title": "normalized"}

        pipeline = ModularVideoPipeline(
            source_collector=mock_collector,
            script_provider=mock_script,
            voice_pipeline=mock_voice,
            transcript_processor=mock_transcript,
            slide_generator=mock_slides,
            timeline_planner=mock_planner,
            editing_backend=mock_backend,
        )
        pipeline.content_adapter_manager = mock_adapter_mgr

        with patch("src.core.pipeline.create_directories"):
            result = await pipeline.run(topic="test", upload=False)
            assert result["success"] is True
            mock_script.generate_script.assert_called_once()
            mock_voice.synthesize.assert_called_once()


# ---------------------------------------------------------------------------
# Private retry/fallback methods
# ---------------------------------------------------------------------------

class TestPipelineInternals:
    @pytest.mark.asyncio
    async def test_generate_script_no_provider_raises(self):
        """_generate_script_with_retry raises when no provider."""
        pipeline = ModularVideoPipeline()
        pipeline.script_provider = None
        with pytest.raises(PipelineError, match="script_provider"):
            await pipeline._generate_script_with_retry(topic="t", sources=[], mode="auto")

    @pytest.mark.asyncio
    async def test_synthesize_audio_no_pipeline_raises(self):
        """_synthesize_audio_with_retry raises when no voice_pipeline."""
        pipeline = ModularVideoPipeline()
        pipeline.voice_pipeline = None
        with pytest.raises(PipelineError, match="voice_pipeline"):
            await pipeline._synthesize_audio_with_retry(script={}, provider="none")

    @pytest.mark.asyncio
    async def test_normalize_script_passthrough(self):
        """_normalize_script_with_fallback returns raw when no manager."""
        pipeline = ModularVideoPipeline()
        pipeline.content_adapter_manager = None
        result = await pipeline._normalize_script_with_fallback({"raw": True})
        assert result == {"raw": True}
