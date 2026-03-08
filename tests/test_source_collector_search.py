import pytest
from unittest.mock import MagicMock, patch
from notebook_lm.source_collector import SourceCollector, SourceInfo

@pytest.mark.asyncio
async def test_search_sources_with_api_key():
    collector = SourceCollector()

    # Mock settings to have API keys
    with patch("notebook_lm.source_collector.settings") as mock_settings:
        mock_settings.RESEARCH_SETTINGS = {
            "google_search_api_key": "fake_key",
            "google_search_cx": "fake_cx"
        }

        # Mock session.get
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {"link": "https://test.com/1"},
                {"link": "https://test.com/2"}
            ]
        }

        with patch.object(collector.session, "get", return_value=mock_response):
            # Mock _process_url to avoid actual web requests
            async def mock_process_url(url, topic):
                return SourceInfo(url=url, title=f"Title for {url}", content_preview="", relevance_score=1.0, reliability_score=1.0, source_type="article")

            with patch.object(collector, "_process_url", side_effect=mock_process_url):
                sources = await collector._search_sources("test topic", 2)

                assert len(sources) == 2
                assert sources[0].url == "https://test.com/1"
                assert sources[1].url == "https://test.com/2"

@pytest.mark.asyncio
async def test_search_sources_fallback_to_simulation():
    collector = SourceCollector()

    # Mock settings to NOT have API keys
    with patch("notebook_lm.source_collector.settings") as mock_settings:
        mock_settings.RESEARCH_SETTINGS = {
            "google_search_api_key": "",
            "google_search_cx": ""
        }

        sources = await collector._search_sources("test topic", 3)
        assert len(sources) == 3
        assert "simulated" in sources[0].url
