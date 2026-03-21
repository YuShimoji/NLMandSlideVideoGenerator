"""記事からパイプライン用トピック候補を抽出する。

重複排除、鮮度フィルタを適用し、
パイプライン互換 JSON + レビュー用 Markdown レポートを生成する。
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .inoreader_client import Article

logger = logging.getLogger(__name__)


def _strip_html(html: str) -> str:
    """HTML タグを除去してプレーンテキストを返す。"""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300]


def extract_topics(
    articles: List[Article],
    freshness_days: int = 7,
    deduplicate: bool = True,
) -> List[Dict[str, Any]]:
    """記事リストからトピック候補を抽出する。

    Args:
        articles: Article オブジェクトのリスト。
        freshness_days: この日数以内の記事のみ残す。0 で無制限。
        deduplicate: URL ベースの重複排除を行うか。

    Returns:
        パイプライン互換のトピックリスト。
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=freshness_days) if freshness_days > 0 else None

    seen_urls: set = set()
    topics: List[Dict[str, Any]] = []

    for article in articles:
        # 鮮度フィルタ
        if cutoff and article.published < cutoff:
            continue

        # URL 重複排除
        normalized_url = article.url.rstrip("/").lower()
        if deduplicate and normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)

        # タイトルが空の記事はスキップ
        if not article.title.strip():
            continue

        topics.append(
            {
                "topic": article.title,
                "urls": [article.url] if article.url else [],
                "source": article.source_name,
                "published": article.published.isoformat(),
                "summary": _strip_html(article.summary) if article.summary else "",
                "categories": article.categories,
            }
        )

    logger.info(
        "Extracted %d topics from %d articles (freshness=%d days)",
        len(topics),
        len(articles),
        freshness_days,
    )
    return topics


def save_topics_json(topics: List[Dict[str, Any]], output_dir: Path) -> Path:
    """パイプライン互換 JSON を出力する。

    出力形式: 各エントリは {"topic": str, "urls": [str]} を含む。
    追加情報 (source, published, summary) もそのまま保持する。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "topics.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)

    logger.info("Saved %d topics to %s", len(topics), output_path)
    return output_path


def save_feed_report(
    topics: List[Dict[str, Any]],
    output_dir: Path,
    report_date: Optional[datetime] = None,
) -> Path:
    """人間レビュー用 Markdown レポートを生成する。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "feed_report.md"

    if report_date is None:
        report_date = datetime.now(timezone.utc)

    # ソース別集計
    sources: Dict[str, int] = {}
    for t in topics:
        src = t.get("source", "Unknown")
        sources[src] = sources.get(src, 0) + 1

    lines = [
        f"# Feed Report ({report_date.strftime('%Y-%m-%d %H:%M UTC')})",
        "",
        f"取得件数: {len(topics)}件 | ソース: {len(sources)}フィード",
        "",
        "## ソース別内訳",
        "",
    ]
    for src, cnt in sorted(sources.items(), key=lambda x: -x[1]):
        lines.append(f"- {src}: {cnt}件")

    lines.extend(
        [
            "",
            "## トピック一覧",
            "",
            "| # | トピック | ソース | 公開日 | URL |",
            "|---|---------|--------|--------|-----|",
        ]
    )

    for i, t in enumerate(topics, 1):
        title = t["topic"][:60] + ("..." if len(t["topic"]) > 60 else "")
        pub = t.get("published", "")[:10]
        url = t.get("urls", [""])[0] if t.get("urls") else ""
        url_md = f"[link]({url})" if url else "-"
        source = t.get("source", "-")
        lines.append(f"| {i} | {title} | {source} | {pub} | {url_md} |")

    # サマリー付き詳細セクション
    if any(t.get("summary") for t in topics):
        lines.extend(["", "## 詳細", ""])
        for i, t in enumerate(topics, 1):
            summary = t.get("summary", "")
            if summary:
                lines.append(f"### {i}. {t['topic']}")
                lines.append(f"- ソース: {t.get('source', '-')}")
                lines.append(f"- URL: {t.get('urls', [''])[0]}")
                lines.append(f"- 要約: {summary}")
                lines.append("")

    content = "\n".join(lines) + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("Saved feed report to %s", output_path)
    return output_path
