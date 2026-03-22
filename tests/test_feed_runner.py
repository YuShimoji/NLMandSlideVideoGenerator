"""CLI フィードランナーの統合テスト。"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from src.feed.feed_runner import build_parser, run
from src.feed.inoreader_client import Article


# --- Fixtures ---


def _make_articles(count=3):
    return [
        Article(
            title=f"Test Article {i}",
            url=f"https://example.com/article-{i}",
            published=datetime(2026, 3, 21, 10, 0, tzinfo=timezone.utc),
            source_name="Test Source",
            summary=f"Summary {i}",
        )
        for i in range(count)
    ]


# --- Parser Tests ---


class TestBuildParser:
    def test_unread_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--unread"])
        assert args.unread is True

    def test_folder_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--folder", "Tech News"])
        assert args.folder == "Tech News"

    def test_starred_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--starred"])
        assert args.starred is True

    def test_subscriptions_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--subscriptions"])
        assert args.subscriptions is True

    def test_mutual_exclusion(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--unread", "--starred"])

    def test_count_default(self):
        parser = build_parser()
        args = parser.parse_args(["--unread"])
        assert args.count == 50

    def test_custom_output(self):
        parser = build_parser()
        args = parser.parse_args(["--unread", "--output", "./custom/"])
        assert args.output == Path("./custom/")


# --- Run Tests ---


class TestRun:
    @patch("src.feed.feed_runner.InoreaderClient")
    def test_unread_success(self, mock_client_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.get_unread_articles.return_value = _make_articles(3)
        mock_client_cls.return_value = mock_client

        parser = build_parser()
        args = parser.parse_args(["--unread", "--days", "0", "--output", str(tmp_path)])
        exit_code = run(args)

        assert exit_code == 0
        assert (tmp_path / "topics.json").exists()
        assert (tmp_path / "feed_report.md").exists()

        topics = json.loads((tmp_path / "topics.json").read_text(encoding="utf-8"))
        assert len(topics) == 3

    @patch("src.feed.feed_runner.InoreaderClient")
    def test_folder_success(self, mock_client_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.get_folder_articles.return_value = _make_articles(2)
        mock_client_cls.return_value = mock_client

        parser = build_parser()
        args = parser.parse_args(["--folder", "AI", "--days", "0", "--output", str(tmp_path)])
        exit_code = run(args)

        assert exit_code == 0
        mock_client.get_folder_articles.assert_called_once_with(
            folder="AI", count=50, include_read=False
        )

    @patch("src.feed.feed_runner.InoreaderClient")
    def test_starred_success(self, mock_client_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.get_starred_articles.return_value = _make_articles(1)
        mock_client_cls.return_value = mock_client

        parser = build_parser()
        args = parser.parse_args(["--starred", "--days", "0", "--output", str(tmp_path)])
        exit_code = run(args)

        assert exit_code == 0

    @patch("src.feed.feed_runner.InoreaderClient")
    def test_subscriptions_list(self, mock_client_cls, tmp_path, capsys):
        mock_client = MagicMock()
        mock_client.get_subscriptions.return_value = [
            {"title": "TechCrunch", "url": "https://tc.com/feed", "categories": []},
        ]
        mock_client_cls.return_value = mock_client

        parser = build_parser()
        args = parser.parse_args(["--subscriptions"])
        exit_code = run(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "TechCrunch" in captured.out

    @patch("src.feed.feed_runner.InoreaderClient")
    def test_no_articles_found(self, mock_client_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.get_unread_articles.return_value = []
        mock_client_cls.return_value = mock_client

        parser = build_parser()
        args = parser.parse_args(["--unread", "--output", str(tmp_path)])
        exit_code = run(args)

        assert exit_code == 0

    @patch("src.feed.feed_runner.InoreaderClient")
    def test_auth_error(self, mock_client_cls):
        from src.feed.inoreader_client import InoreaderAuthError

        mock_client_cls.side_effect = InoreaderAuthError("Missing token")

        parser = build_parser()
        args = parser.parse_args(["--unread"])
        exit_code = run(args)

        assert exit_code == 1

    @patch("src.feed.feed_runner.InoreaderClient")
    def test_rate_limit_error(self, mock_client_cls):
        from src.feed.inoreader_client import InoreaderRateLimitError

        mock_client = MagicMock()
        mock_client.get_unread_articles.side_effect = InoreaderRateLimitError("Limit reached")
        mock_client_cls.return_value = mock_client

        parser = build_parser()
        args = parser.parse_args(["--unread"])
        exit_code = run(args)

        assert exit_code == 2

    @patch("src.feed.feed_runner.InoreaderClient")
    def test_api_error(self, mock_client_cls):
        from src.feed.inoreader_client import InoreaderAPIError

        mock_client = MagicMock()
        mock_client.get_unread_articles.side_effect = InoreaderAPIError("Server error")
        mock_client_cls.return_value = mock_client

        parser = build_parser()
        args = parser.parse_args(["--unread"])
        exit_code = run(args)

        assert exit_code == 3

    @patch("src.feed.feed_runner.InoreaderClient")
    def test_output_files_content(self, mock_client_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.get_unread_articles.return_value = _make_articles(2)
        mock_client_cls.return_value = mock_client

        parser = build_parser()
        args = parser.parse_args(["--unread", "--days", "0", "--output", str(tmp_path)])
        run(args)

        # topics.json の構造確認
        topics = json.loads((tmp_path / "topics.json").read_text(encoding="utf-8"))
        for topic in topics:
            assert "topic" in topic
            assert "urls" in topic
            assert isinstance(topic["urls"], list)

        # feed_report.md の存在確認
        report = (tmp_path / "feed_report.md").read_text(encoding="utf-8")
        assert "Feed Report" in report
        assert "Test Article" in report

    @patch("src.feed.feed_runner.InoreaderClient")
    def test_batch_flag_creates_batch_json(self, mock_client_cls, tmp_path):
        """--batch フラグで batch_topics.json が生成されること (SP-048 Phase 2)"""
        mock_client = MagicMock()
        mock_client.get_unread_articles.return_value = _make_articles(3)
        mock_client_cls.return_value = mock_client

        parser = build_parser()
        args = parser.parse_args(["--unread", "--days", "0", "--output", str(tmp_path), "--batch"])
        exit_code = run(args)

        assert exit_code == 0
        assert (tmp_path / "topics.json").exists()
        assert (tmp_path / "batch_topics.json").exists()

        batch = json.loads((tmp_path / "batch_topics.json").read_text(encoding="utf-8"))
        assert "batch_name" in batch
        assert "defaults" in batch
        assert "topics" in batch
        assert len(batch["topics"]) == 3
        # seed_urls が設定されていること
        for t in batch["topics"]:
            assert "topic" in t
            assert "seed_urls" in t

    @patch("src.feed.feed_runner.InoreaderClient")
    def test_batch_custom_name(self, mock_client_cls, tmp_path):
        """--batch-name でカスタム名が設定されること"""
        mock_client = MagicMock()
        mock_client.get_unread_articles.return_value = _make_articles(1)
        mock_client_cls.return_value = mock_client

        parser = build_parser()
        args = parser.parse_args([
            "--unread", "--days", "0", "--output", str(tmp_path),
            "--batch", "--batch-name", "my_custom_batch",
        ])
        exit_code = run(args)

        assert exit_code == 0
        batch = json.loads((tmp_path / "batch_topics.json").read_text(encoding="utf-8"))
        assert batch["batch_name"] == "my_custom_batch"

    @patch("src.feed.feed_runner.InoreaderClient")
    def test_no_batch_flag_omits_batch_json(self, mock_client_cls, tmp_path):
        """--batch なしで batch_topics.json が生成されないこと"""
        mock_client = MagicMock()
        mock_client.get_unread_articles.return_value = _make_articles(2)
        mock_client_cls.return_value = mock_client

        parser = build_parser()
        args = parser.parse_args(["--unread", "--days", "0", "--output", str(tmp_path)])
        exit_code = run(args)

        assert exit_code == 0
        assert (tmp_path / "topics.json").exists()
        assert not (tmp_path / "batch_topics.json").exists()
