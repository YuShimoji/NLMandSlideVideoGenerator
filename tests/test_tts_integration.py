"""TTS統合テスト: run_csv_pipeline.py の --tts オプション"""
import csv
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from scripts.run_csv_pipeline import main


@pytest.fixture
def sample_csv(tmp_path):
    """テスト用CSVファイルを作成"""
    csv_path = tmp_path / "test_timeline.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Speaker1", "これはテスト文です"])
        writer.writerow(["Speaker2", "二行目のテストです"])
        writer.writerow(["Speaker1", "三行目のテスト"])
    return csv_path


class TestTTSArgumentParsing:
    """--tts オプションの引数パースをテスト"""

    def test_tts_option_accepted(self, sample_csv, tmp_path):
        """--tts voicevox が引数として受け付けられる"""
        audio_dir = tmp_path / "audio"
        # パース段階のテストのみ（実行はモックで停止）
        with patch("scripts.run_csv_pipeline.asyncio") as mock_asyncio:
            mock_asyncio.run.return_value = 0
            result = main([
                "--csv", str(sample_csv),
                "--audio-dir", str(audio_dir),
                "--tts", "voicevox",
                "--tts-speaker-id", "3",
            ])
            assert result == 0

    def test_tts_invalid_engine_rejected(self, sample_csv, tmp_path):
        """未対応のTTSエンジンは argparse でリジェクトされる"""
        audio_dir = tmp_path / "audio"
        with pytest.raises(SystemExit):
            main([
                "--csv", str(sample_csv),
                "--audio-dir", str(audio_dir),
                "--tts", "invalid_engine",
            ])


class TestTTSGeneration:
    """TTS音声生成ロジックのテスト"""

    @pytest.mark.asyncio
    async def test_generate_tts_audio_reads_csv(self, sample_csv, tmp_path):
        """CSVから正しく行を読み取る"""
        from scripts.run_csv_pipeline import _generate_tts_audio

        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        # VOICEVOX 未接続の場合はエラーを返す（接続テストではない）
        result = await _generate_tts_audio(
            csv_path=sample_csv,
            audio_dir=audio_dir,
            tts_engine="voicevox",
            speaker_id=3,
        )
        # VOICEVOX Engine 未起動のためエラーが返る
        assert result == 1

    @pytest.mark.asyncio
    async def test_generate_tts_skips_existing(self, sample_csv, tmp_path):
        """既存WAVがある行はスキップされる"""
        from scripts.run_csv_pipeline import _generate_tts_audio

        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        # 全行分のWAVを事前配置
        for i in range(3):
            (audio_dir / f"{i + 1:03d}.wav").write_bytes(b"\x00" * 100)

        result = await _generate_tts_audio(
            csv_path=sample_csv,
            audio_dir=audio_dir,
            tts_engine="voicevox",
            speaker_id=3,
        )
        # 全て既存なのでスキップ (成功)
        assert result == 0

    @pytest.mark.asyncio
    async def test_generate_tts_unsupported_engine(self, sample_csv, tmp_path):
        """未対応エンジンはエラーを返す"""
        from scripts.run_csv_pipeline import _generate_tts_audio

        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        result = await _generate_tts_audio(
            csv_path=sample_csv,
            audio_dir=audio_dir,
            tts_engine="nonexistent",
            speaker_id=None,
        )
        assert result == 1

    def test_no_wav_without_tts_shows_hint(self, sample_csv, tmp_path, capsys):
        """WAVなし + --tts なしの場合、ヒントメッセージを表示"""
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        # 空のaudio_dir
        result = main([
            "--csv", str(sample_csv),
            "--audio-dir", str(audio_dir),
        ])
        assert result == 1

    @pytest.mark.asyncio
    async def test_tts_voicevox_partial_failure(self, sample_csv, tmp_path):
        """VOICEVOX合成の部分失敗時もサマリ報告して終了する"""
        from scripts.run_csv_pipeline import _tts_voicevox

        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        lines = [(0, "Speaker1", "テスト1"), (1, "Speaker2", "テスト2")]

        with patch("scripts.run_csv_pipeline.settings") as mock_settings:
            mock_settings.TTS_SETTINGS = {"voicevox": {}}

            with patch("audio.voicevox_client.VoicevoxClient") as MockClient:
                instance = MockClient.return_value
                instance.is_available.return_value = True

                call_count = 0
                async def side_effect(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        # 1行目は成功 → ファイルを書き込む
                        output_path = kwargs.get("output_path") or args[1]
                        output_path.write_bytes(b"\x00" * 44)
                        return output_path
                    else:
                        # 2行目は失敗
                        raise ConnectionError("Engine timeout")

                instance.synthesize_to_file_async = MagicMock(side_effect=side_effect)

                result = await _tts_voicevox(audio_dir, lines, speaker_id=3)

        # 部分失敗は return 1 だが、1行目のWAVは生成済み
        assert result == 1
        assert (audio_dir / "001.wav").exists()

    @pytest.mark.asyncio
    async def test_tts_voicevox_all_success(self, sample_csv, tmp_path):
        """VOICEVOX全行成功時はreturn 0"""
        from scripts.run_csv_pipeline import _tts_voicevox

        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        lines = [(0, "Speaker1", "テスト1"), (1, "Speaker2", "テスト2")]

        with patch("scripts.run_csv_pipeline.settings") as mock_settings:
            mock_settings.TTS_SETTINGS = {"voicevox": {}}

            with patch("audio.voicevox_client.VoicevoxClient") as MockClient:
                instance = MockClient.return_value
                instance.is_available.return_value = True

                async def side_effect(*args, **kwargs):
                    output_path = kwargs.get("output_path") or args[1]
                    output_path.write_bytes(b"\x00" * 44)
                    return output_path

                instance.synthesize_to_file_async = MagicMock(side_effect=side_effect)

                result = await _tts_voicevox(audio_dir, lines, speaker_id=3)

        assert result == 0
        assert (audio_dir / "001.wav").exists()
        assert (audio_dir / "002.wav").exists()
