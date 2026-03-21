"""StockImageClient 拡張カバレッジテスト (68% → 85%+)

対象: src/core/visual/stock_image_client.py
既存テスト (test_stock_image_client.py) で未カバーの行を重点的にテストする。
- __init__ パラメータ、validate_api_keys
- search() オーケストレーション (Pexels優先 → Pixabayフォールバック)
- _search_pexels / _search_pixabay 各種パス
- _parse 系レスポンスバリエーション
- download 成功・失敗パス
- _request_with_retry リトライロジック
- _translate_queries_to_english エッジケース
- search_for_segments 追加パス
"""
import hashlib
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from requests.exceptions import ConnectionError, HTTPError, Timeout

from core.visual.stock_image_client import (
    StockImage,
    StockImageClient,
    _BACKOFF_BASE,
    _MAX_RETRIES,
    _RETRYABLE_STATUS_CODES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path: Path) -> StockImageClient:
    """両方のAPIキーを持つクライアント。"""
    return StockImageClient(
        pexels_api_key="test_pexels_key",
        pixabay_api_key="test_pixabay_key",
        cache_dir=tmp_path / "stock_cache",
    )


@pytest.fixture
def pexels_only_client(tmp_path: Path) -> StockImageClient:
    """Pexelsキーのみ。"""
    return StockImageClient(
        pexels_api_key="pexels_only",
        pixabay_api_key="",
        cache_dir=tmp_path / "stock_cache",
    )


@pytest.fixture
def pixabay_only_client(tmp_path: Path) -> StockImageClient:
    """Pixabayキーのみ。"""
    return StockImageClient(
        pexels_api_key="",
        pixabay_api_key="pixabay_only",
        cache_dir=tmp_path / "stock_cache",
    )


@pytest.fixture
def no_keys_client(tmp_path: Path) -> StockImageClient:
    """APIキーなし。"""
    return StockImageClient(
        pexels_api_key="",
        pixabay_api_key="",
        cache_dir=tmp_path / "stock_cache",
    )


