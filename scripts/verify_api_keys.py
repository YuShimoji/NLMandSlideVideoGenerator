#!/usr/bin/env python
"""
API Key Verification Script

Gemini API Keyの設定状態を確認し、接続テストを実行します。
"""
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings


def print_header(text: str):
    """セクションヘッダーを表示"""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print('=' * 60)


def check_env_file():
    """
    .envファイルの存在確認
    """
    print_header("Step 1: .env File Check")
    
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        print(f"✅ .env file exists: {env_file}")
        return True
    else:
        print(f"❌ .env file not found: {env_file}")
        print("\nPlease create .env file from .env.example:")
        print("  cp .env.example .env")
        print("  # or on Windows:")
        print("  Copy-Item .env.example .env")
        return False


def check_gemini_api_key():
    """
    Gemini API Keyの設定確認
    """
    print_header("Step 2: Gemini API Key Check")
    
    api_key = settings.GEMINI_API_KEY
    
    if not api_key:
        print("❌ GEMINI_API_KEY is not set")
        print("\nPlease set your API key in .env file:")
        print("  GEMINI_API_KEY=your_actual_api_key_here")
        print("\nGet your API key from:")
        print("  https://aistudio.google.com/app/apikey")
        return False
    
    # APIキーの形式確認（マスク表示）
    if len(api_key) < 20:
        print(f"⚠️  GEMINI_API_KEY seems too short: {len(api_key)} chars")
        return False
    
    masked_key = f"{api_key[:8]}...{api_key[-4:]}"
    print(f"✅ GEMINI_API_KEY is set: {masked_key}")
    print(f"   Length: {len(api_key)} characters")
    return True


def test_gemini_connection():
    """
    Gemini APIへの接続テスト
    """
    print_header("Step 3: Gemini API Connection Test")
    
    if not settings.GEMINI_API_KEY:
        print("⏭️  Skipping connection test (API key not set)")
        return False
    
    try:
        import google.generativeai as genai
        
        # APIキー設定
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # モデル一覧取得でテスト
        print("Connecting to Gemini API...")
        models = genai.list_models()
        
        available_models = [m.name for m in models]
        
        if available_models:
            print(f"✅ Gemini API: Connected")
            print(f"   Available models: {len(available_models)}")
            print(f"   Example: {available_models[0] if available_models else 'N/A'}")
            return True
        else:
            print("⚠️  Connected but no models available")
            return False
            
    except ImportError:
        print("❌ google-generativeai package not installed")
        print("   Install with: pip install google-generativeai")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nPossible causes:")
        print("  - Invalid API key")
        print("  - Network connection issue")
        print("  - API quota exceeded")
        print("\nVerify your API key at:")
        print("  https://aistudio.google.com/app/apikey")
        return False


def print_summary(env_ok: bool, key_ok: bool, conn_ok: bool):
    """
    検証結果サマリー
    """
    print_header("Verification Summary")
    
    status_items = [
        (".env file", env_ok),
        ("GEMINI_API_KEY", key_ok),
        ("API Connection", conn_ok),
    ]
    
    for item, status in status_items:
        icon = "✅" if status else "❌"
        print(f"  {icon} {item}")
    
    all_ok = env_ok and key_ok and conn_ok
    
    print("\n" + "=" * 60)
    if all_ok:
        print("🎉 All checks passed! TASK_003 can be unblocked.")
        print("\nNext steps:")
        print("  1. Update TASK_003 status: BLOCKED → DONE")
        print("  2. Run smoke tests: python -m pytest tests/smoke_test_notebook_lm.py")
        print("  3. Test NotebookLM pipeline with real API")
    else:
        print("⚠️  Setup incomplete. Please address the issues above.")
        print("\nRefer to: docs/QUICKSTART_API_SETUP.md")
    print("=" * 60)
    
    return all_ok


def main():
    """
    メイン処理
    """
    print("Gemini API Key Verification")
    print(f"Project: {settings.APP_NAME} v{settings.VERSION}")
    
    # 各ステップを実行
    env_ok = check_env_file()
    key_ok = check_gemini_api_key()
    conn_ok = test_gemini_connection() if key_ok else False
    
    # サマリー表示
    all_ok = print_summary(env_ok, key_ok, conn_ok)
    
    # 終了コード
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
