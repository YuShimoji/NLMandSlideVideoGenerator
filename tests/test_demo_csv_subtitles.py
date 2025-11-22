#!/usr/bin/env python3
"""demo_csv_subtitles スクリプトの簡易テスト

実ファイルを使って CSV + 行ごと音声 → 字幕生成が最低限動くことを確認する。
"""

import sys
import wave
import struct
from pathlib import Path

import pytest


project_root = Path(__file__).parent.parent
# ルートをパスに追加して scripts パッケージを import 可能にする
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scripts.demo_csv_subtitles import run_demo


def _create_silent_wav(path: Path, duration_sec: float = 1.0, sample_rate: int = 44100) -> None:
    """指定秒数の無音WAVを生成"""
    n_channels = 1
    sampwidth = 2  # 16-bit
    n_frames = int(sample_rate * duration_sec)

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        silence_frame = struct.pack("<h", 0)
        wf.writeframes(silence_frame * n_frames)


@pytest.mark.asyncio
async def test_demo_csv_subtitles_end_to_end(tmp_path: Path):
    # 1) CSV 作成 (2行)
    csv_path = tmp_path / "timeline.csv"
    csv_content = "Speaker1,こんにちは\nSpeaker2,世界\n"
    csv_path.write_text(csv_content, encoding="utf-8")

    # 2) 行ごとの音声ファイル (2本の無音WAV)
    audio_dir = tmp_path / "audio"
    _create_silent_wav(audio_dir / "001.wav", duration_sec=1.0)
    _create_silent_wav(audio_dir / "002.wav", duration_sec=2.0)

    # 3) 出力ディレクトリ
    out_dir = tmp_path / "subs"

    # 4) デモ実行
    srt_path = await run_demo(csv_path, audio_dir, output_dir=out_dir, style="default")

    assert srt_path.exists()
    content = srt_path.read_text(encoding="utf-8")

    # CSVのテキストがSRTに含まれていることを確認
    assert "こんにちは" in content
    assert "世界" in content

    # セグメントが2つ生成されているはず
    # SRT フォーマットではインデックス行が "1", "2" となるので、それを簡易チェック
    # 先頭行が "1" で始まり、その後のどこかに "2" 行があることを確認
    assert content.lstrip().startswith("1\n")
    assert "\n2\n" in content
