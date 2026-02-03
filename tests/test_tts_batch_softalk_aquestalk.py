#!/usr/bin/env python3
"""SofTalk / AquesTalk TTS バッチスクリプトの軽量テスト"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scripts import tts_batch_softalk_aquestalk as tts_batch  # noqa: E402


def _write_sample_csv(path: Path) -> None:
    content = """Speaker,Text
Speaker1,こんにちは
Speaker2,世界
"""
    path.write_text(content, encoding="utf-8")


def test_row_to_filename_mapping(tmp_path: Path):
    """CSV 行が 001.wav, 002.wav ... に対応することを確認"""

    csv_path = tmp_path / "timeline.csv"
    _write_sample_csv(csv_path)

    rows = tts_batch._load_timeline_rows(csv_path, text_encoding="utf-8")
    assert len(rows) == 2
    assert rows[0] == ("Speaker1", "こんにちは")
    assert rows[1] == ("Speaker2", "世界")

    out_dir = tmp_path / "audio"
    p1 = tts_batch._build_output_path(out_dir, 1)
    p2 = tts_batch._build_output_path(out_dir, 2)

    assert p1.name == "001.wav"
    assert p2.name == "002.wav"
    assert p1.parent == out_dir.resolve()
    assert p2.parent == out_dir.resolve()


def test_dry_run_does_not_invoke_subprocess(tmp_path: Path):
    """--dry-run 時には subprocess.run が呼ばれないことを確認"""

    csv_path = tmp_path / "timeline.csv"
    _write_sample_csv(csv_path)
    out_dir = tmp_path / "audio"

    # エンジン実行ファイルパスはダミーでよいので環境変数を設定
    fake_exe = tmp_path / "softalk.exe"
    fake_exe.write_text("dummy")

    with patch.dict("os.environ", {"SOFTALK_EXE": str(fake_exe)}, clear=False):
        with patch("scripts.tts_batch_softalk_aquestalk.subprocess.run") as mock_run:
            rc = tts_batch.run_batch(
                csv_path=csv_path,
                out_dir=out_dir,
                engine="softalk",
                voice_preset=None,
                text_encoding="utf-8",
                dry_run=True,
            )

    assert rc == 0
    mock_run.assert_not_called()
    # dry-run なので実ファイルは生成されない想定
    assert list(out_dir.glob("*.wav")) == []


def test_skip_existing_files(tmp_path: Path):
    """既存ファイルが存在する場合にスキップされることを確認"""

    csv_path = tmp_path / "timeline.csv"
    _write_sample_csv(csv_path)
    out_dir = tmp_path / "audio"
    out_dir.mkdir()

    # 既存ファイルを作成
    existing_wav = out_dir / "001.wav"
    existing_wav.write_bytes(b"RIFF")

    fake_exe = tmp_path / "softalk.exe"
    fake_exe.write_text("dummy")

    with patch.dict("os.environ", {"SOFTALK_EXE": str(fake_exe)}, clear=False):
        with patch("scripts.tts_batch_softalk_aquestalk.subprocess.run") as mock_run:
            rc = tts_batch.run_batch(
                csv_path=csv_path,
                out_dir=out_dir,
                engine="softalk",
                voice_preset=None,
                text_encoding="utf-8",
                dry_run=False,
                skip_existing=True,
            )

    assert rc == 0
    # 001.wav はスキップされるため、subprocess.run は1回のみ呼ばれる (002.wavのみ)
    assert mock_run.call_count == 1


def test_no_skip_option(tmp_path: Path):
    """--no-skip オプションで既存ファイルも再生成されることを確認"""

    csv_path = tmp_path / "timeline.csv"
    _write_sample_csv(csv_path)
    out_dir = tmp_path / "audio"
    out_dir.mkdir()

    # 既存ファイルを作成
    existing_wav = out_dir / "001.wav"
    existing_wav.write_bytes(b"RIFF")

    fake_exe = tmp_path / "softalk.exe"
    fake_exe.write_text("dummy")

    with patch.dict("os.environ", {"SOFTALK_EXE": str(fake_exe)}, clear=False):
        with patch("scripts.tts_batch_softalk_aquestalk.subprocess.run") as mock_run:
            rc = tts_batch.run_batch(
                csv_path=csv_path,
                out_dir=out_dir,
                engine="softalk",
                voice_preset=None,
                text_encoding="utf-8",
                dry_run=False,
                skip_existing=False,  # スキップしない
            )

    assert rc == 0
    # 両方のファイルで subprocess.run が呼ばれる
    assert mock_run.call_count == 2


def test_retry_on_failure(tmp_path: Path):
    """TTS実行失敗時にリトライされることを確認"""

    # 単一行のCSVを使用
    csv_path = tmp_path / "timeline.csv"
    csv_path.write_text("Speaker,Text\nSpeaker1,こんにちは\n", encoding="utf-8")
    out_dir = tmp_path / "audio"

    fake_exe = tmp_path / "softalk.exe"
    fake_exe.write_text("dummy")

    with patch.dict("os.environ", {"SOFTALK_EXE": str(fake_exe)}, clear=False):
        with patch("scripts.tts_batch_softalk_aquestalk.subprocess.run") as mock_run:
            # 2回失敗、3回目で成功
            mock_run.side_effect = [
                subprocess.CalledProcessError(1, "softalk"),
                subprocess.CalledProcessError(1, "softalk"),
                MagicMock(),  # 成功
            ]

            rc = tts_batch.run_batch(
                csv_path=csv_path,
                out_dir=out_dir,
                engine="softalk",
                voice_preset=None,
                text_encoding="utf-8",
                dry_run=False,
                max_retries=3,
            )

    assert rc == 0
    # 3回呼ばれる（2回失敗+1回成功）
    assert mock_run.call_count == 3


def test_retry_exhausted_returns_error(tmp_path: Path):
    """リトライ回数を超えて失敗した場合エラーを返すことを確認"""

    # 単一行のCSVを使用
    csv_path = tmp_path / "timeline.csv"
    csv_path.write_text("Speaker,Text\nSpeaker1,こんにちは\n", encoding="utf-8")
    out_dir = tmp_path / "audio"

    fake_exe = tmp_path / "softalk.exe"
    fake_exe.write_text("dummy")

    with patch.dict("os.environ", {"SOFTALK_EXE": str(fake_exe)}, clear=False):
        with patch("scripts.tts_batch_softalk_aquestalk.subprocess.run") as mock_run:
            # 常に失敗
            mock_run.side_effect = subprocess.CalledProcessError(1, "softalk")

            rc = tts_batch.run_batch(
                csv_path=csv_path,
                out_dir=out_dir,
                engine="softalk",
                voice_preset=None,
                text_encoding="utf-8",
                dry_run=False,
                max_retries=2,
            )

    assert rc == 1  # エラー
    # max_retries=2 なので、2回試行する
    assert mock_run.call_count == 2


def test_default_path_detection_env_var_priority(tmp_path: Path):
    """環境変数が優先されることを確認"""

    fake_exe = tmp_path / "custom_softalk.exe"
    fake_exe.write_text("dummy")

    with patch.dict("os.environ", {"SOFTALK_EXE": str(fake_exe)}, clear=False):
        exe_path = tts_batch._get_engine_executable("softalk")
        assert exe_path == fake_exe


def test_empty_csv_returns_success(tmp_path: Path):
    """空のCSVの場合も正常終了することを確認"""

    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("Speaker,Text\n", encoding="utf-8")
    out_dir = tmp_path / "audio"

    fake_exe = tmp_path / "softalk.exe"
    fake_exe.write_text("dummy")

    with patch.dict("os.environ", {"SOFTALK_EXE": str(fake_exe)}, clear=False):
        rc = tts_batch.run_batch(
            csv_path=csv_path,
            out_dir=out_dir,
            engine="softalk",
        )

    assert rc == 0


def test_speaker_voice_map(tmp_path: Path):
    """話者マッピングが正しく適用されることを確認"""

    speaker_map = tmp_path / "speaker_map.json"
    speaker_map.write_text(
        '{"Speaker1": "voice_a", "Speaker2": {"softalk": "voice_b"}, "*": "default_voice"}'
    )

    map_data = tts_batch._load_speaker_voice_map(speaker_map)
    assert map_data["Speaker1"] == "voice_a"
    assert map_data["Speaker2"]["softalk"] == "voice_b"

    # Speaker1 -> voice_a
    preset1 = tts_batch._select_voice_preset(
        engine="softalk",
        speaker="Speaker1",
        default_preset=None,
        speaker_voice_map=map_data,
    )
    assert preset1 == "voice_a"

    # Speaker2 (softalk) -> voice_b
    preset2 = tts_batch._select_voice_preset(
        engine="softalk",
        speaker="Speaker2",
        default_preset=None,
        speaker_voice_map=map_data,
    )
    assert preset2 == "voice_b"

    # Unknown speaker -> default_voice (wild card)
    preset3 = tts_batch._select_voice_preset(
        engine="softalk",
        speaker="Unknown",
        default_preset=None,
        speaker_voice_map=map_data,
    )
    assert preset3 == "default_voice"
