"""InoReader API クライアント。

OAuth 2.0 + App ID/Key の二層認証で InoReader REST API にアクセスする。
Google Reader API 互換エンドポイントを使用。
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.inoreader.com/reader/api/0"

# Stream ID constants
READING_LIST = "user/-/state/com.google/reading-list"
READ_STATE = "user/-/state/com.google/read"
STARRED_STATE = "user/-/state/com.google/starred"


@dataclass
class Article:
    """InoReader から取得した記事。"""

    title: str
    url: str
    published: datetime
    source_name: str
    author: str = ""
    summary: str = ""
    article_id: str = ""
    categories: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "published": self.published.isoformat(),
            "source_name": self.source_name,
            "author": self.author,
            "summary": self.summary[:200] if self.summary else "",
        }


class InoreaderAuthError(Exception):
    """認証エラー。"""


class InoreaderAPIError(Exception):
    """API呼び出しエラー。"""


class InoreaderRateLimitError(InoreaderAPIError):
    """レート制限到達。"""


class InoreaderClient:
    """InoReader REST API クライアント。

    環境変数から認証情報を読み取る:
    - INOREADER_APP_ID: アプリケーション ID
    - INOREADER_APP_KEY: アプリケーションキー
    - INOREADER_TOKEN: OAuth 2.0 アクセストークン
    """

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_key: Optional[str] = None,
        token: Optional[str] = None,
    ):
        self.app_id = app_id or os.getenv("INOREADER_APP_ID", "")
        self.app_key = app_key or os.getenv("INOREADER_APP_KEY", "")
        self.token = token or os.getenv("INOREADER_TOKEN", "")

        if not self.app_id or not self.app_key:
            raise InoreaderAuthError(
                "INOREADER_APP_ID and INOREADER_APP_KEY are required. "
                "Register at https://www.inoreader.com/developers/register-app"
            )
        if not self.token:
            raise InoreaderAuthError(
                "INOREADER_TOKEN is required. "
                "Obtain an OAuth 2.0 token from InoReader."
            )

        self._session = requests.Session()
        self._session.headers.update(
            {
                "AppId": self.app_id,
                "AppKey": self.app_key,
                "Authorization": f"Bearer {self.token}",
            }
        )

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """API リクエストを実行し、レート制限を監視する。"""
        url = f"{BASE_URL}/{endpoint}"
        try:
            resp = self._session.get(url, params=params, timeout=30)
        except requests.RequestException as e:
            raise InoreaderAPIError(f"Request failed: {e}") from e

        # レート制限ヘッダー監視
        zone1_usage = resp.headers.get("X-Reader-Zone1-Usage")
        zone1_limit = resp.headers.get("X-Reader-Zone1-Limit")
        if zone1_usage and zone1_limit:
            usage, limit = int(zone1_usage), int(zone1_limit)
            remaining = limit - usage
            if remaining <= 5:
                logger.warning(
                    "InoReader Zone1 rate limit approaching: %d/%d used", usage, limit
                )
            if remaining <= 0:
                raise InoreaderRateLimitError(
                    f"Zone1 rate limit reached: {usage}/{limit}"
                )

        if resp.status_code == 401:
            raise InoreaderAuthError("Invalid or expired token")
        if resp.status_code == 429:
            raise InoreaderRateLimitError("Rate limit exceeded (HTTP 429)")
        if resp.status_code != 200:
            raise InoreaderAPIError(
                f"API error {resp.status_code}: {resp.text[:200]}"
            )

        return resp.json()

    def get_subscriptions(self) -> List[Dict[str, Any]]:
        """サブスクリプション一覧を取得。"""
        data = self._request("subscription/list")
        return data.get("subscriptions", [])

    def get_stream_contents(
        self,
        stream_id: str = READING_LIST,
        count: int = 50,
        exclude_read: bool = True,
        continuation: Optional[str] = None,
        older_than: Optional[int] = None,
    ) -> Dict[str, Any]:
        """記事ストリームを取得。

        Args:
            stream_id: ストリームID。デフォルトは全記事。
            count: 取得件数 (最大100)。
            exclude_read: 既読を除外するか。
            continuation: ページネーション用トークン。
            older_than: この Unix timestamp より古い記事のみ。
        """
        params: Dict[str, Any] = {"n": min(count, 100)}
        if exclude_read:
            params["xt"] = READ_STATE
        if continuation:
            params["c"] = continuation
        if older_than is not None:
            params["ot"] = older_than

        return self._request(f"stream/contents/{stream_id}", params)

    def get_unread_articles(
        self, count: int = 50, folder: Optional[str] = None
    ) -> List[Article]:
        """未読記事を Article リストとして取得。

        Args:
            count: 取得件数。
            folder: フォルダ名でフィルタ (省略時は全フィード)。
        """
        if folder:
            stream_id = f"user/-/label/{folder}"
        else:
            stream_id = READING_LIST

        return self._fetch_articles(stream_id, count, exclude_read=True)

    def get_folder_articles(
        self, folder: str, count: int = 50, include_read: bool = False
    ) -> List[Article]:
        """特定フォルダの記事を取得。"""
        stream_id = f"user/-/label/{folder}"
        return self._fetch_articles(stream_id, count, exclude_read=not include_read)

    def get_starred_articles(self, count: int = 50) -> List[Article]:
        """スター付き記事を取得。"""
        return self._fetch_articles(STARRED_STATE, count, exclude_read=False)

    def _fetch_articles(
        self, stream_id: str, count: int, exclude_read: bool
    ) -> List[Article]:
        """記事を取得し Article オブジェクトに変換。"""
        articles: List[Article] = []
        continuation: Optional[str] = None
        remaining = count

        while remaining > 0:
            batch_size = min(remaining, 100)
            data = self.get_stream_contents(
                stream_id=stream_id,
                count=batch_size,
                exclude_read=exclude_read,
                continuation=continuation,
            )

            items = data.get("items", [])
            for item in items:
                article = self._parse_article(item)
                if article:
                    articles.append(article)

            remaining -= len(items)
            continuation = data.get("continuation")
            if not continuation or not items:
                break

        logger.info("Fetched %d articles from stream %s", len(articles), stream_id)
        return articles

    @staticmethod
    def _parse_article(item: Dict[str, Any]) -> Optional[Article]:
        """API レスポンスの item を Article に変換。"""
        title = item.get("title", "").strip()
        if not title:
            return None

        # URL: canonical > alternate > origin
        url = ""
        for link_list in [
            item.get("canonical", []),
            item.get("alternate", []),
        ]:
            if link_list and isinstance(link_list, list):
                url = link_list[0].get("href", "")
                if url:
                    break
        if not url:
            origin = item.get("origin", {})
            url = origin.get("htmlUrl", "")

        # 公開日
        published_ts = item.get("published", 0)
        published = datetime.fromtimestamp(published_ts, tz=timezone.utc)

        # ソース名
        origin = item.get("origin", {})
        source_name = origin.get("title", "Unknown")

        # カテゴリ
        categories = []
        for cat in item.get("categories", []):
            if isinstance(cat, str) and "/label/" in cat:
                label = cat.split("/label/")[-1]
                categories.append(label)

        return Article(
            title=title,
            url=url,
            published=published,
            source_name=source_name,
            author=item.get("author", ""),
            summary=item.get("summary", {}).get("content", ""),
            article_id=item.get("id", ""),
            categories=categories,
        )
