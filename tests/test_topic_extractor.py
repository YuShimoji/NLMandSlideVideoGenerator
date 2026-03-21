"""トピック抽出ロジックのユニットテスト。"""

import json
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.feed.inoreader_client import Article
from src.feed.topic_extractor import (
    _strip_html,
    extract_topics,
    save_feed_report,
    save_topics_json,
)


# --- Fixtures ---


def _make_article(
    title="Test Article",
    url="https://example.com/article",
    published=None,
    source_name="Tech Blog",
    summary="",
    categories=None,
):
    if published is None:
        published = datetime.now(timezone.utc)
    return Article(
        title=title,
        url=url,
        published=published,
        source_name=source_name,
        summary=summary,
        categories=categories or [],
    )


# --- HTML Strip Tests ---


class TestStripHtml:
    def test_strips_tags(self):
        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_collapses_whitespace(self):
        assert _strip_html("<p>Hello   \n  world</p>") == "Hello world"

    def test_truncates_long_text(self):
        result = _strip_html("x" * 500)
        assert len(result) <= 300

    def test_empty_string(self):
        assert _strip_html("") == ""


# --- Extract Topics Tests ---


class TestExtractTopics:
    def test_basic_extraction(self):
        articles = [_make_article(title="AI News", url="https://example.com/ai")]
        topics = extract_topics(articles, freshness_days=7)
        assert len(topics) == 1
        assert topics[0]["topic"] == "AI News"
        assert topics[0]["urls"] == ["https://example.com/ai"]

    def test_freshness_filter(self):
        recent = _make_article(
            title="Recent",
            published=datetime.now(timezone.utc) - timedelta(days=1),
        )
        old = _make_article(
            title="Old",
            published=datetime.now(timezone.utc) - timedelta(days=30),
        )
        topics = extract_topics([recent, old], freshness_days=7)
        assert len(topics) == 1
        assert topics[0]["topic"] == "Recent"

    def test_freshness_disabled(self):
        old = _make_article(
            title="Old",
            published=datetime.now(timezone.utc) - timedelta(days=365),
        )
        topics = extract_topics([old], freshness_days=0)
        assert len(topics) == 1

    def test_deduplication_by_url(self):
        a1 = _make_article(title="Article A", url="https://example.com/article")
        a2 = _make_article(title="Article B", url="https://example.com/article")
        topics = extract_topics([a1, a2], freshness_days=0)
        assert len(topics) == 1

    def test_deduplication_case_insensitive(self):
        a1 = _make_article(title="A", url="https://Example.COM/Article/")
        a2 = _make_article(title="B", url="https://example.com/article")
        topics = extract_topics([a1, a2], freshness_days=0)
        assert len(topics) == 1

    def test_deduplication_disabled(self):
        a1 = _make_article(title="A", url="https://example.com/article")
        a2 = _make_article(title="B", url="https://example.com/article")
        topics = extract_topics([a1, a2], freshness_days=0, deduplicate=False)
        assert len(topics) == 2

    def test_empty_title_skipped(self):
        a = _make_article(title="   ")
        topics = extract_topics([a], freshness_days=0)
        assert len(topics) == 0

    def test_summary_stripped(self):
        a = _make_article(summary="<p>HTML <b>summary</b></p>")
        topics = extract_topics([a], freshness_days=0)
        assert "<" not in topics[0]["summary"]

    def test_categories_preserved(self):
        a = _make_article(categories=["Tech", "AI"])
        topics = extract_topics([a], freshness_days=0)
        assert topics[0]["categories"] == ["Tech", "AI"]

    def test_empty_input(self):
        topics = extract_topics([], freshness_days=7)
        assert topics == []

    def test_multiple_sources(self):
        articles = [
            _make_article(title="A1", url="https://a.com/1", source_name="Source A"),
            _make_article(title="B1", url="https://b.com/1", source_name="Source B"),
            _make_article(title="A2", url="https://a.com/2", source_name="Source A"),
        ]
        topics = extract_topics(articles, freshness_days=0)
        assert len(topics) == 3
        sources = {t["source"] for t in topics}
        assert sources == {"Source A", "Source B"}


# --- Save Topics JSON Tests ---


class TestSaveTopicsJson:
    def test_creates_json_file(self, tmp_path):
        topics = [
            {"topic": "Test", "urls": ["https://example.com"], "source": "Blog", "published": "2026-03-21"}
        ]
        path = save_topics_json(topics, tmp_path)
        assert path.exists()
        assert path.name == "topics.json"

        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert len(loaded) == 1
        assert loaded[0]["topic"] == "Test"

    def test_creates_output_dir(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        save_topics_json([], nested)
        assert nested.exists()

    def test_japanese_content(self, tmp_path):
        topics = [
            {"topic": "日本語テスト", "urls": [], "source": "ブログ", "published": "2026-03-21"}
        ]
        path = save_topics_json(topics, tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "日本語テスト" in content

    def test_overwrites_existing(self, tmp_path):
        save_topics_json([{"topic": "Old"}], tmp_path)
        save_topics_json([{"topic": "New"}], tmp_path)
        loaded = json.loads((tmp_path / "topics.json").read_text(encoding="utf-8"))
        assert loaded[0]["topic"] == "New"


# --- Save Feed Report Tests ---


class TestSaveFeedReport:
    def test_creates_markdown_report(self, tmp_path):
        topics = [
            {
                "topic": "AI Breakthrough",
                "urls": ["https://example.com/ai"],
                "source": "TechCrunch",
                "published": "2026-03-21T10:00:00+00:00",
                "summary": "Summary text",
                "categories": ["Tech"],
            }
        ]
        report_date = datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc)
        path = save_feed_report(topics, tmp_path, report_date=report_date)

        assert path.exists()
        assert path.name == "feed_report.md"

        content = path.read_text(encoding="utf-8")
        assert "Feed Report" in content
        assert "2026-03-21" in content
        assert "AI Breakthrough" in content
        assert "TechCrunch" in content
        assert "1件" in content

    def test_source_breakdown(self, tmp_path):
        topics = [
            {"topic": "A", "urls": [], "source": "Source1", "published": ""},
            {"topic": "B", "urls": [], "source": "Source1", "published": ""},
            {"topic": "C", "urls": [], "source": "Source2", "published": ""},
        ]
        path = save_feed_report(topics, tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "Source1: 2件" in content
        assert "Source2: 1件" in content

    def test_detail_section_with_summary(self, tmp_path):
        topics = [
            {
                "topic": "Article With Summary",
                "urls": ["https://example.com"],
                "source": "Blog",
                "published": "2026-03-21",
                "summary": "Detailed summary here",
            }
        ]
        path = save_feed_report(topics, tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "## 詳細" in content
        assert "Detailed summary here" in content

    def test_empty_topics(self, tmp_path):
        path = save_feed_report([], tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "0件" in content
