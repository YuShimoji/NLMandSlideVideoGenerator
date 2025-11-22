#!/usr/bin/env python3
"""demo_csv_to_video スクリプトの簡易テスト

CSV + 行ごと WAV から動画生成デモのフローが最低限動くことを確認する。
SlideGenerator / VideoComposer はモックして、重い依存(MoviePy 等)には触れないようにする。
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
    # 1) CSV 作成 (2行)
    csv_path = tmp_path / "timeline.csv"
    csv_content = "Speaker1,こんにちは\nSpeaker2,世界\n"
    csv_path.write_text(csv_content, encoding="utf-8")

    # 2) 行ごとの音声ファイル (2本の無音WAV)
    audio_dir = tmp_path / "audio"
    _create_silent_wav(audio_dir / "001.wav", duration_sec=1.0)
    _create_silent_wav(audio_dir / "002.wav", duration_sec=2.0)

    # 3) SlideGenerator / VideoComposer をモック
    dummy_video_path = tmp_path / "out.mp4"
    dummy_video_path.write_bytes(b"")

    with patch("scripts.demo_csv_to_video.SlideGenerator") as MockSlideGen, \
         patch("scripts.demo_csv_to_video.VideoComposer") as MockVideoComp, \
         patch("scripts.demo_csv_to_video.create_directories") as mock_create_dirs:

        mock_create_dirs.return_value = None

        slide_gen_instance = MockSlideGen.return_value
        slide_gen_instance.generate_slides = AsyncMock(return_value=Mock())

        video_comp_instance = MockVideoComp.return_value
        dummy_video_info = Mock()
        dummy_video_info.file_path = dummy_video_path
        video_comp_instance.compose_video = AsyncMock(return_value=dummy_video_info)

        # 4) デモ実行
        video_path = await run_demo(csv_path, audio_dir, video_quality="720p", max_slides=10)

        assert video_path == dummy_video_path
        assert video_path.exists()

        # SlideGenerator / VideoComposer が呼ばれていること
        slide_gen_instance.generate_slides.assert_awaited()
        video_comp_instance.compose_video.assert_awaited()
