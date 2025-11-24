#!/usr/bin/env python3
"""SofTalk / AquesTalk TTS バッチスクリプトの軽量テスト"""

import sys
from pathlib import Path
from unittest.mock import patch

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
