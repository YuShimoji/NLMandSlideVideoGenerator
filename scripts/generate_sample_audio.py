#!/usr/bin/env python3
"""
サンプル音声ファイル生成スクリプト

テスト用の無音WAVファイルを生成します。
実際の運用では、NotebookLM、SofTalk、AquesTalk等で生成した音声を使用してください。
"""
from __future__ import annotations

import wave
import struct
from pathlib import Path


def generate_silent_wav(output_path: Path, duration_seconds: float = 2.0, sample_rate: int = 44100):
    """無音のWAVファイルを生成"""
    num_samples = int(sample_rate * duration_seconds)
    
    with wave.open(str(output_path), 'w') as wav_file:
        wav_file.setnchannels(1)  # モノラル
        wav_file.setsampwidth(2)  # 16bit
        wav_file.setframerate(sample_rate)
        
        # 無音データ（全て0）
        for _ in range(num_samples):
            wav_file.writeframes(struct.pack('h', 0))
    
    print(f"生成: {output_path} ({duration_seconds}秒)")


def main():
    """サンプル音声セットを生成"""
    samples_dir = Path(__file__).parent.parent / "samples" / "basic_dialogue" / "audio"
    samples_dir.mkdir(parents=True, exist_ok=True)
    
    # 10行分の音声ファイルを生成（各2秒）
    durations = [2.0, 1.5, 3.0, 2.0, 3.5, 2.5, 3.0, 2.0, 2.5, 2.0]
    
    print("=" * 50)
    print("サンプル音声ファイル生成")
    print("=" * 50)
    print(f"出力先: {samples_dir}")
    print()
    
    for i, duration in enumerate(durations, start=1):
        output_path = samples_dir / f"{i:03d}.wav"
        generate_silent_wav(output_path, duration)
    
    print()
    print("=" * 50)
    print(f"完了: {len(durations)}ファイル生成")
    print("=" * 50)
    print()
    print("注意: これらは無音のテスト用ファイルです。")
    print("実際の運用では、以下のツールで音声を生成してください:")
    print("  - NotebookLM (Deep Dive Audio)")
    print("  - SofTalk / AquesTalk")
    print("  - ElevenLabs / OpenAI TTS")


if __name__ == "__main__":
    main()
