"""Tests for src/core/stage_runners.py."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.stage_runners import (
    run_legacy_stage1,
    run_legacy_stage1_with_fallback,
    run_stage2_video_render,
    run_stage3_upload,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_audio_info(**kwargs):
    """Create a minimal AudioInfo-like object."""
    ai = MagicMock()
    ai.file_path = kwargs.get("file_path", Path("/fake/audio.wav"))
    return ai


def _make_video_info(**kwargs):
    vi = MagicMock()
    vi.file_path = kwargs.get("file_path", Path("/fake/video.mp4"))
    return vi


def _make_transcript(**kwargs):
    t = MagicMock()
    t.title = kwargs.get("title", "Test Transcript")
    t.segments = kwargs.get("segments", [])
    return t


def _make_slides_pkg(**kwargs):
    s = MagicMock()
    s.total_slides = kwargs.get("total_slides", 5)
    s.file_path = kwargs.get("file_path", Path("/fake/slides"))
    return s


def _make_source(**kwargs):
    s = MagicMock()
    s.url = kwargs.get("url", "https://example.com")
    s.title = kwargs.get("title", "Source")
    s.content_preview = kwargs.get("content_preview", "preview")
    s.relevance_score = kwargs.get("relevance_score", 0.8)
    s.reliability_score = kwargs.get("reliability_score", 0.9)
    return s


# ---------------------------------------------------------------------------
# run_legacy_stage1
# ---------------------------------------------------------------------------

class TestRunLegacyStage1:
    @pytest.mark.asyncio
    async def test_no_gemini_key(self):
        """Without GEMINI_API_KEY, falls back to audio_generator only."""
        mock_audio_gen = AsyncMock()
        mock_audio_gen.generate_audio.return_value = _make_audio_info()

        with patch("src.core.stage_runners.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            script_bundle, audio_info = await run_legacy_stage1(
                topic="test",
                sources=[_make_source()],
                audio_generator=mock_audio_gen,
            )
            assert script_bundle is None
            mock_audio_gen.generate_audio.assert_called_once()

    @pytest.mark.asyncio
    async def test_gemini_key_but_error(self):
        """With GEMINI_API_KEY but Gemini fails, still returns audio."""
        mock_audio_gen = AsyncMock()
        mock_audio_gen.generate_audio.return_value = _make_audio_info()

        with patch("src.core.stage_runners.settings") as mock_settings, \
             patch("src.core.stage_runners.GeminiIntegration") as mock_gemini_cls:
            mock_settings.GEMINI_API_KEY = "test_key"
            mock_settings.YOUTUBE_SETTINGS = {"default_language": "ja"}
            mock_settings.SCRIPTS_DIR = Path("/tmp/scripts")
            mock_gemini = AsyncMock()
            mock_gemini.generate_script_from_sources.side_effect = RuntimeError("API error")
            mock_gemini_cls.return_value = mock_gemini

            script_bundle, audio_info = await run_legacy_stage1(
                topic="test",
                sources=[_make_source()],
                audio_generator=mock_audio_gen,
            )
            # Falls back, script_bundle is None
            assert script_bundle is None
            mock_audio_gen.generate_audio.assert_called_once()


# ---------------------------------------------------------------------------
# run_legacy_stage1_with_fallback
# ---------------------------------------------------------------------------

class TestRunLegacyStage1Transcript:
    """transcript_text パス (根本ワークフロー) のテスト"""

    @pytest.mark.asyncio
    async def test_transcript_path_no_api_key(self):
        """APIキーなしでもtranscript_textを渡せること（モックフォールバック経由）"""
        mock_audio_gen = AsyncMock()
        mock_audio_gen.generate_audio.return_value = _make_audio_info()

        with patch("src.core.stage_runners.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            with patch.dict("os.environ", {"LLM_API_KEY": ""}, clear=False):
                script_bundle, audio_info = await run_legacy_stage1(
                    topic="test",
                    sources=[_make_source()],
                    audio_generator=mock_audio_gen,
                    transcript_text="Host1: テスト " * 20,
                )
                # No API key → script_bundle is None (transcript path requires LLM)
                assert script_bundle is None

    @pytest.mark.asyncio
    async def test_transcript_kwarg_accepted(self):
        """transcript_text がキーワード引数として受け入れられること"""
        mock_audio_gen = AsyncMock()
        mock_audio_gen.generate_audio.return_value = _make_audio_info()

        with patch("src.core.stage_runners.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            with patch.dict("os.environ", {"LLM_API_KEY": ""}, clear=False):
                # transcript_text=None は従来動作と同じ
                script_bundle, audio_info = await run_legacy_stage1(
                    topic="test",
                    sources=[_make_source()],
                    audio_generator=mock_audio_gen,
                    transcript_text=None,
                )
                assert audio_info is not None


class TestRunLegacyStage1WithFallback:
    @pytest.mark.asyncio
    async def test_success_passthrough(self):
        """Success case delegates to run_legacy_stage1."""
        mock_audio_gen = AsyncMock()
        mock_audio_gen.generate_audio.return_value = _make_audio_info()

        with patch("src.core.stage_runners.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            script_bundle, audio_info = await run_legacy_stage1_with_fallback(
                topic="test",
                sources=[],
                audio_generator=mock_audio_gen,
            )
            assert script_bundle is None

    @pytest.mark.asyncio
    async def test_fallback_on_exception(self):
        """When run_legacy_stage1 raises, falls back gracefully."""
        mock_audio_gen = AsyncMock()
        mock_audio_gen.generate_audio.return_value = _make_audio_info()

        with patch("src.core.stage_runners.run_legacy_stage1", side_effect=RuntimeError("fail")):
            script_bundle, audio_info = await run_legacy_stage1_with_fallback(
                topic="test",
                sources=[],
                audio_generator=mock_audio_gen,
            )
            assert script_bundle is None
            mock_audio_gen.generate_audio.assert_called_once()


# ---------------------------------------------------------------------------
# run_stage2_video_render
# ---------------------------------------------------------------------------

class TestRunStage2VideoRender:
    @pytest.mark.asyncio
    async def test_with_timeline_and_backend(self):
        """Normal path with timeline_planner and editing_backend."""
        mock_planner = AsyncMock()
        mock_planner.build_plan.return_value = {"segments": []}
        mock_backend = AsyncMock()
        mock_backend.render.return_value = _make_video_info()
        mock_cb = MagicMock()

        video_info, thumb, plan, outputs = await run_stage2_video_render(
            audio_info=_make_audio_info(),
            slides_pkg=_make_slides_pkg(),
            transcript=_make_transcript(),
            quality="1080p",
            script_bundle={"title": "test"},
            user_preferences=None,
            stage2_mode="auto",
            timeline_planner=mock_planner,
            editing_backend=mock_backend,
            progress_callback=mock_cb,
        )
        mock_planner.build_plan.assert_called_once()
        mock_backend.render.assert_called_once()
        assert video_info is not None

    @pytest.mark.asyncio
    async def test_missing_planner_raises(self):
        """Without timeline_planner/editing_backend, raises ValueError."""
        with pytest.raises(ValueError, match="timeline_planner"):
            await run_stage2_video_render(
                audio_info=_make_audio_info(),
                slides_pkg=_make_slides_pkg(),
                transcript=_make_transcript(),
                quality="1080p",
                script_bundle=None,
                user_preferences=None,
                stage2_mode="auto",
                timeline_planner=None,
                editing_backend=None,
            )

    @pytest.mark.asyncio
    async def test_with_thumbnail_generator(self):
        """Thumbnail generation when enabled in user_preferences."""
        mock_planner = AsyncMock()
        mock_planner.build_plan.return_value = {}
        mock_backend = AsyncMock()
        mock_backend.render.return_value = _make_video_info()
        mock_thumb = AsyncMock()
        thumb_result = MagicMock()
        thumb_result.file_path = Path("/fake/thumb.png")
        mock_thumb.generate.return_value = thumb_result

        video_info, thumb, plan, outputs = await run_stage2_video_render(
            audio_info=_make_audio_info(),
            slides_pkg=_make_slides_pkg(),
            transcript=_make_transcript(),
            quality="1080p",
            script_bundle=None,
            user_preferences={"generate_thumbnail": True, "thumbnail_style": "modern"},
            stage2_mode="auto",
            timeline_planner=mock_planner,
            editing_backend=mock_backend,
            thumbnail_generator=mock_thumb,
        )
        mock_thumb.generate.assert_called_once()
        assert thumb == Path("/fake/thumb.png")

    @pytest.mark.asyncio
    async def test_thumbnail_failure_graceful(self):
        """Thumbnail generation failure doesn't break the pipeline."""
        mock_planner = AsyncMock()
        mock_planner.build_plan.return_value = {}
        mock_backend = AsyncMock()
        mock_backend.render.return_value = _make_video_info()
        mock_thumb = AsyncMock()
        mock_thumb.generate.side_effect = RuntimeError("thumb error")

        video_info, thumb, plan, outputs = await run_stage2_video_render(
            audio_info=_make_audio_info(),
            slides_pkg=_make_slides_pkg(),
            transcript=_make_transcript(),
            quality="1080p",
            script_bundle=None,
            user_preferences={"generate_thumbnail": True},
            stage2_mode="auto",
            timeline_planner=mock_planner,
            editing_backend=mock_backend,
            thumbnail_generator=mock_thumb,
        )
        assert thumb is None  # Graceful fallback


