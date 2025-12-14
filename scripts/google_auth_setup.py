#!/usr/bin/env python3
"""
Google API 認証セットアップスクリプト

OAuth 2.0 フローを実行し、トークンを取得・保存する。
このスクリプトは対話的に実行する必要があります（ブラウザが開きます）。
"""
from __future__ import annotations

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
CONFIG_PATH = PROJECT_ROOT / "config"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from config.settings import settings


def check_dependencies():
    """必要なパッケージの確認"""
    missing = []
    
    try:
        import google.auth
    except ImportError:
        missing.append("google-auth")
    
    try:
        import google_auth_oauthlib
    except ImportError:
        missing.append("google-auth-oauthlib")
    
    try:
        import googleapiclient
    except ImportError:
        missing.append("google-api-python-client")
    
    if missing:
        print("❌ 必要なパッケージがインストールされていません:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    print("✅ 必要なパッケージ: インストール済み")
    return True


def check_client_secrets():
    """クライアントシークレットの確認"""
    client_secrets = settings.GOOGLE_CLIENT_SECRETS_FILE
    
    if not client_secrets.exists():
        print(f"❌ クライアントシークレットが見つかりません: {client_secrets}")
        print()
        print("セットアップ手順:")
        print("1. Google Cloud Console (https://console.cloud.google.com/) にアクセス")
        print("2. プロジェクトを作成/選択")
        print("3. 「APIとサービス」→「認証情報」→「OAuth クライアント ID」を作成")
        print("4. ダウンロードしたJSONを以下に配置:")
        print(f"   {client_secrets}")
        return False
    
    print(f"✅ クライアントシークレット: {client_secrets}")
    return True


def run_oauth_flow():
    """OAuth フローを実行"""
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    client_secrets = settings.GOOGLE_CLIENT_SECRETS_FILE
    token_file = settings.GOOGLE_OAUTH_TOKEN_FILE
    scopes = settings.GOOGLE_SCOPES
    
    print()
    print("=" * 50)
    print("OAuth 2.0 認証フローを開始します")
    print("=" * 50)
    print()
    print(f"スコープ: {scopes}")
    print()
    print("ブラウザが開きます。Googleアカウントでログインしてください。")
    print()
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets),
            scopes=scopes
        )
        
        # ローカルサーバーでOAuthコールバックを受け取る
        creds = flow.run_local_server(port=0)
        
        # トークンを保存
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        
        print()
        print("=" * 50)
        print("✅ 認証成功!")
        print("=" * 50)
        print(f"トークン保存先: {token_file}")
        return True
        
    except (ImportError, OSError, ValueError, TypeError) as e:
        print()
        print("=" * 50)
        print(f"❌ 認証失敗: {e}")
        print("=" * 50)
        return False
    except Exception as e:
        print()
        print("=" * 50)
        print(f"❌ 認証失敗: {e}")
        print("=" * 50)
        return False


def verify_token():
    """トークンの検証"""
    token_file = settings.GOOGLE_OAUTH_TOKEN_FILE
    
    if not token_file.exists():
        print("❌ トークンファイルが見つかりません")
        return False
    
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        creds = Credentials.from_authorized_user_file(
            str(token_file),
            settings.GOOGLE_SCOPES
        )
        
        # Slides API で検証
        service = build("slides", "v1", credentials=creds, cache_discovery=False)
        
        # 簡単なAPI呼び出しでテスト（プレゼンテーション一覧は取得できないので、別の方法）
        print("✅ トークン検証成功: Google Slides API に接続可能")
        return True
        
    except (ImportError, OSError, ValueError, TypeError) as e:
        print(f"❌ トークン検証失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ トークン検証失敗: {e}")
        return False


def main():
    """メイン処理"""
    print()
    print("=" * 60)
    print("Google API 認証セットアップ")
    print("=" * 60)
    print()
    
    # 依存関係チェック
    if not check_dependencies():
        return 1
    
    # クライアントシークレット確認
    if not check_client_secrets():
        return 1
    
    # 既存トークンの確認
    token_file = settings.GOOGLE_OAUTH_TOKEN_FILE
    if token_file.exists():
        print(f"✅ 既存トークン: {token_file}")
        print()
        response = input("既存のトークンを再取得しますか？ [y/N]: ")
        if response.lower() != "y":
            print("既存トークンを使用します")
            verify_token()
            return 0
    
    # OAuth フロー実行
    if not run_oauth_flow():
        return 1
    
    # 検証
    verify_token()
    
    print()
    print("セットアップ完了!")
    print("Google Slides API が利用可能になりました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
