"""
VOICEVOX パイプラインのユニットテスト

VOICEVOX Engine への実接続は行わず、モックを使用してテストする。
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# プロジェクトルートを sys.path に追加
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))


class TestVoicevoxClient:
    """VoicevoxClient のユニットテスト"""

    def test_is_available_success(self):
        """Engine が起動している場合 True を返す"""
        from audio.voicevox_client import VoicevoxClient

        client = VoicevoxClient()
        with patch("audio.voicevox_client.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            assert client.is_available() is True

    def test_is_available_failure(self):
        """Engine が停止している場合 False を返す"""
        from audio.voicevox_client import VoicevoxClient
        import requests

        client = VoicevoxClient()
        with patch("audio.voicevox_client.requests.get") as mock_get:
            mock_get.side_effect = requests.ConnectionError("Connection refused")
            assert client.is_available() is False

    def test_is_available_timeout(self):
        """Engine がタイムアウトした場合 False を返す"""
        from audio.voicevox_client import VoicevoxClient
        import requests

        client = VoicevoxClient()
        with patch("audio.voicevox_client.requests.get") as mock_get:
            mock_get.side_effect = requests.Timeout("Timeout")
            assert client.is_available() is False

    def test_get_speakers_success(self):
        """スピーカー一覧を正常に取得"""
        from audio.voicevox_client import VoicevoxClient

        client = VoicevoxClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "ずんだもん",
                "styles": [
                    {"id": 3, "name": "ノーマル"},
                    {"id": 1, "name": "あまあま"},
                ],
            },
            {
                "name": "四国めたん",
                "styles": [
                    {"id": 2, "name": "ノーマル"},
                ],
            },
        ]

        with patch("audio.voicevox_client.requests.get") as mock_get:
            mock_get.return_value = mock_response
            speakers = client.get_speakers()

        assert len(speakers) == 3
        assert speakers[0].name == "ずんだもん"
        assert speakers[0].style_id == 3
        assert speakers[1].name == "ずんだもん"
        assert speakers[1].style_id == 1
        assert speakers[2].name == "四国めたん"

    def test_get_speakers_fallback(self):
        """API 失敗時はデフォルトスピーカーを返す"""
        from audio.voicevox_client import VoicevoxClient, DEFAULT_SPEAKERS
        import requests

        client = VoicevoxClient()
        with patch("audio.voicevox_client.requests.get") as mock_get:
            mock_get.side_effect = requests.ConnectionError("Connection refused")
            speakers = client.get_speakers()

        assert speakers == DEFAULT_SPEAKERS

    def test_audio_query(self):
        """audio_query API を正常に呼び出し"""
        from audio.voicevox_client import VoicevoxClient, VoicevoxAudioParams

        client = VoicevoxClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "speedScale": 1.0,
            "pitchScale": 0.0,
            "intonationScale": 1.0,
            "volumeScale": 1.0,
            "prePhonemeLength": 0.1,
            "postPhonemeLength": 0.1,
            "accent_phrases": [],
        }

        with patch("audio.voicevox_client.requests.post") as mock_post:
            mock_post.return_value = mock_response

            params = VoicevoxAudioParams(speed_scale=1.2, pitch_scale=0.1)
            query = client.audio_query("テスト", speaker_id=3, params=params)

        assert query["speedScale"] == 1.2
        assert query["pitchScale"] == 0.1
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["params"]["text"] == "テスト"
        assert call_kwargs[1]["params"]["speaker"] == 3

    def test_synthesis(self):
        """synthesis API を正常に呼び出し"""
        from audio.voicevox_client import VoicevoxClient

        client = VoicevoxClient()
        mock_response = MagicMock()
        mock_response.content = b"RIFF\x00\x00\x00\x00WAVEfmt "

        with patch("audio.voicevox_client.requests.post") as mock_post:
            mock_post.return_value = mock_response

            wav_data = client.synthesis({"accent_phrases": []}, speaker_id=3)

        assert wav_data.startswith(b"RIFF")

    def test_synthesize_to_file(self, tmp_path):
        """テキストから WAV ファイルを生成"""
        from audio.voicevox_client import VoicevoxClient

        client = VoicevoxClient()
        output_path = tmp_path / "test.wav"

        mock_query_response = MagicMock()
        mock_query_response.json.return_value = {"accent_phrases": []}

        mock_synth_response = MagicMock()
        mock_synth_response.content = b"RIFF\x00\x00\x00\x00WAVEfmt mock_data"

        with patch("audio.voicevox_client.requests.post") as mock_post:
            mock_post.side_effect = [mock_query_response, mock_synth_response]

            result = client.synthesize_to_file("テスト", output_path, speaker_id=3)

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_bytes().startswith(b"RIFF")

    def test_custom_engine_url(self):
        """カスタム Engine URL の設定"""
        from audio.voicevox_client import VoicevoxClient

        client = VoicevoxClient(engine_url="http://192.168.1.100:50021/")
        assert client.engine_url == "http://192.168.1.100:50021"


class TestVoicevoxAudioParams:
    """VoicevoxAudioParams のテスト"""

    def test_defaults(self):
        """デフォルトパラメータの確認"""
        from audio.voicevox_client import VoicevoxAudioParams

        params = VoicevoxAudioParams()
        assert params.speed_scale == 1.0
        assert params.pitch_scale == 0.0
        assert params.intonation_scale == 1.0
        assert params.volume_scale == 1.0

    def test_custom_params(self):
        """カスタムパラメータの確認"""
        from audio.voicevox_client import VoicevoxAudioParams

        params = VoicevoxAudioParams(speed_scale=1.5, pitch_scale=0.2)
        assert params.speed_scale == 1.5
        assert params.pitch_scale == 0.2


class TestVoicevoxVoicePipeline:
    """VoicevoxVoicePipeline のユニットテスト"""

    @pytest.mark.asyncio
    async def test_synthesize_success(self, tmp_path):
        """正常な音声合成"""
        from core.voice_pipelines.voicevox_pipeline import VoicevoxVoicePipeline

        pipeline = VoicevoxVoicePipeline(output_dir=tmp_path)

        with patch.object(pipeline.client, "is_available", return_value=True), \
             patch.object(pipeline.client, "synthesize_to_file_async") as mock_synth:

            wav_path = tmp_path / "voicevox_test_0000.wav"
            wav_path.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt mock")

            async def fake_synth(text, output_path, speaker_id, params):
                output_path.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt mock")
                return output_path

            mock_synth.side_effect = fake_synth

            script = {"content": "テストの音声です"}
            result = await pipeline.synthesize(script)

        assert result.provider == "voicevox"
        assert result.language == "ja"
        assert result.quality_score == 0.92

    @pytest.mark.asyncio
    async def test_synthesize_segments(self, tmp_path):
        """セグメント付き台本の音声合成"""
        from core.voice_pipelines.voicevox_pipeline import VoicevoxVoicePipeline

        pipeline = VoicevoxVoicePipeline(output_dir=tmp_path)

        with patch.object(pipeline.client, "is_available", return_value=True), \
             patch.object(pipeline.client, "synthesize_to_file_async") as mock_synth:

            async def fake_synth(text, output_path, speaker_id, params):
                output_path.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt mock")
                return output_path

            mock_synth.side_effect = fake_synth

            script = {
                "segments": [
                    {"content": "こんにちは"},
                    {"content": "今日の話題は"},
                    {"content": "AIについてです"},
                ],
                "language": "ja",
            }
            result = await pipeline.synthesize(script)

        assert mock_synth.call_count == 3
        assert result.provider == "voicevox"

    @pytest.mark.asyncio
    async def test_synthesize_engine_unavailable(self, tmp_path):
        """Engine 停止時にエラーを投げる"""
        from core.voice_pipelines.voicevox_pipeline import VoicevoxVoicePipeline
        from core.exceptions import AudioGenerationError

        pipeline = VoicevoxVoicePipeline(output_dir=tmp_path)

        with patch.object(pipeline.client, "is_available", return_value=False):
            with pytest.raises(AudioGenerationError, match="接続できません"):
                await pipeline.synthesize({"content": "テスト"})

    @pytest.mark.asyncio
    async def test_synthesize_empty_text(self, tmp_path):
        """空のテキストでエラーを投げる"""
        from core.voice_pipelines.voicevox_pipeline import VoicevoxVoicePipeline
        from core.exceptions import AudioGenerationError

        pipeline = VoicevoxVoicePipeline(output_dir=tmp_path)

        with pytest.raises(AudioGenerationError, match="テキストを抽出できません"):
            await pipeline.synthesize({"content": ""})

    def test_extract_text_from_content(self, tmp_path):
        """content フィールドからテキスト抽出"""
        from core.voice_pipelines.voicevox_pipeline import VoicevoxVoicePipeline

        pipeline = VoicevoxVoicePipeline(output_dir=tmp_path)
        text = pipeline._extract_text({"content": "Hello"})
        assert text == "Hello"

    def test_extract_text_from_segments(self, tmp_path):
        """segments フィールドからテキスト抽出"""
        from core.voice_pipelines.voicevox_pipeline import VoicevoxVoicePipeline

        pipeline = VoicevoxVoicePipeline(output_dir=tmp_path)
        text = pipeline._extract_text({
            "segments": [
                {"content": "Part 1"},
                {"content": "Part 2"},
            ]
        })
        assert "Part 1" in text
        assert "Part 2" in text


class TestTTSProviderEnum:
    """TTSProvider に VOICEVOX が追加されたことの確認"""

    def test_voicevox_provider_exists(self):
        """VOICEVOX プロバイダーが enum に存在"""
        from audio.tts_integration import TTSProvider

        assert TTSProvider.VOICEVOX.value == "voicevox"

    def test_voicevox_in_all_providers(self):
        """全プロバイダーリストに VOICEVOX が含まれる"""
        from audio.tts_integration import TTSProvider

        all_values = [p.value for p in TTSProvider]
        assert "voicevox" in all_values
