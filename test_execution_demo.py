#!/usr/bin/env python3
"""
テスト実行とデモンストレーション
実際の動作確認と成果物の生成
"""
import sys
try:
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

from tests.demo_runner import DemoRunner


async def main():
    """メインデモ実行"""
    demo = DemoRunner()
    await demo.run_full_demo()

    print("\n🎉 デモンストレーション完了!")
    print("\n💡 次のステップ:")
    print("  1. API認証情報を設定")
    print("  2. 実際のNotebookLM連携をテスト")
    print("  3. Google Slides APIを設定")
    print("  4. YouTube APIを設定")
    print("  5. 本格的な動画生成を実行")


if __name__ == "__main__":
    asyncio.run(main())
