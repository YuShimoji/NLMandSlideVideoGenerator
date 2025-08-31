#!/usr/bin/env python3
"""
API統合テスト実行スクリプト
"""
import sys
import asyncio
import subprocess
from pathlib import Path

def run_api_integration_test():
    """API統合テストを実行"""
    print("🧪 API統合テスト実行開始")
    print("=" * 50)
    
    project_root = Path(__file__).parent
    test_script = project_root / "test_api_integration.py"
    
    if not test_script.exists():
        print(f"❌ テストスクリプトが見つかりません: {test_script}")
        return False
    
    try:
        # 必要なディレクトリを作成
        data_dirs = [
            "data/input",
            "data/output", 
            "data/temp",
            "data/audio",
            "data/slides",
            "data/videos"
        ]
        
        for dir_path in data_dirs:
            full_path = project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
        
        print("✅ 必要なディレクトリを準備しました")
        
        # API統合テストを実行
        print("🔄 API統合テストを実行中...")
        result = subprocess.run(
            [sys.executable, str(test_script)],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=120  # 2分でタイムアウト
        )
        
        print("📋 テスト実行結果:")
        print("-" * 30)
        
        if result.stdout:
            print("📤 標準出力:")
            print(result.stdout)
        
        if result.stderr:
            print("⚠️ エラー出力:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ API統合テスト完了")
            return True
        else:
            print(f"❌ テスト実行失敗 (終了コード: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ テスト実行がタイムアウトしました")
        return False
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        return False

def main():
    """メイン実行"""
    success = run_api_integration_test()
    
    if success:
        print("\n🎉 API統合テスト完了！")
        print("💡 次のステップ:")
        print("   1. API認証情報を .env ファイルに設定")
        print("   2. python test_execution_demo.py でデモ実行")
        print("   3. python main.py で本格運用開始")
    else:
        print("\n⚠️ テスト実行で問題が発生しました")
        print("💡 トラブルシューティング:")
        print("   1. 依存関係の確認: pip install -r requirements.txt")
        print("   2. Python環境の確認: python --version")
        print("   3. モジュールパスの確認")

if __name__ == "__main__":
    main()
