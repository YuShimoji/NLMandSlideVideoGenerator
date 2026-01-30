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

from notebook_lm.source_collector import SourceCollector, SourceInfo
from notebook_lm.audio_generator import AudioGenerator, AudioInfo
from notebook_lm.transcript_processor import TranscriptProcessor, TranscriptInfo
from config.settings import settings, create_directories

async def smoke_test():
    print("🚀 NotebookLM スモークテスト開始")
    create_directories()
    
    topic = "量子コンピュータの基礎"
    test_urls = ["https://ja.wikipedia.org/wiki/量子コンピュータ"]
    
    # 1. Source Collector Test
    print("\n--- [1] SourceCollector テスト ---")
    collector = SourceCollector()
    sources = await collector.collect_sources(topic, test_urls)
    print(f"✅ ソース収集完了: {len(sources)}件")
    for s in sources:
        print(f"  - {s.title} ({s.source_type})")

    # 2. Audio Generator Test (Mock Path)
    print("\n--- [2] AudioGenerator テスト (Placeholder Path) ---")
    generator = AudioGenerator()
    # Force use of placeholder by temporarily disabling Gemini/TTS if needed, 
    # but here we just want to see if the structure works.
    # Note: AudioGenerator.generate_audio uses self.gemini_integration if key exists.
    audio_info = await generator._generate_placeholder_audio()
    print(f"✅ 音声生成(Placeholder)完了: {audio_info.file_path}")
    print(f"  時間: {audio_info.duration}秒, スコア: {audio_info.quality_score}")

    # 3. Transcript Processor Test
    print("\n--- [3] TranscriptProcessor テスト ---")
    processor = TranscriptProcessor()
    transcript = await processor.process_audio(audio_info)
    print(f"✅ 文字起こし完了: {transcript.title}")
    print(f"  セグメント数: {len(transcript.segments)}")
    print(f"  精度スコア: {transcript.accuracy_score:.2f}")

    print("\n✨ スモークテスト完了")

if __name__ == "__main__":
    asyncio.run(smoke_test())
