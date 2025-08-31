#!/usr/bin/env python3
"""
デバッグ用テスト
"""
import sys
from pathlib import Path

print("=== デバッグテスト開始 ===")
print(f"Python version: {sys.version}")
print(f"Current directory: {Path.cwd()}")

# パス追加
project_root = Path(__file__).parent
src_path = project_root / "src"
print(f"Source path: {src_path}")
print(f"Source exists: {src_path.exists()}")

sys.path.insert(0, str(src_path))
print(f"Updated sys.path: {sys.path[:3]}")

try:
    print("設定ファイルのインポートを試行中...")
    from config.settings import settings
    print(f"✓ 設定読み込み成功: {settings.APP_NAME}")
except Exception as e:
    print(f"✗ 設定読み込み失敗: {e}")
    import traceback
    traceback.print_exc()

print("=== デバッグテスト完了 ===")
