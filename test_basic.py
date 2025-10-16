#!/usr/bin/env python3
"""
基本動作テスト
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))


def test_config_import():
    """設定ファイルのインポートテスト"""
    from config.settings import settings, create_directories

    create_directories()
    print(f"✓ 設定ファイル読み込み成功: {settings.APP_NAME} v{settings.VERSION}")
    assert settings.APP_NAME
    assert settings.VERSION


def test_directory_creation():
    """ディレクトリ作成テスト"""
    from config.settings import settings, create_directories

    create_directories()
    print("✓ ディレクトリ作成成功")

    required_dirs = [
        settings.DATA_DIR,
        settings.AUDIO_DIR,
        settings.SLIDES_DIR,
        settings.VIDEOS_DIR,
        settings.TRANSCRIPTS_DIR,
    ]
    for path in required_dirs:
        assert path.exists(), f"ディレクトリが存在しません: {path}"


def test_module_imports():
    """各モジュールのインポートテスト"""
    modules = [
        ("notebook_lm.source_collector", "SourceCollector"),
        ("notebook_lm.audio_generator", "AudioGenerator"),
        ("slides.slide_generator", "SlideGenerator"),
        ("video_editor.video_composer", "VideoComposer"),
        ("youtube.uploader", "YouTubeUploader"),
    ]

    for module_name, class_name in modules:
        module = __import__(module_name, fromlist=[class_name])
        getattr(module, class_name)
        print(f"✓ {module_name}.{class_name} インポート成功")


def main():
    """メインテスト実行"""
    print("=== NLMandSlideVideoGenerator 基本動作テスト ===")
    print()

    tests = [
        ("設定ファイル", test_config_import),
        ("ディレクトリ作成", test_directory_creation),
        ("モジュールインポート", test_module_imports),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"[テスト] {test_name}")
        try:
            test_func()
            passed += 1
        except Exception as exc:
            print(f"✗ {test_name} でエラー: {exc}")
        print()

    print(f"=== テスト結果: {passed}/{total} 成功 ===")

    if passed == total:
        print("✓ 全てのテストが成功しました")
        return 0

    print("✗ 一部のテストが失敗しました")
    return 1


if __name__ == "__main__":
    sys.exit(main())
