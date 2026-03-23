"""InoReader API クライアントのユニットテスト。

HTTP レスポンスをモックし、クライアントの振る舞いを検証する。
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.feed.inoreader_client import (
    Article,
    InoreaderAuthError,
    InoreaderAPIError,
    InoreaderClient,
    InoreaderRateLimitError,
)


# --- Fixtures ---


def _make_client(**kwargs):
    """テスト用クライアントを作成 (認証チェックをバイパス)。"""
    defaults = {
        "app_id": "test_app_id",
        "app_key": "test_app_key",
        "token": "test_token",
    }
    defaults.update(kwargs)
    return InoreaderClient(**defaults)


def _mock_article_item(
    title="Test Article",
    url="https://example.com/article",
    published=1711000000,
    source_title="Tech Blog",
    author="Alice",
    summary="<p>Test summary</p>",
    categories=None,
):
    """API レスポンスの item 形式を模擬。"""
    return {
        "id": f"tag:google.com,2005:reader/item/{published}",
        "title": title,
        "canonical": [{"href": url}],
        "published": published,
        "origin": {"title": source_title, "htmlUrl": f"https://{source_title.lower().replace(' ', '')}.com"},
        "author": author,
        "summary": {"content": summary},
        "categories": categories or [],
    }


def _mock_stream_response(items, continuation=None):
    """stream/contents エンドポイントのレスポンスを模擬。"""
    resp = {"items": items}
    if continuation:
        resp["continuation"] = continuation
    return resp


# --- Auth Tests ---


class TestInoreaderAuth:
    def test_missing_app_id_raises(self):
        with pytest.raises(InoreaderAuthError, match="APP_ID"):
            InoreaderClient(app_id="", app_key="key", token="tok")

    def test_missing_app_key_raises(self):
        with pytest.raises(InoreaderAuthError, match="APP_KEY"):
            InoreaderClient(app_id="id", app_key="", token="tok")

    def test_missing_token_raises(self):
        with pytest.raises(InoreaderAuthError, match="TOKEN"):
            InoreaderClient(app_id="id", app_key="key", token="")

    def test_valid_credentials_succeed(self):
        client = _make_client()
        assert client.app_id == "test_app_id"
        assert client.app_key == "test_app_key"

    def test_env_var_fallback(self):
        with patch.dict(
            "os.environ",
            {
                "INOREADER_APP_ID": "env_id",
                "INOREADER_APP_KEY": "env_key",
                "INOREADER_TOKEN": "env_token",
            },
        ):
            client = InoreaderClient()
            assert client.app_id == "env_id"
            assert client.token == "env_token"


# --- Request Tests ---


class TestInoreaderRequest:
    @patch("src.feed.inoreader_client.requests.Session")
    def test_successful_request(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"subscriptions": []}
        mock_resp.headers = {}
        mock_session_cls.return_value.get.return_value = mock_resp

        client = _make_client()
        result = client._request("subscription/list")
        assert result == {"subscriptions": []}

    @patch("src.feed.inoreader_client.requests.Session")
    def test_401_raises_auth_error(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.headers = {}
        mock_resp.text = "Unauthorized"
        mock_session_cls.return_value.get.return_value = mock_resp

        client = _make_client()
        with pytest.raises(InoreaderAuthError, match="expired"):
            client._request("subscription/list")

    @patch("src.feed.inoreader_client.requests.Session")
    def test_429_raises_rate_limit(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {}
        mock_resp.text = "Too Many Requests"
        mock_session_cls.return_value.get.return_value = mock_resp

        client = _make_client()
        with pytest.raises(InoreaderRateLimitError):
            client._request("subscription/list")

    @patch("src.feed.inoreader_client.requests.Session")
    def test_rate_limit_header_warning(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_resp.headers = {
            "X-Reader-Zone1-Usage": "98",
            "X-Reader-Zone1-Limit": "100",
        }
        mock_session_cls.return_value.get.return_value = mock_resp

        client = _make_client()
        # Should not raise, just log warning
        client._request("subscription/list")

    @patch("src.feed.inoreader_client.requests.Session")
    def test_rate_limit_header_exceeded(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_resp.headers = {
            "X-Reader-Zone1-Usage": "100",
            "X-Reader-Zone1-Limit": "100",
        }
        mock_session_cls.return_value.get.return_value = mock_resp

        client = _make_client()
        with pytest.raises(InoreaderRateLimitError):
            client._request("subscription/list")

    @patch("src.feed.inoreader_client.requests.Session")
    def test_500_raises_api_error(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.headers = {}
        mock_resp.text = "Internal Server Error"
        mock_session_cls.return_value.get.return_value = mock_resp

        client = _make_client()
        with pytest.raises(InoreaderAPIError, match="500"):
            client._request("subscription/list")


# --- Article Parsing Tests ---


class TestArticleParsing:
    def test_parse_complete_article(self):
        item = _mock_article_item()
        article = InoreaderClient._parse_article(item)
        assert article is not None
        assert article.title == "Test Article"
        assert article.url == "https://example.com/article"
        assert article.source_name == "Tech Blog"
        assert article.author == "Alice"

    def test_parse_article_no_title_returns_none(self):
        item = _mock_article_item(title="")
        assert InoreaderClient._parse_article(item) is None

    def test_parse_article_alternate_url(self):
        item = _mock_article_item()
        del item["canonical"]
        item["alternate"] = [{"href": "https://alt.example.com/article"}]
        article = InoreaderClient._parse_article(item)
        assert article.url == "https://alt.example.com/article"

    def test_parse_article_origin_fallback_url(self):
        item = _mock_article_item()
        del item["canonical"]
        article = InoreaderClient._parse_article(item)
        assert article.url == "https://techblog.com"

    def test_parse_article_categories(self):
        item = _mock_article_item(
            categories=[
                "user/123/state/com.google/reading-list",
                "user/123/label/Tech",
                "user/123/label/AI",
            ]
        )
        article = InoreaderClient._parse_article(item)
        assert "Tech" in article.categories
        assert "AI" in article.categories

    def test_parse_article_published_datetime(self):
        item = _mock_article_item(published=1711000000)
        article = InoreaderClient._parse_article(item)
        assert article.published.year >= 2024
        assert article.published.tzinfo == timezone.utc

    def test_article_to_dict(self):
        article = Article(
            title="Test",
            url="https://example.com",
            published=datetime(2026, 3, 21, tzinfo=timezone.utc),
            source_name="Blog",
        )
        d = article.to_dict()
        assert d["title"] == "Test"
        assert d["url"] == "https://example.com"
        assert "2026-03-21" in d["published"]


# --- Fetch Articles Tests ---


class TestFetchArticles:
    @patch("src.feed.inoreader_client.requests.Session")
    def test_get_unread_articles(self, mock_session_cls):
        items = [_mock_article_item(title=f"Article {i}") for i in range(3)]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _mock_stream_response(items)
        mock_resp.headers = {}
        mock_session_cls.return_value.get.return_value = mock_resp

        client = _make_client()
        articles = client.get_unread_articles(count=10)
        assert len(articles) == 3

    @patch("src.feed.inoreader_client.requests.Session")
    def test_get_folder_articles(self, mock_session_cls):
        items = [_mock_article_item(title="Folder Article")]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _mock_stream_response(items)
        mock_resp.headers = {}
        mock_session_cls.return_value.get.return_value = mock_resp

        client = _make_client()
        articles = client.get_folder_articles("Tech", count=10)
        assert len(articles) == 1

        # stream_id にフォルダ名が含まれることを確認
        call_args = mock_session_cls.return_value.get.call_args
        assert "label/Tech" in call_args[1].get("url", call_args[0][0] if call_args[0] else "")

    @patch("src.feed.inoreader_client.requests.Session")
    def test_pagination(self, mock_session_cls):
        # ページ1: continuation あり
        items_page1 = [_mock_article_item(title=f"P1-{i}") for i in range(3)]
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.json.return_value = _mock_stream_response(items_page1, continuation="cont_token")
        resp1.headers = {}

        # ページ2: continuation なし (最後)
        items_page2 = [_mock_article_item(title=f"P2-{i}") for i in range(2)]
        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = _mock_stream_response(items_page2)
        resp2.headers = {}

        mock_session_cls.return_value.get.side_effect = [resp1, resp2]

        client = _make_client()
        articles = client.get_unread_articles(count=200)
        assert len(articles) == 5

    @patch("src.feed.inoreader_client.requests.Session")
    def test_get_subscriptions(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "subscriptions": [
                {"title": "TechCrunch", "url": "https://techcrunch.com/feed"},
                {"title": "Ars Technica", "url": "https://arstechnica.com/feed"},
            ]
        }
        mock_resp.headers = {}
        mock_session_cls.return_value.get.return_value = mock_resp

        client = _make_client()
        subs = client.get_subscriptions()
        assert len(subs) == 2
        assert subs[0]["title"] == "TechCrunch"
