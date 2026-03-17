"""Tests for src/main.py — VideoGenerationPipeline and CLI entry point."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.main import VideoGenerationPipeline, main


def _close_and_raise(coro):
    """Close unawaited coroutine to suppress RuntimeWarning, then raise."""
    if hasattr(coro, "close"):
        coro.close()
    raise RuntimeError("非推奨")


# ---------------------------------------------------------------------------
# VideoGenerationPipeline
# ---------------------------------------------------------------------------

class TestVideoGenerationPipeline:
    def test_init(self):
        """Pipeline initializes all sub-components."""
        pipeline = VideoGenerationPipeline()
        assert pipeline.source_collector is not None
        assert pipeline.audio_generator is not None
        assert pipeline.transcript_processor is not None
        assert pipeline.slide_generator is not None
        assert pipeline.youtube_uploader is not None
        assert pipeline.metadata_generator is not None

    @pytest.mark.asyncio
    async def test_generate_video_raises_deprecation(self):
        """generate_video raises RuntimeError (deprecated, use ModularVideoPipeline)."""
        pipeline = VideoGenerationPipeline()
        pipeline.source_collector = AsyncMock()
        pipeline.source_collector.collect_sources.return_value = [MagicMock()]
        pipeline.audio_generator = AsyncMock()
        pipeline.audio_generator.generate_audio.return_value = MagicMock(file_path=Path("/fake"))
        pipeline.transcript_processor = AsyncMock()
        pipeline.transcript_processor.process_audio.return_value = MagicMock(title="test")
        pipeline.slide_generator = AsyncMock()
        pipeline.slide_generator.generate_slides.return_value = MagicMock()

        with pytest.raises(RuntimeError, match="非推奨"):
            await pipeline.generate_video(topic="test topic")


# ---------------------------------------------------------------------------
# CLI main()
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_with_topic(self):
        """main() parses --topic and runs (will fail with RuntimeError from pipeline)."""
        test_args = ["main.py", "--topic", "AI basics", "--debug"]
        with patch.object(sys, "argv", test_args), \
             patch("src.main.create_directories"), \
             patch("src.main.asyncio") as mock_asyncio:
            mock_asyncio.run.side_effect = _close_and_raise
            # Should print error but not crash in non-debug mode
            # In debug mode it re-raises, so let's test non-debug
            test_args_nodebug = ["main.py", "--topic", "AI basics"]
            with patch.object(sys, "argv", test_args_nodebug):
                main()  # Should not raise, prints error

    def test_main_with_max_chars(self):
        """main() applies --max-chars-per-slide option."""
        test_args = ["main.py", "--topic", "test", "--max-chars-per-slide", "50"]
        with patch.object(sys, "argv", test_args), \
             patch("src.main.create_directories"), \
             patch("src.main.asyncio") as mock_asyncio:
            mock_asyncio.run.side_effect = _close_and_raise
            main()  # Should not raise

    def test_main_with_urls(self):
        """main() accepts --urls."""
        test_args = ["main.py", "--topic", "test", "--urls", "https://a.com", "https://b.com"]
        with patch.object(sys, "argv", test_args), \
             patch("src.main.create_directories"), \
             patch("src.main.asyncio") as mock_asyncio:
            mock_asyncio.run.side_effect = _close_and_raise
            main()

    def test_main_debug_reraises(self):
        """In debug mode, exceptions are re-raised."""
        test_args = ["main.py", "--topic", "test", "--debug"]
        with patch.object(sys, "argv", test_args), \
             patch("src.main.create_directories"), \
             patch("src.main.asyncio") as mock_asyncio:
            mock_asyncio.run.side_effect = _close_and_raise
            with pytest.raises(RuntimeError):
                main()
