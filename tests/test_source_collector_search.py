"""Tests for SourceCollector search methods (Brave Search API)."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from notebook_lm.source_collector import SourceCollector, SourceInfo


@pytest.mark.asyncio
async def test_brave_search_with_api_key():
    """Brave Search API が設定されている場合、Brave 経由でソース取得する。"""
    collector = SourceCollector()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "web": {
            "results": [
                {"url": "https://test.com/1", "title": "Result 1", "description": "Desc 1"},
                {"url": "https://test.com/2", "title": "Result 2", "description": "Desc 2"},
            ]
        }
    }

    async def mock_process_url(url, topic):
        return SourceInfo(
            url=url, title=f"Title for {url}", content_preview="",
            relevance_score=1.0, reliability_score=1.0, source_type="article",
        )

    with patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "fake_brave_key"}):
        with patch.object(collector.session, "get", return_value=mock_response) as mock_get:
            with patch.object(collector, "_process_url", side_effect=mock_process_url):
                sources = await collector._search_sources("test topic", 2)

            # Verify Brave API was called with correct headers
            call_args = mock_get.call_args
            assert call_args[1]["headers"]["X-Subscription-Token"] == "fake_brave_key"
            assert "api.search.brave.com" in call_args[0][0]

    assert len(sources) == 2
    assert sources[0].url == "https://test.com/1"
    assert sources[1].url == "https://test.com/2"


@pytest.mark.asyncio
async def test_search_sources_fallback_to_simulation():
    """Brave 未設定時、シミュレーションにフォールバック。"""
    collector = SourceCollector()

    with patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": ""}, clear=False):
        sources = await collector._search_sources("test topic", 3)

    assert len(sources) == 3
    assert "simulated" in sources[0].url


@pytest.mark.asyncio
async def test_brave_search_error_falls_back_to_simulation():
    """Brave API がエラーを返した場合、シミュレーションにフォールバック。"""
    collector = SourceCollector()

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("429 Too Many Requests")

    with patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "fake_key"}):
        with patch.object(collector.session, "get", return_value=mock_response):
            sources = await collector._search_sources("test topic", 3)

    assert len(sources) == 3
    assert "simulated" in sources[0].url
