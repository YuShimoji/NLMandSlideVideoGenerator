#!/usr/bin/env python3
"""split_audio_by_silence スクリプトの簡易テスト

- 合成したWAV (音声 → 無音 → 音声) を無音検出で2セグメントに分割できることを確認
"""

from __future__ import annotations

import sys
import wave
import struct
from pathlib import Path

import pytest


project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scripts.split_audio_by_silence import split_audio_by_silence  # noqa: E402


def _create_pattern_wav(
    path: Path,
    pattern: list[tuple[float, int]],
    *,
    sample_rate: int = 8000,
) -> None:
    """(duration_sec, amplitude) のパターンから単純なWAVを生成

    amplitude=0 なら無音、それ以外は一定振幅の矩形波として扱う。
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)

        for duration_sec, amp in pattern:
            n_frames = int(sample_rate * duration_sec)
            value = max(min(amp, 32767), -32768)
            frame = struct.pack("<h", value)
            wf.writeframes(frame * n_frames)


@pytest.mark.parametrize(
    "pattern, expected_segments",
    [
        # 音声(1.0s) → 無音(0.5s) → 音声(1.0s) を2セグメントに分割
        ([(1.0, 12000), (0.5, 0), (1.0, 12000)], 2),
        # 無音が短すぎる場合は1セグメントのまま
        ([(1.0, 12000), (0.1, 0), (1.0, 12000)], 1),
    ],
)
def test_split_audio_by_silence_basic(tmp_path: Path, pattern, expected_segments: int) -> None:
    input_path = tmp_path / "input.wav"
    out_dir = tmp_path / "out"

    _create_pattern_wav(input_path, pattern)

    segments = split_audio_by_silence(
        input_path=input_path,
        out_dir=out_dir,
        min_silence_sec=0.3,
        silence_threshold=0.05,
        min_segment_sec=0.2,
        start_index=1,
        window_ms=10,
        dry_run=False,
    )

    assert len(segments) == expected_segments
    for idx, seg_path in enumerate(segments, start=1):
        assert seg_path.exists()
        # 最低限、フレーム数が0でないことを確認
        with wave.open(str(seg_path), "rb") as wf:
            assert wf.getnframes() > 0