def _make_mock_response(
    status_code: int = 200,
    json_data: dict | None = None,
    content: bytes = b"",
    headers: dict | None = None,
) -> MagicMock:
    """テスト用モックHTTPレスポンスを生成。"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.content = content
    resp.headers = headers or {}
    if status_code >= 400:
        error = HTTPError(response=resp)
        resp.raise_for_status.side_effect = error
    else:
        resp.raise_for_status = MagicMock()
    return resp


# ===========================================================================
# __init__ / 設定パラメータ
# ===========================================================================

class TestInit:
    """__init__ パラメータバリエーション。"""

    def test_custom_api_keys(self, tmp_path: Path) -> None:
        """明示的に渡したAPIキーが設定される。"""
        c = StockImageClient(
            pexels_api_key="my_pexels",
            pixabay_api_key="my_pixabay",
            cache_dir=tmp_path / "c",
        )
        assert c.pexels_api_key == "my_pexels"
        assert c.pixabay_api_key == "my_pixabay"

    def test_custom_cache_dir(self, tmp_path: Path) -> None:
        """カスタムcache_dirが作成される。"""
        cache = tmp_path / "custom_cache"
        c = StockImageClient(
            pexels_api_key="", pixabay_api_key="",
            cache_dir=cache,
        )
        assert c.cache_dir == cache
        assert cache.exists()

    def test_defaults_from_settings(self, tmp_path: Path) -> None:
        """引数Noneの場合settingsからフォールバック。"""
        with patch("core.visual.stock_image_client.settings") as mock_settings:
            mock_settings.STOCK_IMAGE_SETTINGS = {
                "pexels_api_key": "from_settings_p",
                "pixabay_api_key": "from_settings_x",
            }
            mock_settings.DATA_DIR = tmp_path
            c = StockImageClient()
        assert c.pexels_api_key == "from_settings_p"
        assert c.pixabay_api_key == "from_settings_x"

    def test_session_user_agent(self, client: StockImageClient) -> None:
        """セッションにUser-Agentが設定されている。"""
        assert "NLMSlideVideoGenerator" in client.session.headers.get("User-Agent", "")


# ===========================================================================
# validate_api_keys (lines 90-129)
# ===========================================================================

class TestValidateApiKeys:
    """APIキー検証。"""

    def test_both_keys_valid(self, client: StockImageClient) -> None:
        """両方のキーが有効 → 両方True。"""
        resp_ok = _make_mock_response(200)
        with patch.object(client.session, "get", return_value=resp_ok):
            with patch.object(client, "_rate_limit"):
                result = client.validate_api_keys()
        assert result == {"pexels": True, "pixabay": True}

    def test_pexels_invalid_key(self, client: StockImageClient) -> None:
        """Pexels 401 → pexels=False, Pixabay OK → pixabay=True。"""
        resp_401 = _make_mock_response(401)
        resp_ok = _make_mock_response(200)

        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # 最初のGET = Pexels検証, 2番目 = Pixabay検証
            if call_count == 1:
                return resp_401
            return resp_ok

        with patch.object(client.session, "get", side_effect=side_effect):
            with patch.object(client, "_rate_limit"):
                result = client.validate_api_keys()
        assert result["pexels"] is False
        assert result["pixabay"] is True

    def test_pixabay_invalid_key(self, client: StockImageClient) -> None:
        """Pexels OK, Pixabay 403 → pixabay=False。"""
        resp_ok = _make_mock_response(200)
        resp_403 = _make_mock_response(403)

        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return resp_ok
            return resp_403

        with patch.object(client.session, "get", side_effect=side_effect):
            with patch.object(client, "_rate_limit"):
                result = client.validate_api_keys()
        assert result["pexels"] is True
        assert result["pixabay"] is False

    def test_pexels_connection_error(self, client: StockImageClient) -> None:
        """Pexels接続エラー → pexels=False, Pixabay正常。"""
        resp_ok = _make_mock_response(200)
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("connection refused")
            return resp_ok

        with patch.object(client.session, "get", side_effect=side_effect):
            with patch.object(client, "_rate_limit"):
                result = client.validate_api_keys()
        assert result["pexels"] is False
        assert result["pixabay"] is True

    def test_pixabay_timeout(self, client: StockImageClient) -> None:
        """Pixabayタイムアウト → pixabay=False。"""
        resp_ok = _make_mock_response(200)
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return resp_ok
            raise Timeout("request timed out")

        with patch.object(client.session, "get", side_effect=side_effect):
            with patch.object(client, "_rate_limit"):
                result = client.validate_api_keys()
        assert result["pexels"] is True
        assert result["pixabay"] is False

    def test_no_keys_skips_validation(self, no_keys_client: StockImageClient) -> None:
        """キーなし → 両方False、リクエストなし。"""
        with patch.object(no_keys_client.session, "get") as mock_get:
            result = no_keys_client.validate_api_keys()
        mock_get.assert_not_called()
        assert result == {"pexels": False, "pixabay": False}

    def test_pexels_unexpected_status(self, client: StockImageClient) -> None:
        """Pexels 500 → pexels=False (warningログ)。"""
        resp_500 = _make_mock_response(500)
        resp_500.raise_for_status = MagicMock()  # 500でもraise_for_statusは呼ばない
        resp_ok = _make_mock_response(200)

        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return resp_500
            return resp_ok

        with patch.object(client.session, "get", side_effect=side_effect):
            with patch.object(client, "_rate_limit"):
                result = client.validate_api_keys()
        assert result["pexels"] is False
        assert result["pixabay"] is True


# ===========================================================================
# search() オーケストレーション (lines 131-172)
# ===========================================================================

class TestSearchOrchestration:
    """search() のWikimedia→Pexels→Pixabayフォールバック。

    Wikimediaは空を返す前提で、Pexels/Pixabayのフォールバックをテストする。
    """

    @pytest.fixture(autouse=True)
    def _disable_wikimedia(self, client: StockImageClient) -> None:
        """Wikimediaを無効化してPexels/Pixabayのフォールバックに集中する。"""
        client.enable_wikimedia = False

    def test_pexels_success_skips_pixabay(self, client: StockImageClient) -> None:
        """Pexels成功 → Pixabayは呼ばれない。"""
        pexels_img = StockImage(
            id="pexels_1", url="", download_url="https://example.com/1.jpg",
            width=1920, height=1080, photographer="P1", source="pexels",
        )
        with patch.object(client, "_search_pexels", return_value=[pexels_img]) as mock_p:
            with patch.object(client, "_search_pixabay") as mock_x:
                results = client.search("test")
        mock_p.assert_called_once()
        mock_x.assert_not_called()
        assert len(results) == 1
        assert results[0].source == "pexels"

    def test_pexels_empty_falls_to_pixabay(self, client: StockImageClient) -> None:
        """Pexels結果0件 → Pixabayへフォールバック。"""
        pixabay_img = StockImage(
            id="pixabay_1", url="", download_url="https://example.com/2.jpg",
            width=1920, height=1080, photographer="X1", source="pixabay",
        )
        with patch.object(client, "_search_pexels", return_value=[]):
            with patch.object(client, "_search_pixabay", return_value=[pixabay_img]):
                results = client.search("test")
        assert len(results) == 1
        assert results[0].source == "pixabay"

    def test_pexels_http_error_falls_to_pixabay(self, client: StockImageClient) -> None:
        """Pexels HTTPError → Pixabayフォールバック。"""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        http_err = HTTPError(response=mock_resp)

        pixabay_img = StockImage(
            id="pixabay_2", url="", download_url="https://example.com/3.jpg",
            width=1920, height=1080, photographer="X2", source="pixabay",
        )
        with patch.object(client, "_search_pexels", side_effect=http_err):
            with patch.object(client, "_search_pixabay", return_value=[pixabay_img]):
                results = client.search("test")
        assert len(results) == 1
        assert results[0].source == "pixabay"

    def test_pexels_connection_error_falls_to_pixabay(self, client: StockImageClient) -> None:
        """Pexels ConnectionError → Pixabayフォールバック。"""
        pixabay_img = StockImage(
            id="pixabay_3", url="", download_url="", width=1920, height=1080,
            photographer="X3", source="pixabay",
        )
        with patch.object(client, "_search_pexels", side_effect=ConnectionError("conn")):
            with patch.object(client, "_search_pixabay", return_value=[pixabay_img]):
                results = client.search("test")
        assert len(results) == 1

    def test_pexels_timeout_falls_to_pixabay(self, client: StockImageClient) -> None:
        """Pexels Timeout → Pixabayフォールバック。"""
        pixabay_img = StockImage(
            id="pixabay_4", url="", download_url="", width=1920, height=1080,
            photographer="X4", source="pixabay",
        )
        with patch.object(client, "_search_pexels", side_effect=Timeout("timeout")):
            with patch.object(client, "_search_pixabay", return_value=[pixabay_img]):
                results = client.search("test")
        assert len(results) == 1

    def test_pexels_generic_exception_falls_to_pixabay(self, client: StockImageClient) -> None:
        """Pexels 汎用例外 → Pixabayフォールバック。"""
        pixabay_img = StockImage(
            id="pixabay_5", url="", download_url="", width=1920, height=1080,
            photographer="X5", source="pixabay",
        )
        with patch.object(client, "_search_pexels", side_effect=ValueError("unexpected")):
            with patch.object(client, "_search_pixabay", return_value=[pixabay_img]):
                results = client.search("test")
        assert len(results) == 1

    def test_both_fail_returns_empty(self, client: StockImageClient) -> None:
        """両方失敗 → 空リスト。"""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        http_err = HTTPError(response=mock_resp)
        with patch.object(client, "_search_pexels", side_effect=http_err):
            with patch.object(client, "_search_pixabay", side_effect=ConnectionError("fail")):
                results = client.search("test")
        assert results == []

    def test_pixabay_http_error_returns_empty(self, client: StockImageClient) -> None:
        """Pexels空 + Pixabay HTTPError → 空リスト。"""
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        http_err = HTTPError(response=mock_resp)
        with patch.object(client, "_search_pexels", return_value=[]):
            with patch.object(client, "_search_pixabay", side_effect=http_err):
                results = client.search("test")
        assert results == []

    def test_pixabay_timeout_returns_empty(self, client: StockImageClient) -> None:
        """Pexels空 + Pixabay Timeout → 空リスト。"""
        with patch.object(client, "_search_pexels", return_value=[]):
            with patch.object(client, "_search_pixabay", side_effect=Timeout("t")):
                results = client.search("test")
        assert results == []

    def test_pixabay_generic_exception_returns_empty(self, client: StockImageClient) -> None:
        """Pexels空 + Pixabay 汎用例外 → 空リスト。"""
        with patch.object(client, "_search_pexels", return_value=[]):
            with patch.object(client, "_search_pixabay", side_effect=RuntimeError("err")):
                results = client.search("test")
        assert results == []

    def test_pixabay_empty_returns_empty(self, client: StockImageClient) -> None:
        """Pexels空 + Pixabay空 → 空リスト。"""
        with patch.object(client, "_search_pexels", return_value=[]):
            with patch.object(client, "_search_pixabay", return_value=[]):
                results = client.search("test")
        assert results == []

    def test_pexels_only_client_no_pixabay_call(self, pexels_only_client: StockImageClient) -> None:
        """Pixabayキーなし → _search_pixabay は呼ばれない。"""
        with patch.object(pexels_only_client, "_search_pexels", return_value=[]):
            with patch.object(pexels_only_client, "_search_pixabay") as mock_x:
                pexels_only_client.search("test")
        mock_x.assert_not_called()

    def test_pixabay_only_client_no_pexels_call(self, pixabay_only_client: StockImageClient) -> None:
        """Pexelsキーなし → _search_pexels は呼ばれない。"""
        with patch.object(pixabay_only_client, "_search_pexels") as mock_p:
            with patch.object(pixabay_only_client, "_search_pixabay", return_value=[]):
                pixabay_only_client.search("test")
        mock_p.assert_not_called()

    def test_http_error_with_none_response(self, client: StockImageClient) -> None:
        """HTTPError.response が None のケース (line 148)。"""
        http_err = HTTPError("no response")
        http_err.response = None
        pixabay_img = StockImage(
            id="pixabay_6", url="", download_url="", width=1920, height=1080,
            photographer="X6", source="pixabay",
        )
        with patch.object(client, "_search_pexels", side_effect=http_err):
            with patch.object(client, "_search_pixabay", return_value=[pixabay_img]):
                results = client.search("test")
        assert len(results) == 1

    def test_pixabay_http_error_none_response(self, client: StockImageClient) -> None:
        """Pixabay HTTPError.response が None (line 162)。"""
        http_err = HTTPError("no response")
        http_err.response = None
        with patch.object(client, "_search_pexels", return_value=[]):
            with patch.object(client, "_search_pixabay", side_effect=http_err):
                results = client.search("test")
        assert results == []


# ===========================================================================
# _search_pexels 詳細パス
# ===========================================================================

class TestSearchPexelsDetail:
    """_search_pexels 内部パス。"""

    def test_large2x_fallback_to_large(self, client: StockImageClient) -> None:
        """large2x なし → large にフォールバック。"""
        resp = _make_mock_response(200, json_data={
            "photos": [{
                "id": 10,
                "width": 2000, "height": 1200,
                "url": "https://pexels.com/photo/10",
                "photographer": "Alice",
                "alt": "test",
                "src": {"large": "https://images.pexels.com/large.jpg"},
            }],
        })
        with patch.object(client.session, "get", return_value=resp):
            results = client._search_pexels("test", 5, "landscape", 1920)
        assert len(results) == 1
        assert results[0].download_url == "https://images.pexels.com/large.jpg"

    def test_large_fallback_to_original(self, client: StockImageClient) -> None:
        """large2x も large もなし → original にフォールバック。"""
        resp = _make_mock_response(200, json_data={
            "photos": [{
                "id": 20,
                "width": 2000, "height": 1200,
                "url": "",
                "photographer": "Bob",
                "alt": "",
                "src": {"original": "https://images.pexels.com/original.jpg"},
            }],
        })
        with patch.object(client.session, "get", return_value=resp):
            results = client._search_pexels("test", 5, "landscape", 1920)
        assert len(results) == 1
        assert results[0].download_url == "https://images.pexels.com/original.jpg"

    def test_empty_photos(self, client: StockImageClient) -> None:
        """photos が空 → 空リスト。"""
        resp = _make_mock_response(200, json_data={"photos": []})
        with patch.object(client.session, "get", return_value=resp):
            results = client._search_pexels("test", 5, "landscape", 1920)
        assert results == []

    def test_no_photos_key(self, client: StockImageClient) -> None:
        """photos キーなし → 空リスト。"""
        resp = _make_mock_response(200, json_data={})
        with patch.object(client.session, "get", return_value=resp):
            results = client._search_pexels("test", 5, "landscape", 1920)
        assert results == []

    def test_per_page_capped_at_15(self, client: StockImageClient) -> None:
        """count > 15 → per_page=15。"""
        resp = _make_mock_response(200, json_data={"photos": []})
        with patch.object(client.session, "get", return_value=resp) as mock_get:
            client._search_pexels("test", 50, "landscape", 1920)
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["per_page"] == 15

    def test_multiple_photos_with_filtering(self, client: StockImageClient) -> None:
        """min_width で一部フィルタされる。"""
        resp = _make_mock_response(200, json_data={
            "photos": [
                {"id": 1, "width": 800, "height": 600, "url": "", "photographer": "",
                 "alt": "", "src": {"large2x": "https://a.com/1.jpg"}},
                {"id": 2, "width": 1920, "height": 1080, "url": "", "photographer": "",
                 "alt": "", "src": {"large2x": "https://a.com/2.jpg"}},
                {"id": 3, "width": 3840, "height": 2160, "url": "", "photographer": "",
                 "alt": "", "src": {"large2x": "https://a.com/3.jpg"}},
            ],
        })
        with patch.object(client.session, "get", return_value=resp):
            results = client._search_pexels("test", 5, "landscape", 1920)
        assert len(results) == 2
        assert results[0].id == "pexels_2"
        assert results[1].id == "pexels_3"


# ===========================================================================
# _search_pixabay 詳細パス (lines 330-371)
# ===========================================================================

class TestSearchPixabayDetail:
    """_search_pixabay 内部パス。"""

    def test_orientation_mapping_landscape(self, client: StockImageClient) -> None:
        """orientation="landscape" → "horizontal" にマッピング。"""
        resp = _make_mock_response(200, json_data={"hits": []})
        with patch.object(client.session, "get", return_value=resp) as mock_get:
            client._search_pixabay("test", 5, "landscape", 1920)
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["orientation"] == "horizontal"

    def test_orientation_mapping_portrait(self, client: StockImageClient) -> None:
        """orientation="portrait" → そのまま "portrait"。"""
        resp = _make_mock_response(200, json_data={"hits": []})
        with patch.object(client.session, "get", return_value=resp) as mock_get:
            client._search_pixabay("test", 5, "portrait", 1920)
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["orientation"] == "portrait"

    def test_per_page_capped_at_20(self, client: StockImageClient) -> None:
        """count > 20 → per_page=20。"""
        resp = _make_mock_response(200, json_data={"hits": []})
        with patch.object(client.session, "get", return_value=resp) as mock_get:
            client._search_pixabay("test", 50, "landscape", 1920)
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["per_page"] == 20

    def test_pixabay_tags_parsing(self, client: StockImageClient) -> None:
        """tagsフィールドのカンマ区切り解析。"""
        resp = _make_mock_response(200, json_data={
            "hits": [{
                "id": 100,
                "pageURL": "https://pixabay.com/photos/100",
                "largeImageURL": "https://cdn.pixabay.com/100.jpg",
                "imageWidth": 2000, "imageHeight": 1200,
                "user": "PixUser",
                "tags": "nature, forest, green, tree",
            }],
        })
        with patch.object(client.session, "get", return_value=resp):
            results = client._search_pixabay("nature", 5, "landscape", 1920)
        assert len(results) == 1
        assert results[0].tags == ["nature", "forest", "green", "tree"]

    def test_pixabay_empty_tags(self, client: StockImageClient) -> None:
        """tags が空文字列 → 空リスト。"""
        resp = _make_mock_response(200, json_data={
            "hits": [{
                "id": 200,
                "pageURL": "",
                "largeImageURL": "https://cdn.pixabay.com/200.jpg",
                "imageWidth": 2000, "imageHeight": 1200,
                "user": "User",
                "tags": "",
            }],
        })
        with patch.object(client.session, "get", return_value=resp):
            results = client._search_pixabay("test", 5, "landscape", 1920)
        assert results[0].tags == []

    def test_pixabay_empty_hits(self, client: StockImageClient) -> None:
        """hits が空 → 空リスト。"""
        resp = _make_mock_response(200, json_data={"hits": []})
        with patch.object(client.session, "get", return_value=resp):
            results = client._search_pixabay("test", 5, "landscape", 1920)
        assert results == []

    def test_pixabay_no_hits_key(self, client: StockImageClient) -> None:
        """hits キーなし → 空リスト。"""
        resp = _make_mock_response(200, json_data={"totalHits": 0})
        with patch.object(client.session, "get", return_value=resp):
            results = client._search_pixabay("test", 5, "landscape", 1920)
        assert results == []

    def test_pixabay_multiple_hits(self, client: StockImageClient) -> None:
        """複数件返却。"""
        resp = _make_mock_response(200, json_data={
            "hits": [
                {"id": 301, "pageURL": "", "largeImageURL": "https://cdn/301.jpg",
                 "imageWidth": 2000, "imageHeight": 1200, "user": "U1", "tags": "a, b"},
                {"id": 302, "pageURL": "", "largeImageURL": "https://cdn/302.jpg",
                 "imageWidth": 2000, "imageHeight": 1200, "user": "U2", "tags": "c"},
            ],
        })
        with patch.object(client.session, "get", return_value=resp):
            results = client._search_pixabay("test", 5, "landscape", 1920)
        assert len(results) == 2
        assert results[0].id == "pixabay_301"
        assert results[1].id == "pixabay_302"


# ===========================================================================
# download() 成功・失敗パス (lines 241-279)
# ===========================================================================

class TestDownloadPaths:
    """download() の各経路。"""

    def test_download_png_extension(self, client: StockImageClient) -> None:
        """URLに.pngが含まれる → .png拡張子でキャッシュ。"""
        image = StockImage(
            id="png_1", url="", download_url="https://example.com/image.png",
            width=1920, height=1080, photographer="Test", source="pexels",
        )
        resp = _make_mock_response(200, content=b"\x89PNG\r\n\x1a\nfake_png")
        with patch.object(client.session, "get", return_value=resp):
            result = client.download(image)
        assert result is not None
        assert result.local_path is not None
        assert result.local_path.suffix == ".png"

    def test_download_jpg_extension_default(self, client: StockImageClient) -> None:
        """URLに.pngなし → .jpg拡張子。"""
        image = StockImage(
            id="jpg_1", url="", download_url="https://example.com/image_large",
            width=1920, height=1080, photographer="Test", source="pixabay",
        )
        resp = _make_mock_response(200, content=b"\xff\xd8\xff\xe0fake_jpg")
        with patch.object(client.session, "get", return_value=resp):
            result = client.download(image)
        assert result is not None
        assert result.local_path.suffix == ".jpg"

    def test_download_http_error(self, client: StockImageClient) -> None:
        """ダウンロード中のHTTPError → None。"""
        image = StockImage(
            id="err_1", url="", download_url="https://example.com/fail.jpg",
            width=1920, height=1080, photographer="Test", source="pexels",
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        http_err = HTTPError(response=mock_resp)
        with patch.object(client, "_request_with_retry", side_effect=http_err):
            result = client.download(image)
        assert result is None

    def test_download_http_error_none_response(self, client: StockImageClient) -> None:
        """HTTPError.response が None (line 271)。"""
        image = StockImage(
            id="err_2", url="", download_url="https://example.com/fail2.jpg",
            width=1920, height=1080, photographer="Test", source="pexels",
        )
        http_err = HTTPError("no response")
        http_err.response = None
        with patch.object(client, "_request_with_retry", side_effect=http_err):
            result = client.download(image)
        assert result is None

    def test_download_connection_error(self, client: StockImageClient) -> None:
        """ダウンロード中のConnectionError → None。"""
        image = StockImage(
            id="conn_1", url="", download_url="https://example.com/fail3.jpg",
            width=1920, height=1080, photographer="Test", source="pexels",
        )
        with patch.object(client, "_request_with_retry", side_effect=ConnectionError("down")):
            result = client.download(image)
        assert result is None

    def test_download_timeout_error(self, client: StockImageClient) -> None:
        """ダウンロード中のTimeout → None。"""
        image = StockImage(
            id="to_1", url="", download_url="https://example.com/fail4.jpg",
            width=1920, height=1080, photographer="Test", source="pexels",
        )
        with patch.object(client, "_request_with_retry", side_effect=Timeout("slow")):
            result = client.download(image)
        assert result is None

    def test_download_generic_exception(self, client: StockImageClient) -> None:
        """ダウンロード中の汎用例外 → None。"""
        image = StockImage(
            id="gen_1", url="", download_url="https://example.com/fail5.jpg",
            width=1920, height=1080, photographer="Test", source="pexels",
        )
        with patch.object(client, "_request_with_retry", side_effect=OSError("disk full")):
            result = client.download(image)
        assert result is None


# ===========================================================================
# _request_with_retry (lines 448-521)
# ===========================================================================

class TestRequestWithRetry:
    """リトライロジック。"""

    def test_success_first_attempt(self, client: StockImageClient) -> None:
        """1回目で成功 → そのまま返却。"""
        resp = _make_mock_response(200)
        with patch.object(client.session, "get", return_value=resp):
            result = client._request_with_retry("https://example.com", source_name="Test")
        assert result.status_code == 200

    def test_401_raises_immediately(self, client: StockImageClient) -> None:
        """401 → リトライせず即HTTPError。"""
        resp = _make_mock_response(401)
        with patch.object(client.session, "get", return_value=resp):
            with pytest.raises(HTTPError):
                client._request_with_retry("https://example.com", source_name="Test")

    def test_403_raises_immediately(self, client: StockImageClient) -> None:
        """403 → リトライせず即HTTPError。"""
        resp = _make_mock_response(403)
        with patch.object(client.session, "get", return_value=resp):
            with pytest.raises(HTTPError):
                client._request_with_retry("https://example.com", source_name="Test")

    def test_429_retries_with_backoff(self, client: StockImageClient) -> None:
        """429 → リトライし、最終的に成功。"""
        resp_429 = _make_mock_response(429)
        resp_429.raise_for_status = MagicMock()  # 429はraise_for_statusを直接呼ばない
        resp_ok = _make_mock_response(200)

        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return resp_429
            return resp_ok

        with patch.object(client.session, "get", side_effect=side_effect):
            with patch("core.visual.stock_image_client.time.sleep"):
                result = client._request_with_retry("https://example.com", source_name="Test")
        assert result.status_code == 200

    def test_429_with_retry_after_header(self, client: StockImageClient) -> None:
        """429 + Retry-After ヘッダー → ヘッダー値を使用。"""
        resp_429 = _make_mock_response(429, headers={"Retry-After": "10"})
        resp_429.raise_for_status = MagicMock()
        resp_ok = _make_mock_response(200)

        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return resp_429
            return resp_ok

        with patch.object(client.session, "get", side_effect=side_effect):
            with patch("core.visual.stock_image_client.time.sleep") as mock_sleep:
                result = client._request_with_retry("https://example.com", source_name="Test")
        # Retry-After=10 > backoff 1.0 → sleep(10)
        assert mock_sleep.call_args_list[0][0][0] >= 10.0

    def test_500_retries_then_raises(self, client: StockImageClient) -> None:
        """500がMAX_RETRIES回続く → HTTPError。"""
        resp_500 = _make_mock_response(500)
        resp_500.raise_for_status = MagicMock()

        with patch.object(client.session, "get", return_value=resp_500):
            with patch("core.visual.stock_image_client.time.sleep"):
                with pytest.raises(HTTPError, match="リトライ上限超過"):
                    client._request_with_retry("https://example.com", source_name="Test")

    def test_connection_error_retries_then_raises(self, client: StockImageClient) -> None:
        """ConnectionError がMAX_RETRIES回続く → ConnectionError。"""
        with patch.object(client.session, "get", side_effect=ConnectionError("refused")):
            with patch("core.visual.stock_image_client.time.sleep"):
                with pytest.raises(ConnectionError):
                    client._request_with_retry("https://example.com", source_name="Test")

    def test_timeout_retries_then_raises(self, client: StockImageClient) -> None:
        """Timeout がMAX_RETRIES回続く → Timeout。"""
        with patch.object(client.session, "get", side_effect=Timeout("slow")):
            with patch("core.visual.stock_image_client.time.sleep"):
                with pytest.raises(Timeout):
                    client._request_with_retry("https://example.com", source_name="Test")

    def test_connection_error_then_success(self, client: StockImageClient) -> None:
        """ConnectionError 1回 → 2回目で成功。"""
        resp_ok = _make_mock_response(200)
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("temp failure")
            return resp_ok

        with patch.object(client.session, "get", side_effect=side_effect):
            with patch("core.visual.stock_image_client.time.sleep"):
                result = client._request_with_retry("https://example.com", source_name="Test")
        assert result.status_code == 200

    def test_502_then_success(self, client: StockImageClient) -> None:
        """502 → 2回目で成功。"""
        resp_502 = _make_mock_response(502)
        resp_502.raise_for_status = MagicMock()
        resp_ok = _make_mock_response(200)

        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return resp_502
            return resp_ok

        with patch.object(client.session, "get", side_effect=side_effect):
            with patch("core.visual.stock_image_client.time.sleep"):
                result = client._request_with_retry("https://example.com", source_name="Test")
        assert result.status_code == 200


# ===========================================================================
# search_for_segments 追加パス (lines 174-239)
# ===========================================================================

class TestSearchForSegmentsExtended:
    """search_for_segments の追加パス。"""

    def test_pre_generated_queries(self, client: StockImageClient) -> None:
        """事前生成済みクエリ使用 (line 201)。"""
        segments = [
            {"section": "s1", "key_points": ["irrelevant"]},
            {"section": "s2"},
        ]
        queries = ["ocean waves", "mountain peaks"]

        img = StockImage(
            id="px_1", url="", download_url="https://example.com/1.jpg",
            width=1920, height=1080, photographer="P", source="pexels",
        )
        downloaded = StockImage(
            id="px_1", url="", download_url="https://example.com/1.jpg",
            width=1920, height=1080, photographer="P", source="pexels",
            local_path=Path("/fake/1.jpg"),
        )

        with patch.object(client, "search", return_value=[img]):
            with patch.object(client, "download", return_value=downloaded):
                results = client.search_for_segments(segments, queries=queries)
        assert len(results) == 2

    def test_empty_query_produces_empty_image(self, client: StockImageClient) -> None:
        """空クエリ → empty StockImage (lines 210-215)。"""
        segments = [{"section": "", "content": ""}]
        with patch.object(client, "_translate_queries_to_english", return_value=[""]):
            results = client.search_for_segments(segments)
        assert len(results) == 1
        assert results[0].id == "empty_0"
        assert results[0].source == "none"

    def test_duplicate_image_skipped(self, client: StockImageClient) -> None:
        """重複ID → スキップ (line 222)。"""
        segments = [
            {"key_points": ["query1"]},
            {"key_points": ["query2"]},
        ]
        # 両方同じIDの画像が返る
        dup_img = StockImage(
            id="same_id", url="", download_url="https://example.com/dup.jpg",
            width=1920, height=1080, photographer="P", source="pexels",
        )
        downloaded = StockImage(
            id="same_id", url="", download_url="https://example.com/dup.jpg",
            width=1920, height=1080, photographer="P", source="pexels",
            local_path=Path("/fake/dup.jpg"),
        )

        with patch.object(client, "_translate_queries_to_english",
                          return_value=["query1", "query2"]):
            with patch.object(client, "search", return_value=[dup_img]):
                with patch.object(client, "download", return_value=downloaded):
                    results = client.search_for_segments(segments)
        # 1件目は取得成功、2件目は重複スキップで empty に
        assert len(results) == 2
        assert results[0].id == "same_id"
        assert results[1].id == "empty_1"

    def test_download_failure_produces_empty(self, client: StockImageClient) -> None:
        """ダウンロード失敗 → empty StockImage (lines 232-234)。"""
        segments = [{"key_points": ["nature"]}]
        img = StockImage(
            id="dl_fail", url="", download_url="https://example.com/fail.jpg",
            width=1920, height=1080, photographer="P", source="pexels",
        )
        with patch.object(client, "_translate_queries_to_english",
                          return_value=["nature"]):
            with patch.object(client, "search", return_value=[img]):
                with patch.object(client, "download", return_value=None):
                    results = client.search_for_segments(segments)
        assert len(results) == 1
        assert results[0].id == "empty_0"

    def test_queries_length_mismatch_generates_new(self, client: StockImageClient) -> None:
        """queries長さ不一致 → クエリ再生成 (line 202-205)。"""
        segments = [
            {"key_points": ["seg1"]},
            {"key_points": ["seg2"]},
        ]
        queries = ["only_one"]  # 長さ不一致

        img = StockImage(
            id="px_m", url="", download_url="https://example.com/m.jpg",
            width=1920, height=1080, photographer="P", source="pexels",
        )
        downloaded = StockImage(
            id="px_m", url="", download_url="https://example.com/m.jpg",
            width=1920, height=1080, photographer="P", source="pexels",
            local_path=Path("/fake/m.jpg"),
        )

        with patch.object(client, "_translate_queries_to_english",
                          return_value=["seg1", "seg2"]) as mock_translate:
            with patch.object(client, "search", return_value=[img]):
                with patch.object(client, "download", return_value=downloaded):
                    results = client.search_for_segments(segments, queries=queries)
        # _translate_queries_to_english が呼ばれる (新規生成パス)
        mock_translate.assert_called_once()


# ===========================================================================
# _build_query_from_segment エッジケース (line 384)
# ===========================================================================

class TestBuildQueryEdgeCases:
    """_build_query_from_segment の長いkey_pointsケース。"""

    def test_long_key_points_truncated(self, client: StockImageClient) -> None:
        """key_points結合が80文字超 → 先頭のkey_point[:80] (line 384)。"""
        long_kp = "a" * 50
        segment = {
            "key_points": [long_kp, "b" * 50],
        }
        query = client._build_query_from_segment(segment)
        # "a"*50 + " " + "b"*50 = 101文字 > 80 → key_points[0][:80]
        assert query == long_kp[:80]
        assert len(query) <= 80

    def test_single_key_point_over_80(self, client: StockImageClient) -> None:
        """単一key_pointが80文字超 → 80文字で切り詰め。"""
        segment = {"key_points": ["x" * 100]}
        query = client._build_query_from_segment(segment)
        # len("x"*100) <= 80? → No. → key_points[0][:80]
        # 実際はlen("x"*100) = 100 > 80 なので切り詰め
        assert len(query) <= 80

    def test_text_fallback(self, client: StockImageClient) -> None:
        """content なし、text あり → text[:40]。"""
        segment = {"text": "This is alternative text content for search query generation."}
        query = client._build_query_from_segment(segment)
        assert len(query) <= 40


# ===========================================================================
# _translate_queries_to_english エッジケース (line 444-446)
# ===========================================================================

class TestTranslateEdgeCases:
    """翻訳エッジケース。"""

    def test_gemini_exception_returns_original(self, client: StockImageClient) -> None:
        """Gemini呼び出し例外 → 元のクエリを返す (lines 444-446)。"""
        queries = ["量子コンピュータ", "AI"]
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}, clear=False):
            with patch("google.genai.Client", side_effect=RuntimeError("API down")):
                result = client._translate_queries_to_english(queries)
        assert result == queries

    def test_gemini_empty_response(self, client: StockImageClient) -> None:
        """Geminiレスポンスが空 → 元のクエリを返す。"""
        queries = ["深層学習"]
        mock_response = MagicMock()
        mock_response.text = ""
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}, clear=False):
            with patch("google.genai.Client", return_value=mock_client):
                result = client._translate_queries_to_english(queries)
        # 空レスポンス → 翻訳行なし → 元のクエリが残る
        assert result[0] == "深層学習"

    def test_gemini_none_text(self, client: StockImageClient) -> None:
        """Gemini response.text が None → 空文字扱い。"""
        queries = ["機械学習"]
        mock_response = MagicMock()
        mock_response.text = None
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}, clear=False):
            with patch("google.genai.Client", return_value=mock_client):
                result = client._translate_queries_to_english(queries)
        assert result[0] == "機械学習"

    def test_all_empty_queries_skip_translation(self, client: StockImageClient) -> None:
        """全クエリが空 → 翻訳スキップ。"""
        queries = ["", "", ""]
        result = client._translate_queries_to_english(queries)
        assert result == queries

    def test_gemini_partial_response(self, client: StockImageClient) -> None:
        """Geminiが一部だけ翻訳を返す → 返された分だけ適用。"""
        queries = ["量子力学", "technology", "生物学", "chemistry"]
        # japanese_indices = [0, 2]
        mock_response = MagicMock()
        # 1行しか返さない
        mock_response.text = "1. quantum mechanics"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}, clear=False):
            with patch("google.genai.Client", return_value=mock_client):
                result = client._translate_queries_to_english(queries)
        assert result[0] == "quantum mechanics"
        assert result[1] == "technology"
        assert result[2] == "生物学"  # 未翻訳のまま
        assert result[3] == "chemistry"


# ===========================================================================
# _rate_limit
# ===========================================================================

class TestRateLimit:
    """レート制限の動作確認。"""

    def test_rate_limit_throttles(self, client: StockImageClient) -> None:
        """連続呼び出しでsleepが発生する。"""
        client._last_request_time = time.monotonic()  # 今呼んだことにする
        client._min_interval = 1.0

        with patch("core.visual.stock_image_client.time.sleep") as mock_sleep:
            with patch("core.visual.stock_image_client.time.monotonic",
                       side_effect=[client._last_request_time + 0.1, client._last_request_time + 1.1]):
                client._rate_limit()
        # 0.1秒しか経っていない → 0.9秒sleepされる
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 0.8 <= sleep_time <= 1.0
