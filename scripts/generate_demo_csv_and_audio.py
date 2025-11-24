#!/usr/bin/env python3
"""CSVタイムラインモード用のデモ CSV / 無音WAV を生成するユーティリティ

- data/input/demo_timeline.csv
- data/audio/demo_timeline/001.wav, 002.wav

を生成し、CSVタイムライン + YMM4 エクスポートの動作確認に使える最小セットを用意します。
"""

from __future__ import annotations

import sys
from pathlib import Path
import wave


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def generate_demo_csv(csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    content = """Speaker,Text
Speaker1,こんにちは
Speaker2,世界
"""
    csv_path.write_text(content, encoding="utf-8")


def _create_silent_wav(path: Path, duration_sec: float = 1.0, sample_rate: int = 44100) -> None:
    """簡易な無音WAVを生成するヘルパー

    - モノラル16bit PCM
    - duration_sec 秒分の無音サンプルを書き出す
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    n_channels = 1
    sampwidth = 2  # bytes (16bit)
    framerate = sample_rate
    n_frames = int(duration_sec * framerate)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(framerate)
        # 無音なのですべて 0
        wf.writeframes(b"\x00\x00" * n_frames)


def generate_demo_audio(audio_dir: Path) -> None:
    _create_silent_wav(audio_dir / "001.wav", duration_sec=1.0)
    _create_silent_wav(audio_dir / "002.wav", duration_sec=1.0)


def main(argv: list[str] | None = None) -> int:
    csv_path = PROJECT_ROOT / "data" / "input" / "demo_timeline.csv"
    audio_dir = PROJECT_ROOT / "data" / "audio" / "demo_timeline"

    generate_demo_csv(csv_path)
    generate_demo_audio(audio_dir)

    print("[generate_demo_csv_and_audio] Generated files:")
    print(f"  CSV : {csv_path}")
    print(f"  WAV : {audio_dir / '001.wav'}")
    print(f"        {audio_dir / '002.wav'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
