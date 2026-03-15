"""AIImageProvider テスト (SP-033 Phase 3)"""
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.visual.ai_image_provider import AIImageProvider, GeneratedImage


class TestGeneratedImage:
    def test_defaults(self) -> None:
        img = GeneratedImage(prompt="test prompt")
        assert img.prompt == "test prompt"
        assert img.image_path is None
        assert img.source == "ai"
        assert img.error is None
        assert img.mime_type == "image/png"

    def test_with_error(self) -> None:
        img = GeneratedImage(prompt="p", error="no_api_key")
        assert img.error == "no_api_key"
        assert img.image_path is None


class TestBuildPrompt:
    """_build_prompt のプロンプト構築ロジック。"""

    @pytest.fixture
    def provider(self, tmp_path: Path) -> AIImageProvider:
        with patch("core.visual.ai_image_provider.AIImageProvider.__init__", return_value=None):
            p = AIImageProvider.__new__(AIImageProvider)
            p.api_key = "test_key"
            p.cache_dir = tmp_path
            p.model = "test-model"
            p.aspect_ratio = "16:9"
            return p

    def test_key_points_priority(self, provider: AIImageProvider) -> None:
        seg = {"key_points": ["quantum computing", "AI"], "section": "intro", "content": "text"}
        prompt = provider._build_prompt(seg, topic="tech", style_hint="clean")
        assert "quantum computing, AI" in prompt
        assert "Topic: tech" in prompt

    def test_section_fallback(self, provider: AIImageProvider) -> None:
        seg = {"section": "conclusion", "content": "some text"}
        prompt = provider._build_prompt(seg, topic="", style_hint="")
        assert "Subject: conclusion" in prompt

    def test_content_fallback(self, provider: AIImageProvider) -> None:
        seg = {"content": "A very long content text here"}
        prompt = provider._build_prompt(seg, topic="", style_hint="")
        assert "Subject: A very long content" in prompt

    def test_empty_segment_uses_topic(self, provider: AIImageProvider) -> None:
        seg = {}
        prompt = provider._build_prompt(seg, topic="science", style_hint="")
        assert "Subject: science" in prompt

    def test_no_watermark_instruction(self, provider: AIImageProvider) -> None:
        seg = {"key_points": ["test"]}
        prompt = provider._build_prompt(seg, topic="", style_hint="")
        assert "No text or watermarks" in prompt


class TestCache:
    """キャッシュの読み書きテスト。"""

    @pytest.fixture
    def provider(self, tmp_path: Path) -> AIImageProvider:
        with patch("core.visual.ai_image_provider.AIImageProvider.__init__", return_value=None):
            p = AIImageProvider.__new__(AIImageProvider)
            p.api_key = "test_key"
            p.cache_dir = tmp_path
            p.model = "test-model"
            p.aspect_ratio = "16:9"
            return p

    def test_cache_miss(self, provider: AIImageProvider) -> None:
        result = provider._check_cache("nonexistent prompt")
        assert result is None

    def test_cache_hit(self, provider: AIImageProvider, tmp_path: Path) -> None:
        prompt = "test prompt for cache"
        cache_key = hashlib.md5(prompt.encode()).hexdigest()[:12]
        cache_file = tmp_path / f"ai_{cache_key}.png"
        cache_file.write_bytes(b"fake_png_data")

        result = provider._check_cache(prompt)
        assert result is not None
        assert result.image_path == cache_file
        assert result.source == "ai_cache"


class TestGenerateForSegments:
    """generate_for_segments の統合テスト (API モック)。"""

    @pytest.fixture
    def provider(self, tmp_path: Path) -> AIImageProvider:
        with patch("core.visual.ai_image_provider.AIImageProvider.__init__", return_value=None):
            p = AIImageProvider.__new__(AIImageProvider)
            p.api_key = "test_key"
            p.cache_dir = tmp_path
            p.model = "test-model"
            p.aspect_ratio = "16:9"
            return p

    def test_no_api_key_returns_errors(self, tmp_path: Path) -> None:
        with patch("core.visual.ai_image_provider.AIImageProvider.__init__", return_value=None):
            p = AIImageProvider.__new__(AIImageProvider)
            p.api_key = ""
            p.cache_dir = tmp_path
            p.model = "test-model"
            p.aspect_ratio = "16:9"

        segments = [{"content": "test1"}, {"content": "test2"}]
        results = p.generate_for_segments(segments)
        assert len(results) == 2
        assert all(r.error == "no_api_key" for r in results)

    @patch("time.sleep")
    def test_successful_generation(self, mock_sleep, provider: AIImageProvider, tmp_path: Path) -> None:
        fake_path = tmp_path / "generated.png"
        fake_path.write_bytes(b"fake")

        with patch.object(
            provider, "_generate_with_retry",
            return_value=GeneratedImage(prompt="p", image_path=fake_path),
        ):
            segments = [{"key_points": ["AI"]}, {"key_points": ["ML"]}]
            results = provider.generate_for_segments(segments, topic="tech")

        assert len(results) == 2
        assert all(r.image_path == fake_path for r in results)

    def test_cached_segments_skip_api(self, provider: AIImageProvider, tmp_path: Path) -> None:
        # プロンプトに対応するキャッシュファイルを事前に作成
        seg = {"key_points": ["quantum"]}
        prompt = provider._build_prompt(seg, "tech", "clean, professional illustration for educational video")
        cache_key = hashlib.md5(prompt.encode()).hexdigest()[:12]
        cache_file = tmp_path / f"ai_{cache_key}.png"
        cache_file.write_bytes(b"cached_data")

        with patch.object(provider, "_generate_with_retry") as mock_gen:
            results = provider.generate_for_segments([seg], topic="tech")

        # キャッシュヒット → API呼び出しなし
        mock_gen.assert_not_called()
        assert len(results) == 1
        assert results[0].image_path == cache_file


class TestGenerateWithRetry:
    """リトライロジックのテスト。"""

    @pytest.fixture
    def provider(self, tmp_path: Path) -> AIImageProvider:
        with patch("core.visual.ai_image_provider.AIImageProvider.__init__", return_value=None):
            p = AIImageProvider.__new__(AIImageProvider)
            p.api_key = "test_key"
            p.cache_dir = tmp_path
            p.model = "test-model"
            p.aspect_ratio = "16:9"
            return p

    @patch("time.sleep")
    def test_400_error_no_retry(self, mock_sleep, provider: AIImageProvider) -> None:
        mock_api = MagicMock(side_effect=Exception("400 Bad Request"))
        with patch.object(provider, "_call_api", mock_api):
            result = provider._generate_with_retry("bad prompt")

        assert result.error is not None
        assert "prompt_error" in result.error
        # 400エラーは即座にリターン (リトライなし)
        mock_api.assert_called_once()

    @patch("time.sleep")
    def test_429_retries_with_backoff(self, mock_sleep, provider: AIImageProvider) -> None:
        fake_result = GeneratedImage(prompt="p", image_path=Path("/tmp/ok.png"))
        mock_api = MagicMock(
            side_effect=[Exception("429 Too Many Requests"), fake_result],
        )
        with patch.object(provider, "_call_api", mock_api):
            result = provider._generate_with_retry("prompt")

        assert result.image_path is not None
        assert mock_api.call_count == 2

    @patch("time.sleep")
    def test_max_retries_exceeded(self, mock_sleep, provider: AIImageProvider) -> None:
        mock_api = MagicMock(side_effect=Exception("500 Server Error"))
        with patch.object(provider, "_call_api", mock_api):
            result = provider._generate_with_retry("prompt")

        assert result.error is not None
