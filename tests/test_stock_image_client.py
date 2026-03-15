"""StockImageClient テスト (SP-033 Phase 2)"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.visual.stock_image_client import StockImage, StockImageClient


@pytest.fixture
def client(tmp_path: Path) -> StockImageClient:
    """APIキーなしのクライアント (モック用)。"""
    return StockImageClient(
        pexels_api_key="test_pexels_key",
        pixabay_api_key="test_pixabay_key",
        cache_dir=tmp_path / "stock_cache",
    )


@pytest.fixture
def client_no_keys(tmp_path: Path) -> StockImageClient:
    """APIキーなしのクライアント。"""
    return StockImageClient(
        pexels_api_key="",
        pixabay_api_key="",
        cache_dir=tmp_path / "stock_cache",
    )


class TestStockImageClient:
    """基本動作テスト。"""

    def test_no_api_keys_returns_empty(self, client_no_keys: StockImageClient) -> None:
        """APIキーなし → 空リスト"""
        result = client_no_keys.search("technology")
        assert result == []

    def test_cache_dir_created(self, client: StockImageClient) -> None:
        """キャッシュディレクトリが自動作成される"""
        assert client.cache_dir.exists()

    def test_build_query_from_segment_key_points(self, client: StockImageClient) -> None:
        """key_points からクエリ生成"""
        segment = {
            "section": "AI技術",
            "content": "長いコンテンツ",
            "key_points": ["機械学習", "ディープラーニング", "ニューラルネット"],
        }
        query = client._build_query_from_segment(segment)
        assert query == "機械学習 ディープラーニング"

    def test_build_query_from_segment_section_fallback(self, client: StockImageClient) -> None:
        """key_points なし → section にフォールバック"""
        segment = {"section": "産業応用", "content": "何かの内容"}
        query = client._build_query_from_segment(segment)
        assert query == "産業応用"

    def test_build_query_from_segment_content_fallback(self, client: StockImageClient) -> None:
        """key_points も section もなし → content の先頭40文字"""
        segment = {"content": "これは40文字以上のコンテンツでクエリに使用される想定です。実際にはもっと長い文章。"}
        query = client._build_query_from_segment(segment)
        assert len(query) <= 40

    def test_build_query_empty_segment(self, client: StockImageClient) -> None:
        """空セグメント → 空文字列"""
        assert client._build_query_from_segment({}) == ""


class TestPexelsSearch:
    """Pexels API検索テスト (モック)。"""

    def test_pexels_search_success(self, client: StockImageClient) -> None:
        """正常レスポンスからStockImageリストを生成"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "photos": [
                {
                    "id": 12345,
                    "width": 1920,
                    "height": 1080,
                    "url": "https://pexels.com/photo/12345",
                    "photographer": "Test User",
                    "alt": "Test photo",
                    "src": {
                        "original": "https://images.pexels.com/original.jpg",
                        "large2x": "https://images.pexels.com/large2x.jpg",
                        "large": "https://images.pexels.com/large.jpg",
                    },
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.session, "get", return_value=mock_response):
            results = client._search_pexels("technology", 5, "landscape", 1920)

        assert len(results) == 1
        assert results[0].id == "pexels_12345"
        assert results[0].source == "pexels"
        assert results[0].photographer == "Test User"

    def test_pexels_filters_small_images(self, client: StockImageClient) -> None:
        """min_width 未満の画像をフィルタ"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "photos": [
                {
                    "id": 1, "width": 800, "height": 600,
                    "url": "", "photographer": "", "alt": "",
                    "src": {"original": "https://example.com/small.jpg"},
                },
                {
                    "id": 2, "width": 1920, "height": 1080,
                    "url": "", "photographer": "", "alt": "",
                    "src": {"original": "https://example.com/large.jpg"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.session, "get", return_value=mock_response):
            results = client._search_pexels("test", 5, "landscape", 1920)

        assert len(results) == 1
        assert results[0].id == "pexels_2"


class TestPixabaySearch:
    """Pixabay API検索テスト (モック)。"""

    def test_pixabay_search_success(self, client: StockImageClient) -> None:
        """正常レスポンスからStockImageリストを生成"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "hits": [
                {
                    "id": 67890,
                    "pageURL": "https://pixabay.com/photos/67890",
                    "largeImageURL": "https://cdn.pixabay.com/large.jpg",
                    "imageWidth": 1920,
                    "imageHeight": 1080,
                    "user": "PixUser",
                    "tags": "technology, computer, science",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.session, "get", return_value=mock_response):
            results = client._search_pixabay("technology", 5, "landscape", 1920)

        assert len(results) == 1
        assert results[0].id == "pixabay_67890"
        assert results[0].source == "pixabay"
        assert results[0].tags == ["technology", "computer", "science"]


