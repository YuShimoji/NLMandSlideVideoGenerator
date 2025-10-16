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
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def _check_basic_imports() -> bool:
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

    except Exception as exc:
        print(f"✗ インポートエラー: {exc}")
        return False


def _check_basic_instantiation() -> bool:
    print("\n=== クラスインスタンス化テスト ===")

    try:
        from config.settings import create_directories
        from notebook_lm.source_collector import SourceCollector
        from notebook_lm.audio_generator import AudioGenerator
        from notebook_lm.transcript_processor import TranscriptProcessor
        from slides.slide_generator import SlideGenerator
        from video_editor.video_composer import VideoComposer
        from youtube.uploader import YouTubeUploader

        create_directories()
        print("✓ ディレクトリ作成")

        SourceCollector()
        print("✓ SourceCollector")

        AudioGenerator()
        print("✓ AudioGenerator")

        TranscriptProcessor()
        print("✓ TranscriptProcessor")

        SlideGenerator()
        print("✓ SlideGenerator")

        VideoComposer()
        print("✓ VideoComposer")

        YouTubeUploader()
        print("✓ YouTubeUploader")

        print("✓ 全てのクラスのインスタンス化が成功しました")
        return True

    except Exception as exc:
        print(f"✗ インスタンス化エラー: {exc}")
        import traceback
        traceback.print_exc()
        return False


def _check_data_classes() -> bool:
    print("\n=== データクラステスト ===")

    try:
        from notebook_lm.source_collector import SourceInfo
        from notebook_lm.audio_generator import AudioInfo
        from slides.slide_generator import SlideInfo, SlidesPackage
        from video_editor.video_composer import VideoInfo
        from youtube.uploader import UploadResult

        SourceInfo(
            url="https://example.com",
            title="テストタイトル",
            content_preview="テスト内容",
            relevance_score=0.9,
            reliability_score=0.8,
            source_type="news",
        )
        print("✓ SourceInfo")

        AudioInfo(
            file_path=Path("test.mp3"),
            duration=180.0,
            quality_score=0.95,
            sample_rate=44100,
            file_size=1_000_000,
            language="ja",
        )
        print("✓ AudioInfo")

        slide = SlideInfo(
            slide_id=1,
            title="テストスライド",
            content="テスト内容",
            layout="title_slide",
            duration=30.0,
        )
        print("✓ SlideInfo")

        SlidesPackage(
            file_path=Path("test.pptx"),
            slides=[slide],
            total_slides=1,
            theme="business",
        )
        print("✓ SlidesPackage")

        VideoInfo(
            file_path=Path("test.mp4"),
            duration=180.0,
            resolution=(1920, 1080),
            fps=30,
            file_size=50_000_000,
            has_subtitles=True,
            has_effects=True,
            created_at=None,
        )
        print("✓ VideoInfo")

        UploadResult(
            video_id="test123",
            video_url="https://youtube.com/watch?v=test123",
            upload_status="success",
            processing_status="processing",
            privacy_status="private",
        )
        print("✓ UploadResult")

        print("✓ 全てのデータクラスが正常に動作しました")
        return True

    except Exception as exc:
        print(f"✗ データクラスエラー: {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_imports():
    assert _check_basic_imports()


def test_basic_instantiation():
    assert _check_basic_instantiation()


def test_data_classes():
    assert _check_data_classes()


def main() -> int:
    print("=== 簡単なモックテスト開始 ===\n")

    tests = [
        ("基本インポート", _check_basic_imports),
        ("クラスインスタンス化", _check_basic_instantiation),
        ("データクラス", _check_data_classes),
    ]

    passed = 0
    total = len(tests)

    for name, func in tests:
        print(f"[テスト] {name}")
        if func():
            passed += 1
        print()

    print(f"=== テスト結果: {passed}/{total} 成功 ===")

    if passed == total:
        print("✓ 全てのテストが成功しました")
        return 0

    print("✗ 一部のテストが失敗しました")
    return 1


if __name__ == "__main__":
    sys.exit(main())
