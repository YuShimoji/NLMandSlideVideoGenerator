"""InoReader フィード取得の CLI エントリポイント。

Usage:
    python -m src.feed.feed_runner --unread --count 50
    python -m src.feed.feed_runner --folder "Tech News" --count 30
    python -m src.feed.feed_runner --starred --count 20
    python -m src.feed.feed_runner --unread --days 3 --output ./output/feed/
"""

import argparse
import logging
import sys
from pathlib import Path

from .inoreader_client import (
    InoreaderAuthError,
    InoreaderAPIError,
    InoreaderClient,
    InoreaderRateLimitError,
)
from .topic_extractor import (
    extract_topics,
    save_batch_json,
    save_feed_report,
    save_topics_json,
)

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path("output/feed")
DEFAULT_COUNT = 50
DEFAULT_FRESHNESS_DAYS = 7


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="InoReader フィードからトピック候補を取得",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python -m src.feed.feed_runner --unread --count 50
  python -m src.feed.feed_runner --folder "Tech News" --days 3
  python -m src.feed.feed_runner --starred --output ./my_topics/

環境変数:
  INOREADER_APP_ID    InoReader App ID
  INOREADER_APP_KEY   InoReader App Key
  INOREADER_TOKEN     OAuth 2.0 アクセストークン
""",
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--unread", action="store_true", help="未読記事を取得"
    )
    source_group.add_argument(
        "--folder", type=str, help="指定フォルダの記事を取得"
    )
    source_group.add_argument(
        "--starred", action="store_true", help="スター付き記事を取得"
    )
    source_group.add_argument(
        "--subscriptions", action="store_true", help="サブスクリプション一覧を表示 (トピック取得なし)"
    )

    parser.add_argument(
        "--count", type=int, default=DEFAULT_COUNT, help=f"取得件数 (default: {DEFAULT_COUNT})"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_FRESHNESS_DAYS,
        help=f"鮮度フィルタ日数。0で無制限 (default: {DEFAULT_FRESHNESS_DAYS})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"出力ディレクトリ (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--include-read",
        action="store_true",
        help="既読記事も含める (--folder 使用時のみ)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="バッチキュー(SP-040)互換形式で batch_topics.json も出力",
    )
    parser.add_argument(
        "--batch-name",
        type=str,
        default="feed_batch",
        help="バッチ名 (--batch 使用時、default: feed_batch)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="詳細ログを表示"
    )

    return parser


def run(args: argparse.Namespace) -> int:
    """メイン実行ロジック。戻り値は終了コード。"""
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        client = InoreaderClient()
    except InoreaderAuthError as e:
        logger.error("認証エラー: %s", e)
        print(f"\n認証エラー: {e}", file=sys.stderr)
        print("\n.env ファイルに以下を設定してください:", file=sys.stderr)
        print("  INOREADER_APP_ID=your_app_id", file=sys.stderr)
        print("  INOREADER_APP_KEY=your_app_key", file=sys.stderr)
        print("  INOREADER_TOKEN=your_oauth_token", file=sys.stderr)
        return 1

    try:
        # サブスクリプション一覧モード
        if args.subscriptions:
            subs = client.get_subscriptions()
            print(f"\nサブスクリプション一覧 ({len(subs)}件):\n")
            for sub in subs:
                categories = [
                    c.get("label", "") for c in sub.get("categories", [])
                ]
                folder_str = f" [{', '.join(categories)}]" if categories else ""
                print(f"  - {sub.get('title', 'Unknown')}{folder_str}")
                print(f"    URL: {sub.get('url', '')}")
            return 0

        # 記事取得
        if args.unread:
            print(f"\n未読記事を取得中 (最大{args.count}件)...")
            articles = client.get_unread_articles(count=args.count)
        elif args.folder:
            print(f"\nフォルダ '{args.folder}' の記事を取得中 (最大{args.count}件)...")
            articles = client.get_folder_articles(
                folder=args.folder,
                count=args.count,
                include_read=args.include_read,
            )
        elif args.starred:
            print(f"\nスター付き記事を取得中 (最大{args.count}件)...")
            articles = client.get_starred_articles(count=args.count)
        else:
            print("取得ソースを指定してください (--unread / --folder / --starred)", file=sys.stderr)
            return 1

        if not articles:
            print("\n記事が見つかりませんでした。")
            return 0

        print(f"  取得完了: {len(articles)}件")

        # トピック抽出
        topics = extract_topics(
            articles,
            freshness_days=args.days,
            deduplicate=True,
        )

        if not topics:
            print(f"\n鮮度フィルタ ({args.days}日以内) を通過した記事がありません。")
            print("--days 0 で無制限にできます。")
            return 0

        print(f"  フィルタ後: {len(topics)}件")

        # 出力
        json_path = save_topics_json(topics, args.output)
        report_path = save_feed_report(topics, args.output)

        print(f"\n出力完了:")
        print(f"  topics.json:    {json_path}")
        print(f"  feed_report.md: {report_path}")

        # バッチキュー互換出力 (SP-048 Phase 2)
        if args.batch:
            batch_path = save_batch_json(
                topics, args.output, batch_name=args.batch_name,
            )
            print(f"  batch_topics.json: {batch_path}")
            print(
                f"\nバッチ実行: python scripts/research_cli.py batch "
                f"--topics {batch_path}"
            )
        else:
            print(f"\ntopics.json をパイプラインの入力として使用できます。")
            print(f"バッチ互換形式で出力するには --batch を追加してください。")
        return 0

    except InoreaderRateLimitError as e:
        logger.error("レート制限: %s", e)
        print(f"\nレート制限に達しました: {e}", file=sys.stderr)
        return 2
    except InoreaderAPIError as e:
        logger.error("APIエラー: %s", e)
        print(f"\nAPIエラー: {e}", file=sys.stderr)
        return 3


def main():
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
