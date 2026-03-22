#!/usr/bin/env python3
"""
NotebookLM components smoke test
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from notebook_lm.audio_generator import AudioGenerator
from notebook_lm.transcript_processor import TranscriptProcessor
from config.settings import create_directories

async def smoke_test():
    print("NotebookLM smoke test")
    create_directories()

    # 1. Audio Generator Test (Mock Path)
    print("\n--- [1] AudioGenerator test (Placeholder Path) ---")
    generator = AudioGenerator()
    audio_info = await generator._generate_placeholder_audio()
    print(f"OK audio (Placeholder): {audio_info.file_path}")
    print(f"  duration: {audio_info.duration}s, score: {audio_info.quality_score}")

    # 2. Transcript Processor Test
    print("\n--- [2] TranscriptProcessor test ---")
    processor = TranscriptProcessor()
    transcript = await processor.process_audio(audio_info)
    print(f"OK transcript: {transcript.title}")
    print(f"  segments: {len(transcript.segments)}")
    print(f"  accuracy: {transcript.accuracy_score:.2f}")

    print("\nSmoke test complete")

if __name__ == "__main__":
    asyncio.run(smoke_test())
