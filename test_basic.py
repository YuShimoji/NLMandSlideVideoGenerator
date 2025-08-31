#!/usr/bin/env python3
"""
基本動作テスト
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def test_config_import():
    """設定ファイルのインポートテスト"""
    try:
        from config.settings import settings, create_directories
        print(f"✓ 設定ファイル読み込み成功: {settings.APP_NAME} v{settings.VERSION}")
        return True
    except Exception as e:
        print(f"✗ 設定ファイル読み込み失敗: {e}")
        return False

def test_directory_creation():
    """ディレクトリ作成テスト"""
    try:
        from config.settings import create_directories
        create_directories()
        print("✓ ディレクトリ作成成功")
        return True
    except Exception as e:
        print(f"✗ ディレクトリ作成失敗: {e}")
        return False

def test_module_imports():
    """各モジュールのインポートテスト"""
    modules = [
        ("notebook_lm.source_collector", "SourceCollector"),
        ("notebook_lm.audio_generator", "AudioGenerator"),
        ("slides.slide_generator", "SlideGenerator"),
        ("video_editor.video_composer", "VideoComposer"),
        ("youtube.uploader", "YouTubeUploader")
    ]
    
    success_count = 0
    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✓ {module_name}.{class_name} インポート成功")
            success_count += 1
        except Exception as e:
            print(f"✗ {module_name}.{class_name} インポート失敗: {e}")
    
    return success_count == len(modules)

def main():
    """メインテスト実行"""
    print("=== NLMandSlideVideoGenerator 基本動作テスト ===")
    print()
    
    tests = [
        ("設定ファイル", test_config_import),
        ("ディレクトリ作成", test_directory_creation),
        ("モジュールインポート", test_module_imports)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"[テスト] {test_name}")
        if test_func():
            passed += 1
        print()
    
    print(f"=== テスト結果: {passed}/{total} 成功 ===")
    
    if passed == total:
        print("✓ 全てのテストが成功しました")
        return 0
    else:
        print("✗ 一部のテストが失敗しました")
        return 1

if __name__ == "__main__":
    sys.exit(main())
