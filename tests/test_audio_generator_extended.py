"""AudioGenerator テスト (YMM4一本化後)

AudioGenerator はレガシースタブ:
  - generate_audio() はプレースホルダー WAV を生成するだけ
  - regenerate_audio_if_needed() は常に既存の audio_info を返す
  - AudioInfo データクラスの互換性を確認

削除済みシミュレーションメソッドのテストは撤去:
  _upload_sources, _request_audio_generation, _check_generation_status,
  _get_audio_download_url, _wait_for_audio_completion, _download_audio,
  _validate_audio_quality, _calculate_audio_quality
"""

import wave
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# config.settings をモックしてからインポート
_mock_settings = MagicMock()
_mock_settings.NOTEBOOK_LM_SETTINGS = {
    "audio_quality_threshold": 0.7,
    "max_audio_duration": 1800,
    "max_sources": 10,
}
_mock_settings.AUDIO_DIR = Path("/tmp/test_audio_gen")
_mock_settings.GEMINI_API_KEY = ""
_mock_settings.YOUTUBE_SETTINGS = {
    "default_audio_language": "ja",
}

with patch.dict("sys.modules", {
    "config": MagicMock(),
    "config.settings": MagicMock(settings=_mock_settings),
}):
    from notebook_lm.audio_generator import AudioGenerator, AudioInfo
    from notebook_lm.source_collector import SourceInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_source(**overrides) -> SourceInfo:
    defaults = dict(
        url="https://example.com/article",
        title="Test Article",
        content_preview="preview text",
        relevance_score=0.9,
        reliability_score=0.8,
        source_type="web",
    )
    defaults.update(overrides)
    return SourceInfo(**defaults)


# ---------------------------------------------------------------------------
# AudioInfo dataclass
# ---------------------------------------------------------------------------

class TestAudioInfoDataclass:
    def test_creation_minimal(self):
        info = AudioInfo(file_path=Path("/tmp/test.wav"), duration=10.0)
        assert info.file_path == Path("/tmp/test.wav")
        assert info.duration == 10.0
        assert info.quality_score == 1.0
        assert info.sample_rate == 44100
        assert info.language == "ja"

    def test_creation_full(self):
        info = AudioInfo(
            file_path=Path("/tmp/test.wav"),
            duration=60.0,
            quality_score=0.9,
            sample_rate=48000,
            file_size=1024,
            language="en",
            channels=1,
        )
        assert info.sample_rate == 48000
        assert info.language == "en"
        assert info.channels == 1


# ---------------------------------------------------------------------------
# AudioGenerator init
# ---------------------------------------------------------------------------

class TestAudioGeneratorInit:
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    def test_basic_init(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        gen = AudioGenerator()
        assert gen.audio_quality_threshold == 0.7
        assert gen.max_duration == 1800
        assert gen.output_dir.exists()


# ---------------------------------------------------------------------------
# generate_audio (placeholder WAV)
# ---------------------------------------------------------------------------

class TestGenerateAudio:
    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_generates_wav(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        gen = AudioGenerator()
        result = await gen.generate_audio([_make_source()])
        assert isinstance(result, AudioInfo)
        assert result.file_path.exists()
        assert result.duration == 1.0
        assert result.quality_score == 0.5

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_wav_is_valid(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        gen = AudioGenerator()
        result = await gen.generate_audio([_make_source()])
        with wave.open(str(result.file_path), 'rb') as wf:
            assert wf.getnchannels() == 2
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 44100

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_empty_sources(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        gen = AudioGenerator()
        result = await gen.generate_audio([])
        assert result.file_path.exists()


# ---------------------------------------------------------------------------
# regenerate_audio_if_needed (always returns same)
# ---------------------------------------------------------------------------

class TestRegenerateAudio:
    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_returns_same_audio_high_quality(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        gen = AudioGenerator()
        good_audio = AudioInfo(file_path=Path("/a.wav"), duration=10.0, quality_score=0.8)
        result = await gen.regenerate_audio_if_needed(good_audio, [_make_source()])
        assert result is good_audio

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_returns_same_audio_low_quality(self, tmp_path):
        """YMM4一本化: 低品質でも再生成しない"""
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        gen = AudioGenerator()
        bad_audio = AudioInfo(file_path=Path("/a.wav"), duration=10.0, quality_score=0.3)
        result = await gen.regenerate_audio_if_needed(bad_audio, [_make_source()])
        assert result is bad_audio
