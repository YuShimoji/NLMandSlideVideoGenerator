#!/usr/bin/env python3
"""demo_csv_to_video スクリプトの簡易テスト

Path B (MoviePy) が削除されたため、run_demo は NotImplementedError を投げる。
このテストはそのことを検証する。
"""

import sys
import wave
import struct
from pathlib import Path
from unittest.mock import patch, AsyncMock, Mock

import pytest


project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scripts.demo_csv_to_video import run_demo  # noqa: E402


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
async def test_demo_csv_to_video_end_to_end(tmp_path: Path):
    """Path B removed: run_demo raises NotImplementedError"""
    csv_path = tmp_path / "timeline.csv"
    csv_content = "Speaker1,こんにちは\nSpeaker2,世界\n"
    csv_path.write_text(csv_content, encoding="utf-8")

    audio_dir = tmp_path / "audio"
    _create_silent_wav(audio_dir / "001.wav", duration_sec=1.0)
    _create_silent_wav(audio_dir / "002.wav", duration_sec=2.0)

    with patch("scripts.demo_csv_to_video.SlideGenerator") as MockSlideGen, \
         patch("scripts.demo_csv_to_video.create_directories") as mock_create_dirs:

        mock_create_dirs.return_value = None
        slide_gen_instance = MockSlideGen.return_value
        slide_gen_instance.generate_slides = AsyncMock(return_value=Mock())

        with pytest.raises(NotImplementedError, match="Path B"):
            await run_demo(csv_path, audio_dir, video_quality="720p", max_slides=10)
