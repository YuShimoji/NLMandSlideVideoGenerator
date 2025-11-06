#!/usr/bin/env python3
"""
API統合テスト
実環境でのAPI連携動作確認
"""
import sys
try:
    # Windowsのコンソールで絵文字などが原因で失敗しないようUTF-8に設定
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import asyncio
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from tests.api_test_runner import APIIntegrationTest


async def main():
    """メインテスト実行"""
    test_runner = APIIntegrationTest()
    await test_runner.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
