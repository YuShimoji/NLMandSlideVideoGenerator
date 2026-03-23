"""AudioGenerator 拡張テスト — カバレッジ 24% → 60%+ を目指す"""

import asyncio
import struct
import time
import wave
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

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


def _write_wav(path: Path, duration_sec: float = 1.0, sample_rate: int = 44100,
               channels: int = 2, sampwidth: int = 2) -> Path:
    """テスト用 WAV ファイルを作成する"""
    path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = int(sample_rate * duration_sec)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        silence = struct.pack("<h", 0) * n_frames * channels
        wf.writeframes(silence)
    return path


# ---------------------------------------------------------------------------
# AudioInfo dataclass
# ---------------------------------------------------------------------------

class TestAudioInfo:
    def test_defaults(self):
        info = AudioInfo(file_path=Path("/a.wav"), duration=5.0)
        assert info.quality_score == 1.0
        assert info.sample_rate == 44100
        assert info.file_size == 0
        assert info.language == "ja"
        assert info.channels == 2

    def test_custom_fields(self):
        info = AudioInfo(
            file_path=Path("/b.wav"), duration=10.0,
            quality_score=0.8, sample_rate=22050,
            file_size=1024, language="en", channels=1,
        )
        assert info.quality_score == 0.8
        assert info.sample_rate == 22050
        assert info.file_size == 1024
        assert info.language == "en"
        assert info.channels == 1


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestAudioGeneratorInit:
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    def test_basic_init(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        gen = AudioGenerator()
        assert gen.audio_quality_threshold == 0.7
        assert gen.max_duration == 1800
        assert gen.output_dir.exists()
        assert gen._job_poll_count == {}


# ---------------------------------------------------------------------------
# generate_audio — placeholder path (YMM4 handles voice)
# ---------------------------------------------------------------------------

class TestGenerateAudioPlaceholder:
    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_fallback_to_placeholder(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        sources = [_make_source()]
        result = await gen.generate_audio(sources)
        assert isinstance(result, AudioInfo)
        assert result.file_path.exists()
        assert result.duration == 1.0
        assert result.quality_score == 0.5

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_generate_audio_exception_propagates(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        # _generate_placeholder_audio を壊して例外を確認
        gen._generate_placeholder_audio = AsyncMock(side_effect=RuntimeError("boom"))
        with pytest.raises(RuntimeError, match="boom"):
            await gen.generate_audio([_make_source()])


# ---------------------------------------------------------------------------
# generate_audio — Gemini+TTS path (分岐の確認)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# _generate_placeholder_audio
# ---------------------------------------------------------------------------

class TestGeneratePlaceholderAudio:
    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_creates_wav_file(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        result = await gen._generate_placeholder_audio()
        assert result.file_path.exists()
        assert result.file_path.suffix == ".wav"
        assert result.duration == 1.0
        assert result.sample_rate == 44100
        assert result.channels == 2
        assert result.file_size > 0

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_wav_is_valid(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        result = await gen._generate_placeholder_audio()
        with wave.open(str(result.file_path), "rb") as wf:
            assert wf.getnchannels() == 2
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 44100


# ---------------------------------------------------------------------------
# _generate_script_with_gemini
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# _upload_sources (simulation)
# ---------------------------------------------------------------------------

class TestUploadSources:
    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_upload_completes(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        sources = [_make_source(title=f"S{i}") for i in range(3)]
        # 例外なく完了すること
        await gen._upload_sources("session-123", sources)

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_upload_empty_sources(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        await gen._upload_sources("session-456", [])


# ---------------------------------------------------------------------------
# _request_audio_generation (simulation)
# ---------------------------------------------------------------------------

class TestRequestAudioGeneration:
    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_returns_job_id(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        job_id = await gen._request_audio_generation("session-abc1")
        assert "audio_job_" in job_id
        assert "abc1" in job_id
        assert gen._job_poll_count[job_id] == 0


# ---------------------------------------------------------------------------
# _check_generation_status (simulation with poll count)
# ---------------------------------------------------------------------------

class TestCheckGenerationStatus:
    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_processing_then_completed(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        job_id = "test_job_1"
        gen._job_poll_count[job_id] = 0

        # 1-3回: processing
        for _ in range(3):
            status = await gen._check_generation_status(job_id)
            assert status == "processing"

        # 4回目: completed
        status = await gen._check_generation_status(job_id)
        assert status == "completed"

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_unknown_job_id(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        # 未登録ジョブでも poll_count=0 -> +1 = 1 -> processing
        status = await gen._check_generation_status("unknown_job")
        assert status == "processing"
        assert gen._job_poll_count["unknown_job"] == 1


# ---------------------------------------------------------------------------
# _get_audio_download_url (simulation)
# ---------------------------------------------------------------------------

class TestGetAudioDownloadUrl:
    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_returns_url(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        url = await gen._get_audio_download_url("job_42")
        assert url.startswith("https://")
        assert "job_42" in url


# ---------------------------------------------------------------------------
# _wait_for_audio_completion
# ---------------------------------------------------------------------------

class TestWaitForAudioCompletion:
    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_completes_after_polling(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        job_id = "poll_test"
        gen._job_poll_count[job_id] = 0  # シミュレーション用
        url = await gen._wait_for_audio_completion(job_id)
        assert url.startswith("https://")

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_raises_on_failure(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        gen._check_generation_status = AsyncMock(return_value="failed")
        with pytest.raises(Exception, match="失敗"):
            await gen._wait_for_audio_completion("fail_job")

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_timeout(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        gen._check_generation_status = AsyncMock(return_value="processing")
        # asyncio.sleep をモックして実際の待機を回避
        with patch("notebook_lm.audio_generator.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(TimeoutError, match="タイムアウト"):
                await gen._wait_for_audio_completion("unregistered_job_xyz")


# ---------------------------------------------------------------------------
# _download_audio
# ---------------------------------------------------------------------------

class TestDownloadAudio:
    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    @patch("notebook_lm.audio_generator.requests")
    async def test_successful_download(self, mock_requests, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()

        # WAV ファイルのバイト列を用意
        wav_path = tmp_path / "sample.wav"
        _write_wav(wav_path, duration_sec=0.1)
        wav_bytes = wav_path.read_bytes()

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_content = MagicMock(return_value=[wav_bytes])
        mock_requests.get.return_value = mock_resp

        result = await gen._download_audio("https://example.com/audio.wav")
        assert result.exists()
        assert result.stat().st_size > 0

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    @patch("notebook_lm.audio_generator.requests")
    async def test_download_failure_fallback(self, mock_requests, tmp_path):
        """ダウンロード失敗時、ローカル WAV フォールバックが生成される"""
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()

        import requests as real_requests
        mock_requests.get.side_effect = real_requests.exceptions.ConnectionError("fail")
        mock_requests.exceptions = real_requests.exceptions

        result = await gen._download_audio("https://example.com/audio.wav")
        assert result.exists()
        # フォールバック WAV の妥当性を確認
        with wave.open(str(result), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getframerate() == 44100

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    @patch("notebook_lm.audio_generator.requests")
    async def test_download_unexpected_exception_fallback(self, mock_requests, tmp_path):
        """予期しない例外でもフォールバック WAV が生成される"""
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()

        import requests as real_requests
        mock_requests.get.side_effect = ValueError("unexpected")
        mock_requests.exceptions = real_requests.exceptions

        result = await gen._download_audio("https://example.com/audio.wav")
        assert result.exists()


# ---------------------------------------------------------------------------
# _validate_audio_quality
# ---------------------------------------------------------------------------

class TestValidateAudioQuality:
    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_with_pydub_mock(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()

        audio_file = tmp_path / "test.wav"
        _write_wav(audio_file, duration_sec=2.0)

        mock_audio = MagicMock()
        mock_audio.__len__ = MagicMock(return_value=2000)  # 2000ms
        mock_audio.frame_rate = 44100
        mock_audio.channels = 2
        mock_audio.dBFS = -12.0

        # pydub が from pydub import AudioSegment でインポートされるので
        # 関数内のローカルインポートをモック
        mock_pydub = MagicMock()
        mock_pydub.AudioSegment.from_file.return_value = mock_audio

        with patch.dict("sys.modules", {"pydub": mock_pydub}):
            result = await gen._validate_audio_quality(audio_file)

        assert isinstance(result, AudioInfo)
        assert result.duration == 2.0
        assert result.sample_rate == 44100
        assert result.channels == 2

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_fallback_when_pydub_fails(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()

        audio_file = tmp_path / "test.wav"
        _write_wav(audio_file, duration_sec=1.0)

        mock_pydub = MagicMock()
        mock_pydub.AudioSegment.from_file.side_effect = Exception("pydub not available")

        with patch.dict("sys.modules", {"pydub": mock_pydub}):
            result = await gen._validate_audio_quality(audio_file)

        assert isinstance(result, AudioInfo)
        assert result.duration == 0.0
        assert result.quality_score == 0.5
        assert result.file_size > 0

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_fallback_when_file_missing(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()

        audio_file = tmp_path / "nonexistent.wav"

        mock_pydub = MagicMock()
        mock_pydub.AudioSegment.from_file.side_effect = FileNotFoundError("no file")

        with patch.dict("sys.modules", {"pydub": mock_pydub}):
            result = await gen._validate_audio_quality(audio_file)

        assert isinstance(result, AudioInfo)
        assert result.duration == 0.0
        assert result.quality_score == 0.5
        assert result.file_size == 0  # OSError でフォールバック

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_low_quality_warning(self, tmp_path):
        """品質スコアが threshold を下回るケース"""
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        gen.audio_quality_threshold = 0.99  # 高い閾値

        audio_file = tmp_path / "low_quality.wav"
        _write_wav(audio_file)

        mock_audio = MagicMock()
        mock_audio.__len__ = MagicMock(return_value=1000)
        mock_audio.frame_rate = 8000  # 低品質
        mock_audio.channels = 1
        mock_audio.dBFS = -30.0  # 適切範囲外

        mock_pydub = MagicMock()
        mock_pydub.AudioSegment.from_file.return_value = mock_audio

        with patch.dict("sys.modules", {"pydub": mock_pydub}):
            result = await gen._validate_audio_quality(audio_file)

        assert result.quality_score < 0.99

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_over_max_duration_warning(self, tmp_path):
        """max_duration 超過ケース"""
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        gen.max_duration = 10  # 10秒上限

        audio_file = tmp_path / "long.wav"
        _write_wav(audio_file)

        mock_audio = MagicMock()
        mock_audio.__len__ = MagicMock(return_value=20000)  # 20秒
        mock_audio.frame_rate = 44100
        mock_audio.channels = 2
        mock_audio.dBFS = -10.0

        mock_pydub = MagicMock()
        mock_pydub.AudioSegment.from_file.return_value = mock_audio

        with patch.dict("sys.modules", {"pydub": mock_pydub}):
            result = await gen._validate_audio_quality(audio_file)

        assert result.duration == 20.0


# ---------------------------------------------------------------------------
# _calculate_audio_quality
# ---------------------------------------------------------------------------

class TestCalculateAudioQuality:
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    def test_high_quality(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()

        audio = MagicMock()
        audio.frame_rate = 44100
        audio.channels = 2
        audio.dBFS = -10.0

        score = gen._calculate_audio_quality(audio)
        # base 0.5 + sample_rate 0.2 + channels 0.1 + dBFS 0.2 = 1.0
        assert score == 1.0

    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    def test_medium_sample_rate(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()

        audio = MagicMock()
        audio.frame_rate = 22050
        audio.channels = 1
        audio.dBFS = -10.0

        score = gen._calculate_audio_quality(audio)
        # base 0.5 + sample_rate 0.1 + channels 0 + dBFS 0.2 = 0.8
        assert score == 0.8

    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    def test_low_sample_rate(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()

        audio = MagicMock()
        audio.frame_rate = 8000
        audio.channels = 1
        audio.dBFS = -30.0  # 適切範囲外

        score = gen._calculate_audio_quality(audio)
        # base 0.5 + sample_rate 0 + channels 0 + dBFS 0 = 0.5
        assert score == 0.5

    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    def test_no_dbfs_attribute(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()

        audio = MagicMock(spec=[])  # dBFS 属性なし
        audio.frame_rate = 44100
        audio.channels = 2

        score = gen._calculate_audio_quality(audio)
        # base 0.5 + sample_rate 0.2 + channels 0.1 = 0.8
        assert abs(score - 0.8) < 1e-9

    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    def test_capped_at_1_0(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()

        audio = MagicMock()
        audio.frame_rate = 96000  # 高サンプルレート
        audio.channels = 6
        audio.dBFS = -10.0

        score = gen._calculate_audio_quality(audio)
        assert score <= 1.0


# ---------------------------------------------------------------------------
# regenerate_audio_if_needed
# ---------------------------------------------------------------------------

class TestRegenerateAudioIfNeeded:
    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_no_regeneration_when_quality_ok(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        gen.audio_quality_threshold = 0.5

        good_audio = AudioInfo(file_path=Path("/a.wav"), duration=10.0, quality_score=0.8)
        result = await gen.regenerate_audio_if_needed(good_audio, [_make_source()])
        assert result is good_audio

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_regeneration_when_quality_low(self, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        gen.audio_quality_threshold = 0.9

        bad_audio = AudioInfo(file_path=Path("/a.wav"), duration=10.0, quality_score=0.3)
        new_audio = AudioInfo(file_path=Path("/b.wav"), duration=10.0, quality_score=0.95)
        gen.generate_audio = AsyncMock(return_value=new_audio)

        result = await gen.regenerate_audio_if_needed(bad_audio, [_make_source()])
        assert result is new_audio
        gen.generate_audio.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    async def test_threshold_boundary(self, tmp_path):
        """quality_score == threshold のとき再生成しない"""
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()
        gen.audio_quality_threshold = 0.7

        edge_audio = AudioInfo(file_path=Path("/a.wav"), duration=10.0, quality_score=0.7)
        result = await gen.regenerate_audio_if_needed(edge_audio, [_make_source()])
        assert result is edge_audio


# ---------------------------------------------------------------------------
# Full workflow integration: _request → _wait → _download
# ---------------------------------------------------------------------------

class TestFullSimulationWorkflow:
    @pytest.mark.asyncio
    @patch("notebook_lm.audio_generator.settings", _mock_settings)
    @patch("notebook_lm.audio_generator.requests")
    async def test_request_wait_download(self, mock_requests, tmp_path):
        _mock_settings.AUDIO_DIR = tmp_path / "audio"
        _mock_settings.GEMINI_API_KEY = ""
        gen = AudioGenerator()

        # Step 1: ソースアップロード
        await gen._upload_sources("sess-1", [_make_source()])

        # Step 2: 音声生成リクエスト
        job_id = await gen._request_audio_generation("sess-1")
        assert job_id

        # Step 3: 完了待機 (simulated poll → 4回で完了)
        url = await gen._wait_for_audio_completion(job_id)
        assert "https://" in url

        # Step 4: ダウンロード (フォールバックでOK)
        import requests as real_requests
        mock_requests.get.side_effect = real_requests.exceptions.ConnectionError("mock")
        mock_requests.exceptions = real_requests.exceptions
        path = await gen._download_audio(url)
        assert path.exists()
