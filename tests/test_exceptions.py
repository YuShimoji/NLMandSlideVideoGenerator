"""例外階層テスト"""
import pytest

from core.exceptions import (
    APIAuthenticationError,
    AudioGenerationError,
    ConfigurationError,
    PipelineError,
    QuotaExceededError,
    ScriptGenerationError,
    SlideGenerationError,
    UploadError,
    VideoCompositionError,
)


class TestPipelineError:
    def test_basic_attributes(self):
        err = PipelineError("something failed", stage="script", recoverable=True)
        assert str(err) == "something failed"
        assert err.stage == "script"
        assert err.recoverable is True

    def test_default_user_message_with_known_stage(self):
        err = PipelineError("internal", stage="voice")
        assert "音声" in err.user_message

    def test_default_user_message_unknown_stage(self):
        err = PipelineError("internal", stage="unknown_stage")
        assert "エラーが発生しました" in err.user_message

    def test_custom_user_message(self):
        err = PipelineError("internal", user_message="カスタムメッセージ")
        assert err.user_message == "カスタムメッセージ"

    def test_is_exception(self):
        with pytest.raises(PipelineError):
            raise PipelineError("test")


class TestSubclasses:
    """各サブクラスの stage/recoverable デフォルト値を確認"""

    def test_script_generation_error(self):
        err = ScriptGenerationError("fail")
        assert err.stage == "script"
        assert err.recoverable is True
        assert isinstance(err, PipelineError)

    def test_audio_generation_error(self):
        err = AudioGenerationError("fail")
        assert err.stage == "voice"
        assert err.recoverable is True

    def test_slide_generation_error(self):
        err = SlideGenerationError("fail")
        assert err.stage == "slides"
        assert err.recoverable is True

    def test_video_composition_error(self):
        err = VideoCompositionError("fail")
        assert err.stage == "video"
        assert err.recoverable is False  # デフォルト False

    def test_upload_error(self):
        err = UploadError("fail")
        assert err.stage == "upload"
        assert err.recoverable is True


class TestQuotaExceededError:
    def test_inherits_upload_error(self):
        err = QuotaExceededError("quota hit")
        assert isinstance(err, UploadError)
        assert isinstance(err, PipelineError)

    def test_not_recoverable(self):
        err = QuotaExceededError("quota hit")
        assert err.recoverable is False

    def test_default_user_message(self):
        err = QuotaExceededError("quota")
        assert "利用制限" in err.user_message


class TestAPIAuthenticationError:
    def test_service_attribute(self):
        err = APIAuthenticationError("bad key", service="YouTube")
        assert err.service == "YouTube"
        assert err.stage == "auth"
        assert err.recoverable is False

    def test_user_message_includes_service(self):
        err = APIAuthenticationError("bad key", service="Gemini")
        assert "Gemini" in err.user_message


class TestConfigurationError:
    def test_defaults(self):
        err = ConfigurationError("missing config")
        assert err.stage == "config"
        assert err.recoverable is False
        assert "設定" in err.user_message
