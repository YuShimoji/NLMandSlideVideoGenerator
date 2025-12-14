#!/usr/bin/env python3
"""run_csv_pipeline CLI の簡易テスト

- 一時ディレクトリに CSV + 無音WAV を作成
- main([...]) を直接呼び出し、終了コード0と動画生成ログを確認
"""

import sys
from pathlib import Path
from io import StringIO

import pytest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from tests.test_demo_csv_to_video import _create_silent_wav  # noqa: E402
from scripts.run_csv_pipeline import main  # noqa: E402


def _build_basic_csv_and_audio(tmp_path: Path) -> tuple[Path, Path]:
    csv_path = tmp_path / "timeline.csv"
    csv_content = "Speaker1,こんにちは\nSpeaker2,世界\n"
    csv_path.write_text(csv_content, encoding="utf-8")

    audio_dir = tmp_path / "audio"
    _create_silent_wav(audio_dir / "001.wav", duration_sec=1.0)
    _create_silent_wav(audio_dir / "002.wav", duration_sec=2.0)
    return csv_path, audio_dir


@pytest.mark.integration
@pytest.mark.slow
def test_run_csv_pipeline_cli_basic(tmp_path: Path, monkeypatch):
    # 1) CSV / 音声を準備
    csv_path, audio_dir = _build_basic_csv_and_audio(tmp_path)

    # 3) 出力をキャプチャ
    buf = StringIO()
    monkeypatch.setattr("sys.stdout", buf)

    exit_code = main([
        "--csv",
        str(csv_path),
        "--audio-dir",
        str(audio_dir),
        "--video-quality",
        "720p",
    ])

    output = buf.getvalue()

    assert exit_code == 0
    assert "Generated video:" in output


@pytest.mark.integration
@pytest.mark.slow
def test_run_csv_pipeline_cli_max_chars_override(tmp_path: Path, monkeypatch):
    # 1) CSV / 音声を準備
    csv_path, audio_dir = _build_basic_csv_and_audio(tmp_path)

    # 2) 出力をキャプチャ
    buf = StringIO()
    monkeypatch.setattr("sys.stdout", buf)

    exit_code = main([
        "--csv",
        str(csv_path),
        "--audio-dir",
        str(audio_dir),
        "--video-quality",
        "720p",
        "--max-chars-per-slide",
        "50",
    ])

    output = buf.getvalue()

    assert exit_code == 0
    assert "Generated video:" in output
