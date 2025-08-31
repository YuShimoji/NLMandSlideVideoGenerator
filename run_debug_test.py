#!/usr/bin/env python3
"""
デバッグテスト実行とシステム状態確認
"""
import sys
import subprocess
from pathlib import Path

def run_debug_test():
    """デバッグテストを実行"""
    print("🔍 システム状態確認を開始します")
    print("=" * 50)
    
    project_root = Path(__file__).parent
    debug_script = project_root / "debug_test.py"
    
    if not debug_script.exists():
        print(f"❌ デバッグスクリプトが見つかりません: {debug_script}")
        return False
    
    try:
        # Pythonスクリプトを実行
        result = subprocess.run(
            [sys.executable, str(debug_script)],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        
        print("📋 実行結果:")
        print("-" * 30)
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ エラー出力:")
            print(result.stderr)
        
        print(f"📊 終了コード: {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ テスト実行中にエラーが発生: {e}")
        return False

def check_project_structure():
    """プロジェクト構造を確認"""
    print("\n📁 プロジェクト構造確認")
    print("-" * 30)
    
    project_root = Path(__file__).parent
    
    # 重要なディレクトリとファイルをチェック
    important_paths = [
        "src/",
        "src/config/",
        "src/config/settings.py",
        "src/notebook_lm/",
        "src/slides/",
        "src/video_editor/",
        "src/youtube/",
        "tests/",
        "requirements.txt",
        "README.md"
    ]
    
    for path_str in important_paths:
        path = project_root / path_str
        if path.exists():
            if path.is_dir():
                file_count = len(list(path.glob("*")))
                print(f"✅ {path_str} ({file_count}項目)")
            else:
                size = path.stat().st_size
                print(f"✅ {path_str} ({size}bytes)")
        else:
            print(f"❌ {path_str} (見つかりません)")

def run_simple_import_test():
    """簡単なインポートテストを実行"""
    print("\n🔧 インポートテスト")
    print("-" * 30)
    
    # プロジェクトルートをパスに追加
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root / "src"))
    
    # 各モジュールのインポートをテスト
    modules_to_test = [
        ("config.settings", "settings"),
        ("notebook_lm.source_collector", "SourceCollector"),
        ("notebook_lm.audio_generator", "AudioGenerator"),
        ("slides.slide_generator", "SlideGenerator"),
        ("video_editor.video_composer", "VideoComposer"),
        ("youtube.uploader", "YouTubeUploader")
    ]
    
    success_count = 0
    
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}")
            success_count += 1
        except Exception as e:
            print(f"❌ {module_name}.{class_name}: {e}")
    
    print(f"\n📊 インポート成功率: {success_count}/{len(modules_to_test)} ({success_count/len(modules_to_test)*100:.1f}%)")
    
    return success_count == len(modules_to_test)

def main():
    """メイン実行"""
    print("🚀 NLMandSlideVideoGenerator システム診断")
    print("=" * 60)
    
    # 1. プロジェクト構造確認
    check_project_structure()
    
    # 2. デバッグテスト実行
    debug_success = run_debug_test()
    
    # 3. インポートテスト実行
    import_success = run_simple_import_test()
    
    # 4. 総合結果
    print("\n" + "=" * 60)
    print("📋 診断結果サマリー")
    print("=" * 60)
    
    print(f"🔍 デバッグテスト: {'✅ 成功' if debug_success else '❌ 失敗'}")
    print(f"🔧 インポートテスト: {'✅ 成功' if import_success else '❌ 失敗'}")
    
    if debug_success and import_success:
        print("\n🎉 システムは正常に動作しています！")
        print("💡 次のステップ:")
        print("  1. モックテストの実行")
        print("  2. デモンストレーションの実行")
        print("  3. API連携の準備")
    else:
        print("\n⚠️ 問題が検出されました。")
        print("💡 対処方法:")
        print("  1. 依存関係の再インストール")
        print("  2. パス設定の確認")
        print("  3. モジュール構造の確認")

if __name__ == "__main__":
    main()
