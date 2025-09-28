#!/usr/bin/env python3
"""
簡単なモックテスト - 基本動作確認
"""
import sys
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import asyncio
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def test_basic_imports():
    """基本的なインポートテスト"""
    print("=== 基本インポートテスト ===")
    
    try:
        from config.settings import settings, create_directories
        print("✓ 設定ファイル")
        
        from notebook_lm.source_collector import SourceCollector, SourceInfo
        print("✓ ソース収集")
        
        from notebook_lm.audio_generator import AudioGenerator, AudioInfo
        print("✓ 音声生成")
        
        from notebook_lm.transcript_processor import TranscriptProcessor, TranscriptInfo
        print("✓ 文字起こし")
        
        from slides.slide_generator import SlideGenerator, SlidesPackage
        print("✓ スライド生成")
        
        from video_editor.video_composer import VideoComposer, VideoInfo
        print("✓ 動画合成")
        
        from youtube.uploader import YouTubeUploader, UploadResult
        print("✓ YouTube アップロード")
        
        print("✓ 全てのモジュールのインポートが成功しました")
        return True
        
    except Exception as e:
        print(f"✗ インポートエラー: {e}")
        return False

def test_basic_instantiation():
    """基本的なクラスインスタンス化テスト"""
    print("\n=== クラスインスタンス化テスト ===")
    
    try:
        from config.settings import create_directories
        from notebook_lm.source_collector import SourceCollector
        from notebook_lm.audio_generator import AudioGenerator
        from notebook_lm.transcript_processor import TranscriptProcessor
        from slides.slide_generator import SlideGenerator
        from video_editor.video_composer import VideoComposer
        from youtube.uploader import YouTubeUploader
        
        # ディレクトリ作成
        create_directories()
        print("✓ ディレクトリ作成")
        
        # インスタンス化
        source_collector = SourceCollector()
        print("✓ SourceCollector")
        
        audio_generator = AudioGenerator()
        print("✓ AudioGenerator")
        
        transcript_processor = TranscriptProcessor()
        print("✓ TranscriptProcessor")
        
        slide_generator = SlideGenerator()
        print("✓ SlideGenerator")
        
        video_composer = VideoComposer()
        print("✓ VideoComposer")
        
        youtube_uploader = YouTubeUploader()
        print("✓ YouTubeUploader")
        
        print("✓ 全てのクラスのインスタンス化が成功しました")
        return True
        
    except Exception as e:
        print(f"✗ インスタンス化エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_classes():
    """データクラスのテスト"""
    print("\n=== データクラステスト ===")
    
    try:
        from pathlib import Path
        from notebook_lm.source_collector import SourceInfo
        from notebook_lm.audio_generator import AudioInfo
        from slides.slide_generator import SlideInfo, SlidesPackage
        from video_editor.video_composer import VideoInfo
        from youtube.uploader import UploadResult
        
        # SourceInfo
        source = SourceInfo(
            url="https://example.com",
            title="テストタイトル",
            content_preview="テスト内容",
            relevance_score=0.9,
            reliability_score=0.8,
            source_type="news"
        )
        print("✓ SourceInfo")
        
        # AudioInfo
        audio = AudioInfo(
            file_path=Path("test.mp3"),
            duration=180.0,
            quality_score=0.95,
            sample_rate=44100,
            file_size=1000000,
            language="ja"
        )
        print("✓ AudioInfo")
        
        # SlideInfo
        slide = SlideInfo(
            slide_id=1,
            title="テストスライド",
            content="テスト内容",
            layout="title_slide",
            duration=30.0
        )
        print("✓ SlideInfo")
        
        # SlidesPackage
        slides_package = SlidesPackage(
            file_path=Path("test.pptx"),
            slides=[slide],
            total_slides=1,
            theme="business"
        )
        print("✓ SlidesPackage")
        
        # VideoInfo
        video = VideoInfo(
            file_path=Path("test.mp4"),
            duration=180.0,
            resolution=(1920, 1080),
            fps=30,
            file_size=50000000,
            has_subtitles=True,
            has_effects=True,
            created_at=None
        )
        print("✓ VideoInfo")
        
        # UploadResult
        upload_result = UploadResult(
            video_id="test123",
            video_url="https://youtube.com/watch?v=test123",
            upload_status="success",
            processing_status="processing",
            privacy_status="private"
        )
        print("✓ UploadResult")
        
        print("✓ 全てのデータクラスが正常に動作しました")
        return True
        
    except Exception as e:
        print(f"✗ データクラスエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """メインテスト実行"""
    print("=== 簡単なモックテスト開始 ===\n")
    
    tests = [
        test_basic_imports,
        test_basic_instantiation,
        test_data_classes
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"✗ テストエラー: {e}")
    
    print(f"\n=== テスト結果: {passed}/{total} 成功 ===")
    
    if passed == total:
        print("✓ 全てのテストが成功しました")
        return 0
    else:
        print("✗ 一部のテストが失敗しました")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
