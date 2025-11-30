#!/usr/bin/env python3
"""
環境チェックスクリプト

必要な依存関係（FFmpeg、AutoHotkey、YMM4等）の存在確認を行う
"""
from __future__ import annotations

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.utils.ffmpeg_utils import detect_ffmpeg, FFMPEG_INSTALL_GUIDE


def check_ffmpeg() -> bool:
    """FFmpegの確認"""
    print("\n" + "=" * 50)
    print("FFmpeg チェック")
    print("=" * 50)
    
    info = detect_ffmpeg()
    
    if info.available:
        print(f"✅ FFmpeg: インストール済み")
        print(f"   パス: {info.path}")
        print(f"   バージョン: {info.version or '不明'}")
        print(f"   libx264: {'✅' if info.has_libx264 else '⚠️ 未検出'}")
        print(f"   AAC: {'✅' if info.has_aac else '⚠️ 未検出'}")
        return True
    else:
        print("❌ FFmpeg: 未インストール")
        print(FFMPEG_INSTALL_GUIDE)
        return False


def check_autohotkey() -> bool:
    """AutoHotkeyの確認"""
    print("\n" + "=" * 50)
    print("AutoHotkey チェック")
    print("=" * 50)
    
    ahk_paths = [
        Path("C:/Program Files/AutoHotkey/AutoHotkey.exe"),
        Path("C:/Program Files/AutoHotkey/v2/AutoHotkey.exe"),
    ]
    
    for path in ahk_paths:
        if path.exists():
            print(f"✅ AutoHotkey: インストール済み")
            print(f"   パス: {path}")
            return True
    
    print("❌ AutoHotkey: 未インストール (YMM4自動操作には必要)")
    print("   インストール: https://www.autohotkey.com/")
    return False


def check_ymm4() -> bool:
    """YMM4の確認"""
    print("\n" + "=" * 50)
    print("YMM4 (ゆっくりMovieMaker4) チェック")
    print("=" * 50)
    
    ymm4_paths = [
        Path("C:/Program Files/YMM4/YMM4.exe"),
        Path("D:/Program Files/YMM4/YMM4.exe"),
    ]
    
    for path in ymm4_paths:
        if path.exists():
            print(f"✅ YMM4: インストール済み")
            print(f"   パス: {path}")
            return True
    
    print("⚠️ YMM4: 標準パスに見つかりません")
    print("   ダウンロード: https://manjubox.net/ymm4/")
    print("   (MoviePyフォールバックで動画生成は可能です)")
    return False


def check_python_packages() -> bool:
    """Pythonパッケージの確認"""
    print("\n" + "=" * 50)
    print("Python パッケージ チェック")
    print("=" * 50)
    
    packages = [
        ("moviepy", "MoviePy"),
        ("PIL", "Pillow"),
        ("aiohttp", "aiohttp"),
        ("google.generativeai", "Google Generative AI"),
        ("google.auth", "Google Auth"),
        ("googleapiclient", "Google API Client"),
    ]
    
    all_ok = True
    for module, name in packages:
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name}: 未インストール")
            all_ok = False
    
    return all_ok


def check_google_api() -> bool:
    """Google API認証の確認"""
    print("\n" + "=" * 50)
    print("Google API 認証チェック")
    print("=" * 50)
    
    from config.settings import settings
    
    # クライアントシークレット
    client_secrets = settings.GOOGLE_CLIENT_SECRETS_FILE
    if client_secrets.exists():
        print(f"✅ クライアントシークレット: {client_secrets.name}")
    else:
        print(f"❌ クライアントシークレット: 未設定")
        print(f"   セットアップ: python scripts/google_auth_setup.py")
        return False
    
    # トークン
    token_file = settings.GOOGLE_OAUTH_TOKEN_FILE
    if token_file.exists():
        print(f"✅ OAuthトークン: {token_file.name}")
        
        # トークンの有効性確認
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(
                str(token_file),
                settings.GOOGLE_SCOPES
            )
            if creds.valid:
                print("✅ トークン: 有効")
            elif creds.expired:
                print("⚠️ トークン: 期限切れ（再認証が必要）")
            return True
        except Exception as e:
            print(f"⚠️ トークン検証エラー: {e}")
            return False
    else:
        print(f"❌ OAuthトークン: 未取得")
        print(f"   認証実行: python scripts/google_auth_setup.py")
        return False


def main():
    """メイン処理"""
    print("\n" + "=" * 60)
    print("NLMandSlideVideoGenerator 環境チェック")
    print("=" * 60)
    
    results = {
        "ffmpeg": check_ffmpeg(),
        "autohotkey": check_autohotkey(),
        "ymm4": check_ymm4(),
        "python_packages": check_python_packages(),
        "google_api": check_google_api(),
    }
    
    print("\n" + "=" * 50)
    print("サマリー")
    print("=" * 50)
    
    essential_ok = results["python_packages"]
    
    if essential_ok:
        print("✅ 必須コンポーネント: OK")
    else:
        print("❌ 必須コンポーネント: 要対応")
    
    if results["ffmpeg"]:
        print("✅ 動画出力: FFmpegで高品質出力が可能")
    else:
        print("⚠️ 動画出力: FFmpegインストール推奨")
    
    if results["autohotkey"] and results["ymm4"]:
        print("✅ YMM4連携: 利用可能")
    else:
        print("⚠️ YMM4連携: 一部未対応 (MoviePyで代替可能)")
    
    if results["google_api"]:
        print("✅ Google Slides API: 利用可能")
    else:
        print("⚠️ Google Slides API: 未設定 (モックモードで動作)")
    
    return 0 if essential_ok else 1


if __name__ == "__main__":
    sys.exit(main())
