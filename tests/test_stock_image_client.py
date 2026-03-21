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
    """APIキーなし+Wikimedia無効のクライアント。"""
    return StockImageClient(
        pexels_api_key="",
        pixabay_api_key="",
        cache_dir=tmp_path / "stock_cache",
        enable_wikimedia=False,
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


class TestWikimediaSearch:
    """Wikimedia Commons API検索テスト (モック)。"""

    def test_wikimedia_search_success(self, client: StockImageClient) -> None:
        """正常レスポンスからStockImageリストを生成"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": {
                "pages": {
                    "12345": {
                        "pageid": 12345,
                        "title": "File:Test_image.jpg",
                        "imageinfo": [
                            {
                                "url": "https://upload.wikimedia.org/commons/test.jpg",
                                "thumburl": "https://upload.wikimedia.org/commons/thumb/test.jpg",
                                "width": 2048,
                                "height": 1024,
                                "user": "WikiUser",
                                "extmetadata": {
                                    "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                    "ImageDescription": {"value": "A test image"},
                                },
                            }
                        ],
                    }
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.session, "get", return_value=mock_response):
            results = client._search_wikimedia("technology", 5)

        assert len(results) == 1
        assert results[0].id == "wikimedia_12345"
        assert results[0].source == "wikimedia"
        assert results[0].photographer == "WikiUser"
        assert "commons.wikimedia.org" in results[0].url

    def test_wikimedia_filters_small_images(self, client: StockImageClient) -> None:
        """min_width 未満の画像をフィルタ"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": {
                "pages": {
                    "1": {
                        "pageid": 1,
                        "title": "File:Small.jpg",
                        "imageinfo": [{"url": "https://example.com/small.jpg", "width": 800, "height": 600, "user": "U", "extmetadata": {"LicenseShortName": {"value": "CC0"}}}],
                    },
                    "2": {
                        "pageid": 2,
                        "title": "File:Large.jpg",
                        "imageinfo": [{"url": "https://example.com/large.jpg", "thumburl": "https://example.com/thumb.jpg", "width": 2048, "height": 1024, "user": "U", "extmetadata": {"LicenseShortName": {"value": "CC0"}}}],
                    },
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.session, "get", return_value=mock_response):
            results = client._search_wikimedia("test", 5)

        assert len(results) == 1
        assert results[0].id == "wikimedia_2"

    def test_wikimedia_filters_non_cc_licenses(self, client: StockImageClient) -> None:
        """CC/PD以外のライセンスをフィルタ"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": {
                "pages": {
                    "1": {
                        "pageid": 1,
                        "title": "File:NonFree.jpg",
                        "imageinfo": [{"url": "https://example.com/nonfree.jpg", "thumburl": "https://example.com/thumb.jpg", "width": 2048, "height": 1024, "user": "U", "extmetadata": {"LicenseShortName": {"value": "Fair use"}}}],
                    },
                    "2": {
                        "pageid": 2,
                        "title": "File:CC.jpg",
                        "imageinfo": [{"url": "https://example.com/cc.jpg", "thumburl": "https://example.com/thumb2.jpg", "width": 2048, "height": 1024, "user": "U", "extmetadata": {"LicenseShortName": {"value": "CC BY 4.0"}}}],
                    },
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.session, "get", return_value=mock_response):
            results = client._search_wikimedia("test", 5)

        assert len(results) == 1
        assert results[0].id == "wikimedia_2"

    def test_wikimedia_empty_result(self, client: StockImageClient) -> None:
        """空結果 → 空リスト"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"query": {"pages": {}}}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.session, "get", return_value=mock_response):
            results = client._search_wikimedia("nonexistent_query", 5)

        assert results == []

    def test_wikimedia_fallback_to_pexels(self, client: StockImageClient) -> None:
        """Wikimedia 0件 → Pexelsにフォールバック"""
        call_count = 0

        def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            if "commons.wikimedia.org" in url:
                resp.json.return_value = {"query": {"pages": {}}}
            elif "pexels.com" in url:
                resp.json.return_value = {
                    "photos": [{
                        "id": 99, "width": 1920, "height": 1080,
                        "url": "", "photographer": "Pexels User", "alt": "",
                        "src": {"large2x": "https://images.pexels.com/99.jpg"},
                    }]
                }
            return resp

        with patch.object(client.session, "get", side_effect=mock_get):
            results = client.search("technology", count=3)

        assert len(results) == 1
        assert results[0].source == "pexels"

    def test_wikimedia_attribution(self, client: StockImageClient) -> None:
        """Wikimedia画像のクレジット表記"""
        images = [
            StockImage(id="wm1", url="https://commons.wikimedia.org/wiki/File:Test.jpg",
                       download_url="", width=0, height=0,
                       photographer="WikiUser", source="wikimedia"),
        ]
        attr = client.get_attribution(images)
        assert "WikiUser" in attr
        assert "Wikimedia Commons" in attr


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


class TestQueryTranslation:
    """クエリ翻訳テスト。"""

    def test_english_queries_unchanged(self, client: StockImageClient) -> None:
        """英語のみのクエリは翻訳をスキップ"""
        queries = ["technology", "artificial intelligence", ""]
        result = client._translate_queries_to_english(queries)
        assert result == queries

    def test_japanese_detection(self) -> None:
        """日本語文字の検出"""
        from core.visual.stock_image_client import _JAPANESE_RE
        assert _JAPANESE_RE.search("量子コンピュータ")
        assert _JAPANESE_RE.search("テスト")
        assert _JAPANESE_RE.search("漢字")
        assert not _JAPANESE_RE.search("technology")
        assert not _JAPANESE_RE.search("AI 2024")

    def test_translate_fallback_on_no_api_key(self, tmp_path: Path) -> None:
        """Gemini APIキーなし → 元のクエリを返す"""
        client = StockImageClient(
            pexels_api_key="", pixabay_api_key="",
            cache_dir=tmp_path / "cache",
        )
        queries = ["量子コンピュータ", "technology"]
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            with patch("core.visual.stock_image_client.settings") as mock_settings:
                mock_settings.GEMINI_API_KEY = ""
                result = client._translate_queries_to_english(queries)
        assert result == queries

    def test_translate_with_mock_gemini(self, client: StockImageClient) -> None:
        """Gemini翻訳のモックテスト"""
        queries = ["量子コンピュータ", "technology", "深層学習"]

        mock_response = MagicMock()
        mock_response.text = "1. quantum computer\n2. deep learning"

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}, clear=False):
            with patch("google.genai.Client", return_value=mock_client_instance):
                result = client._translate_queries_to_english(queries)

        assert result[0] == "quantum computer"
        assert result[1] == "technology"  # 英語はそのまま
        assert result[2] == "deep learning"

    def test_mixed_japanese_english(self, client: StockImageClient) -> None:
        """日本語と英語混在のクエリリスト"""
        queries = ["AI revolution", "量子ビット", "cloud computing"]
        # 英語のみ (index 0, 2) は翻訳スキップ
        # 日本語 (index 1) のみ翻訳対象
        mock_response = MagicMock()
        mock_response.text = "1. quantum bit"

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}, clear=False):
            with patch("google.genai.Client", return_value=mock_client_instance):
                result = client._translate_queries_to_english(queries)

        assert result[0] == "AI revolution"
        assert result[1] == "quantum bit"
        assert result[2] == "cloud computing"