class TestDownloadAndCache:
    """ダウンロードとキャッシュのテスト。"""

    def test_download_creates_cached_file(self, client: StockImageClient, tmp_path: Path) -> None:
        """ダウンロード → キャッシュファイル作成"""
        image = StockImage(
            id="test_1", url="", download_url="https://example.com/image.jpg",
            width=1920, height=1080, photographer="Test", source="pexels",
        )
        mock_response = MagicMock()
        mock_response.content = b"\xff\xd8\xff\xe0fake_jpg_data"
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.download(image)

        assert result is not None
        assert result.local_path is not None
        assert result.local_path.exists()

    def test_download_cache_hit(self, client: StockImageClient) -> None:
        """キャッシュ済み → リクエストなし"""
        import hashlib
        url = "https://example.com/cached.jpg"
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_path = client.cache_dir / f"pexels_{cache_key}.jpg"
        cache_path.write_bytes(b"cached_data")

        image = StockImage(
            id="cached_1", url="", download_url=url,
            width=1920, height=1080, photographer="Test", source="pexels",
        )
        result = client.download(image)

        assert result is not None
        assert result.local_path == cache_path

    def test_download_empty_url_returns_none(self, client: StockImageClient) -> None:
        """空URL → None"""
        image = StockImage(
            id="empty", url="", download_url="",
            width=0, height=0, photographer="", source="none",
        )
        assert client.download(image) is None


class TestAttribution:
    """クレジット表記テスト。"""

    def test_attribution_generation(self, client: StockImageClient) -> None:
        """複数画像のクレジット表記"""
        images = [
            StockImage(id="1", url="", download_url="", width=0, height=0,
                       photographer="Alice", source="pexels"),
            StockImage(id="2", url="", download_url="", width=0, height=0,
                       photographer="Bob", source="pixabay"),
            StockImage(id="3", url="", download_url="", width=0, height=0,
                       photographer="Alice", source="pexels"),  # 重複
        ]
        attr = client.get_attribution(images)
        assert "Alice" in attr
        assert "Bob" in attr
        assert attr.count("Alice") == 1  # 重複除去

    def test_attribution_empty(self, client: StockImageClient) -> None:
        """source=none → 空文字"""
        images = [
            StockImage(id="e", url="", download_url="", width=0, height=0,
                       photographer="", source="none"),
        ]
        assert client.get_attribution(images) == ""


class TestSearchForSegments:
    """セグメント一括検索テスト。"""

    def test_search_for_segments_basic(self, client: StockImageClient) -> None:
        """セグメントごとに画像を収集"""
        segments = [
            {"section": "intro", "key_points": ["AI technology"], "content": "intro content"},
            {"section": "body", "key_points": ["machine learning"], "content": "body content"},
        ]

        call_count = 0

        def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            if "pexels.com/v1" in url:
                resp.json.return_value = {
                    "photos": [
                        {
                            "id": call_count * 100, "width": 1920, "height": 1080,
                            "url": "", "photographer": f"P{call_count}", "alt": "",
                            "src": {"large2x": f"https://images.pexels.com/{call_count}.jpg"},
                        },
                    ]
                }
            else:
                # ダウンロードリクエスト → 実バイト列を返す
                resp.content = b"\xff\xd8\xff\xe0fake_jpg"
            return resp

        with patch.object(client.session, "get", side_effect=mock_get):
            results = client.search_for_segments(segments)

        assert len(results) == 2
        for img in results:
            assert img.local_path is not None
            assert img.local_path.exists()


class TestGeminiJsonExtraction:
    """Gemini レスポンスJSON抽出テスト。"""

    def test_extract_json_from_markdown_block(self) -> None:
        """```json ... ``` パターンからJSON抽出"""
        from notebook_lm.gemini_integration import GeminiIntegration

        text = '```json\n{"title": "test", "segments": []}\n```'
        result = GeminiIntegration._extract_json_from_response(text)
        parsed = json.loads(result)
        assert parsed["title"] == "test"

    def test_extract_plain_json(self) -> None:
        """プレーンJSONをそのまま返す"""
        from notebook_lm.gemini_integration import GeminiIntegration

        text = '{"title": "plain"}'
        result = GeminiIntegration._extract_json_from_response(text)
        parsed = json.loads(result)
        assert parsed["title"] == "plain"

    def test_extract_json_with_surrounding_text(self) -> None:
        """前後にテキストがある場合"""
        from notebook_lm.gemini_integration import GeminiIntegration

        text = 'Here is the result:\n```json\n{"title": "surrounded"}\n```\nDone.'
        result = GeminiIntegration._extract_json_from_response(text)
        parsed = json.loads(result)
        assert parsed["title"] == "surrounded"