# ---------------------------------------------------------------------------
# run_stage3_upload
# ---------------------------------------------------------------------------

class TestRunStage3Upload:
    @pytest.mark.asyncio
    async def test_with_platform_adapter(self):
        """Upload via platform_adapter path."""
        mock_meta = AsyncMock()
        mock_meta.generate_metadata.return_value = {"title": "test"}
        mock_adapter = AsyncMock()
        mock_adapter.publish.return_value = {"url": "https://youtube.com/test"}
        mock_cb = MagicMock()

        with patch("src.core.stage_runners.settings") as mock_settings:
            mock_settings.YOUTUBE_SETTINGS = {"default_language": "ja"}
            result = await run_stage3_upload(
                video_info=_make_video_info(),
                transcript=_make_transcript(),
                thumbnail_path=None,
                private_upload=True,
                stage3_mode="auto",
                user_preferences=None,
                metadata_generator=mock_meta,
                platform_adapter=mock_adapter,
                progress_callback=mock_cb,
            )
            upload_result, youtube_url, metadata, pub_result = result
            assert youtube_url == "https://youtube.com/test"
            mock_adapter.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_uploader(self):
        """Upload via legacy uploader path."""
        mock_meta = AsyncMock()
        mock_meta.generate_metadata.return_value = {"title": "test"}
        mock_uploader = AsyncMock()
        upload_res = MagicMock()
        upload_res.video_url = "https://youtube.com/direct"
        mock_uploader.upload_video.return_value = upload_res

        with patch("src.core.stage_runners.settings") as mock_settings:
            mock_settings.YOUTUBE_SETTINGS = {"default_language": "ja"}
            result = await run_stage3_upload(
                video_info=_make_video_info(),
                transcript=_make_transcript(),
                thumbnail_path=None,
                private_upload=False,
                stage3_mode="auto",
                user_preferences=None,
                metadata_generator=mock_meta,
                uploader=mock_uploader,
            )
            _, youtube_url, metadata, _ = result
            assert youtube_url == "https://youtube.com/direct"
            assert metadata["privacy_status"] == "public"

    @pytest.mark.asyncio
    async def test_no_uploader_raises(self):
        """Without platform_adapter or uploader, raises ValueError."""
        mock_meta = AsyncMock()
        mock_meta.generate_metadata.return_value = {"title": "test"}

        with patch("src.core.stage_runners.settings") as mock_settings:
            mock_settings.YOUTUBE_SETTINGS = {"default_language": "ja"}
            with pytest.raises(ValueError, match="uploader is required"):
                await run_stage3_upload(
                    video_info=_make_video_info(),
                    transcript=_make_transcript(),
                    thumbnail_path=None,
                    private_upload=True,
                    stage3_mode="auto",
                    user_preferences=None,
                    metadata_generator=mock_meta,
                    platform_adapter=None,
                    uploader=None,
                )

