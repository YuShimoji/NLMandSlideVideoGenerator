#!/usr/bin/env python3
"""inspect_csv_timeline スクリプトの簡易テスト

CSV + 行ごと WAV から Transcript/スライド分割の可視化ロジックが最低限動くことを確認する。
"""

import sys
import wave
import struct
from pathlib import Path

import pytest


project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scripts.inspect_csv_timeline import inspect_timeline  # noqa: E402


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
async def test_inspect_csv_timeline_basic(tmp_path: Path):
    # 1) CSV 作成 (2行)
    csv_path = tmp_path / "timeline.csv"
    csv_content = "Speaker1,こんにちは世界\nSpeaker2,テストです\n"
    csv_path.write_text(csv_content, encoding="utf-8")

    # 2) 行ごとの音声ファイル (2本の無音WAV)
    audio_dir = tmp_path / "audio"
    _create_silent_wav(audio_dir / "001.wav", duration_sec=1.0)
    _create_silent_wav(audio_dir / "002.wav", duration_sec=2.0)

    # 3) 可視化処理を実行（小さい max_chars_per_slide を指定して、分割挙動に影響を与える）
    summary = await inspect_timeline(
        csv_path=csv_path,
        audio_dir=audio_dir,
        max_chars_per_slide=20,
        max_slides=10,
    )

    transcript = summary["transcript"]
    slides = summary["slide_contents"]
    stats = summary["stats"]

    # セグメント数と総時間が期待どおりであること
    assert len(transcript.segments) == 2
    assert transcript.total_duration == pytest.approx(3.0, rel=0.1)

    # スライド分割結果が少なくとも1枚以上あり、統計情報と整合していること
    assert slides
    assert stats["num_slides"] == len(slides)

    # max_chars_per_slide が stats に反映されていること
    assert stats["max_chars_per_slide"] == 20
