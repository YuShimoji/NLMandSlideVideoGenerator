"""
Google 認証ヘルパー (gapi 名前空間)
- OAuth2 のトークン読み込み/更新
- スコープは settings.GOOGLE_SCOPES を既定とする

非対話環境では新規フローを行わず、既存トークンがない場合は None を返す設計。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, List

from config.settings import settings


class SimpleLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")


logger = SimpleLogger()


class GoogleAuthHelper:
    def __init__(self,
                 client_secrets_file: Path | None = None,
                 token_file: Path | None = None,
                 scopes: Optional[List[str]] = None) -> None:
        self.client_secrets_file = client_secrets_file or settings.GOOGLE_CLIENT_SECRETS_FILE
        self.token_file = token_file or settings.GOOGLE_OAUTH_TOKEN_FILE
        self.scopes = scopes or settings.GOOGLE_SCOPES

    def get_credentials(self):  # -> Optional[Credentials]
        try:
            from google.oauth2.credentials import Credentials
        except Exception:
            logger.warning("google-auth ライブラリが見つからないため、認証をスキップします")
            return None

        creds = None
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), self.scopes)
            except Exception as e:
                logger.warning(f"トークンファイルの読み込みに失敗しました: {e}")
                creds = None

        # 新規フローは行わない（非対話環境を想定）。
        if not creds:
            if not self.client_secrets_file.exists():
                logger.warning("Google クライアントシークレットが見つかりません。モックモードで動作します。")
            else:
                logger.warning("OAuth トークンが存在しません。対話フローが必要ですが、この環境ではスキップします。")
            return None

        return creds

    def save_token(self, creds) -> None:
        try:
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        except Exception as e:
            logger.warning(f"トークンの保存に失敗: {e}")
