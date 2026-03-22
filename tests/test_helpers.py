"""helpers テスト — with_fallback / build_default_pipeline"""
from unittest.mock import patch, MagicMock

import pytest

from core.helpers import with_fallback, build_default_pipeline
from core.exceptions import PipelineError


# ---------------------------------------------------------------------------
# with_fallback
# ---------------------------------------------------------------------------
class TestWithFallback:
    def test_primary_succeeds(self):
        result = with_fallback(lambda x: x * 2, lambda x: x * 3, 5)
        assert result == 10

    def test_fallback_on_value_error(self):
        def bad(x):
            raise ValueError("boom")

        result = with_fallback(bad, lambda x: x + 1, 5)
        assert result == 6

    def test_fallback_on_os_error(self):
        def bad(x):
            raise OSError("disk")

        result = with_fallback(bad, lambda x: "ok", 1)
        assert result == "ok"

    def test_fallback_on_generic_exception(self):
        """Exception サブクラスでもフォールバックが動く"""
        def bad(x):
            raise RuntimeError("generic")

        result = with_fallback(bad, lambda x: "recovered", 1)
        assert result == "recovered"

    def test_both_fail_raises_pipeline_error(self):
        def bad1(x):
            raise ValueError("primary fail")

        def bad2(x):
            raise TypeError("fallback fail")

        with pytest.raises(PipelineError, match="Both primary and fallback failed"):
            with_fallback(bad1, bad2, 1)

    def test_pipeline_error_not_recoverable(self):
        def bad1(x):
            raise ValueError("p")

        def bad2(x):
            raise ValueError("f")

        with pytest.raises(PipelineError) as exc_info:
            with_fallback(bad1, bad2, 1)
        assert exc_info.value.recoverable is False

    def test_kwargs_forwarded(self):
        def fn(a, b=10):
            return a + b

        result = with_fallback(fn, fn, 1, b=20)
        assert result == 21

    def test_primary_specific_fallback_generic_exception(self):
        """Primary raises specific exception, fallback raises generic Exception."""
        class CustomError(Exception):
            pass

        def bad1(x):
            raise ValueError("primary")

        def bad2(x):
            raise CustomError("fallback generic")

        with pytest.raises(PipelineError, match="Both primary and fallback failed"):
            with_fallback(bad1, bad2, 1)

    def test_primary_generic_fallback_specific_exception(self):
        """Primary raises generic Exception, fallback raises specific exception."""
        class CustomError(Exception):
            pass

        def bad1(x):
            raise CustomError("primary generic")

        def bad2(x):
            raise ValueError("fallback specific")

        with pytest.raises(PipelineError, match="Both primary and fallback failed"):
            with_fallback(bad1, bad2, 1)

    def test_primary_generic_fallback_generic_exception(self):
        """Primary raises generic Exception, fallback raises generic Exception."""
        class CustomError1(Exception):
            pass

        class CustomError2(Exception):
            pass

        def bad1(x):
            raise CustomError1("primary")

        def bad2(x):
            raise CustomError2("fallback")

        with pytest.raises(PipelineError, match="Both primary and fallback failed"):
            with_fallback(bad1, bad2, 1)

    def test_primary_generic_exception_fallback_succeeds(self):
        """Primary raises non-standard Exception, fallback succeeds."""
        class CustomError(Exception):
            pass

        def bad(x):
            raise CustomError("primary")

        result = with_fallback(bad, lambda x: "recovered", 1)
        assert result == "recovered"


# ---------------------------------------------------------------------------
# build_default_pipeline
# ---------------------------------------------------------------------------
def _base_components(**overrides):
    defaults = {
        "script_provider": "legacy",
        "voice_pipeline": "none",
        "editing_backend": "none",
        "platform_adapter": "none",
        "thumbnail_generator": "none",
    }
    defaults.update(overrides)
    return defaults


class TestBuildDefaultPipeline:
    @patch("core.helpers.settings")
    def test_returns_pipeline_instance(self, mock_settings):
        mock_settings.PIPELINE_STAGE_MODES = {"stage1": "auto", "stage2": "auto", "stage3": "auto"}
        mock_settings.PIPELINE_COMPONENTS = _base_components()
        mock_settings.GEMINI_API_KEY = ""

        pipeline = build_default_pipeline()

        from core.pipeline import ModularVideoPipeline
        assert isinstance(pipeline, ModularVideoPipeline)

    @patch("core.helpers.settings")
    def test_ymm4_backend_configured(self, mock_settings):
        mock_settings.PIPELINE_STAGE_MODES = {"stage1": "auto", "stage2": "auto", "stage3": "auto"}
        mock_settings.PIPELINE_COMPONENTS = _base_components(editing_backend="ymm4")
        mock_settings.GEMINI_API_KEY = ""
        mock_settings.TEMPLATES_DIR = MagicMock()
        mock_settings.DATA_DIR = MagicMock()
        mock_settings.YMM4_SETTINGS = {
            "project_template": "/tmp/template.y4mmp",
            "auto_hotkey_script": "/tmp/dummy.ahk",
            "workspace_dir": "/tmp/ymm4",
        }

        pipeline = build_default_pipeline()
        assert pipeline.editing_backend is not None

    @patch("core.helpers.settings")
    def test_gemini_provider_configured(self, mock_settings):
        mock_settings.PIPELINE_STAGE_MODES = {}
        mock_settings.PIPELINE_COMPONENTS = _base_components(script_provider="gemini")
        mock_settings.GEMINI_API_KEY = "test-key"

        pipeline = build_default_pipeline()
        assert pipeline.script_provider is not None

    @patch("core.helpers.settings")
    def test_gemini_provider_no_key(self, mock_settings):
        mock_settings.PIPELINE_STAGE_MODES = {}
        mock_settings.PIPELINE_COMPONENTS = _base_components(script_provider="gemini")
        mock_settings.GEMINI_API_KEY = ""

        pipeline = build_default_pipeline()
        assert pipeline.script_provider is None

    @patch("core.helpers.settings")
    def test_notebooklm_provider_configured(self, mock_settings):
        mock_settings.PIPELINE_STAGE_MODES = {}
        mock_settings.PIPELINE_COMPONENTS = _base_components(script_provider="notebooklm")
        mock_settings.GEMINI_API_KEY = ""

        pipeline = build_default_pipeline()
        assert pipeline.script_provider is not None

    @patch("core.helpers.settings")
    def test_youtube_adapter_configured(self, mock_settings):
        mock_settings.PIPELINE_STAGE_MODES = {}
        mock_settings.PIPELINE_COMPONENTS = _base_components(platform_adapter="youtube")
        mock_settings.GEMINI_API_KEY = ""

        pipeline = build_default_pipeline()
        assert pipeline.platform_adapter is not None

    @patch("core.helpers.settings")
    def test_template_thumbnail_configured(self, mock_settings):
        mock_settings.PIPELINE_STAGE_MODES = {}
        mock_settings.PIPELINE_COMPONENTS = _base_components(thumbnail_generator="template")
        mock_settings.GEMINI_API_KEY = ""

        pipeline = build_default_pipeline()
        assert pipeline.thumbnail_generator is not None

    @patch("core.helpers.settings")
    def test_ai_thumbnail_configured(self, mock_settings):
        mock_settings.PIPELINE_STAGE_MODES = {}
        mock_settings.PIPELINE_COMPONENTS = _base_components(thumbnail_generator="ai")
        mock_settings.GEMINI_API_KEY = ""

        pipeline = build_default_pipeline()
        assert pipeline.thumbnail_generator is not None
