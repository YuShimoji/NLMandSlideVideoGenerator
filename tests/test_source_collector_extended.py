"""Extended tests for source_collector.py — targeting uncovered lines."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import requests
from bs4 import BeautifulSoup

from notebook_lm.source_collector import SourceCollector, SourceInfo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def collector():
    """Create a SourceCollector with mocked settings."""
    with patch("notebook_lm.source_collector.settings") as mock_settings:
        mock_settings.NOTEBOOK_LM_SETTINGS = {"max_sources": 5}
        mock_settings.RESEARCH_SETTINGS = {
            "google_search_api_key": "",
            "google_search_cx": "",
        }
        yield SourceCollector()


def _make_response(content: bytes, encoding: str = "utf-8", apparent_encoding: str = "utf-8",
                   status_code: int = 200) -> MagicMock:
    """Build a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.content = content
    resp.text = content.decode(encoding, errors="ignore")
    resp.encoding = encoding
    resp.apparent_encoding = apparent_encoding
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# 1. collect_sources() with seed URLs (lines 51-55)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_sources_with_seed_urls(collector):
    """Seed URLs are processed before auto-search; results are sorted by combined score."""
    html = b"<html><head><title>Seed Page</title></head><body><p>Topic content here.</p></body></html>"
    resp = _make_response(html)

    with patch.object(collector.session, "get", return_value=resp):
        # Suppress _search_sources so it returns nothing extra
        with patch.object(collector, "_search_sources", return_value=[]):
            sources = await collector.collect_sources(
                "topic",
                urls=["https://example.com/seed1", "https://example.com/seed2"],
            )

    assert len(sources) == 2
    assert all(isinstance(s, SourceInfo) for s in sources)


@pytest.mark.asyncio
async def test_collect_sources_seed_failure_skipped(collector):
    """When a seed URL fails, it is skipped without breaking the collection."""
    # First call raises, second call succeeds
    good_html = b"<html><head><title>Good</title></head><body></body></html>"
    good_resp = _make_response(good_html)

    def side_effect(url, timeout=10):
        if "bad" in url:
            raise requests.exceptions.ConnectionError("refused")
        return good_resp

    with patch.object(collector.session, "get", side_effect=side_effect):
        with patch.object(collector, "_search_sources", return_value=[]):
            sources = await collector.collect_sources(
                "topic",
                urls=["https://bad.example.com", "https://good.example.com/page"],
            )

    assert len(sources) == 1


# ---------------------------------------------------------------------------
# 2. _process_url() success and exception paths (lines 69-101)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_url_success(collector):
    """Successful fetch returns a populated SourceInfo."""
    html = b"""<html><head>
        <title>Test Article</title>
        <meta name="description" content="A detailed article about testing." />
    </head><body><article><p>Testing is important for quality software.</p></article></body></html>"""
    resp = _make_response(html)

    with patch.object(collector.session, "get", return_value=resp):
        source = await collector._process_url("https://example.com/test", "testing")

    assert source is not None
    assert source.title == "Test Article"
    assert source.url == "https://example.com/test"
    assert source.source_type == "article"
    assert 0.0 <= source.relevance_score <= 1.0
    assert 0.0 <= source.reliability_score <= 1.0


@pytest.mark.asyncio
async def test_process_url_request_exception(collector):
    """RequestException returns None (line 93-95)."""
    with patch.object(collector.session, "get", side_effect=requests.exceptions.Timeout("timeout")):
        result = await collector._process_url("https://example.com/slow", "topic")
    assert result is None


@pytest.mark.asyncio
async def test_process_url_os_error(collector):
    """OSError returns None (line 96-98)."""
    with patch.object(collector.session, "get", side_effect=OSError("network down")):
        result = await collector._process_url("https://example.com/err", "topic")
    assert result is None


@pytest.mark.asyncio
async def test_process_url_generic_exception(collector):
    """Unexpected exception returns None (line 99-101)."""
    with patch.object(collector.session, "get", side_effect=RuntimeError("unexpected")):
        result = await collector._process_url("https://example.com/err", "topic")
    assert result is None


# ---------------------------------------------------------------------------
# 3. _search_sources() API path + exception fallback (lines 132, 139-141)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_sources_api_skips_items_without_link():
    """Items without 'link' key are skipped (line 132)."""
    with patch("notebook_lm.source_collector.settings") as mock_settings:
        mock_settings.NOTEBOOK_LM_SETTINGS = {"max_sources": 5}
        mock_settings.RESEARCH_SETTINGS = {
            "google_search_api_key": "key",
            "google_search_cx": "cx",
        }
        collector = SourceCollector()

    api_resp = MagicMock()
    api_resp.raise_for_status = MagicMock()
    api_resp.json.return_value = {
        "items": [
            {"link": "https://example.com/valid"},
            {"title": "No link here"},  # no "link" key
        ]
    }

    async def mock_process(url, topic):
        return SourceInfo(url=url, title="T", content_preview="C",
                          relevance_score=0.8, reliability_score=0.8, source_type="article")

    with patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": ""}, clear=False):
        with patch("notebook_lm.source_collector.settings") as mock_settings:
            mock_settings.RESEARCH_SETTINGS = {
                "google_search_api_key": "key",
                "google_search_cx": "cx",
            }
            with patch.object(collector.session, "get", return_value=api_resp):
                with patch.object(collector, "_process_url", side_effect=mock_process):
                    sources = await collector._search_sources("topic", 5)

    assert len(sources) == 1
    assert sources[0].url == "https://example.com/valid"


@pytest.mark.asyncio
async def test_search_sources_api_exception_falls_back():
    """API exception falls back to simulation (lines 139-141)."""
    with patch("notebook_lm.source_collector.settings") as mock_settings:
        mock_settings.NOTEBOOK_LM_SETTINGS = {"max_sources": 5}
        mock_settings.RESEARCH_SETTINGS = {
            "google_search_api_key": "key",
            "google_search_cx": "cx",
        }
        collector = SourceCollector()

    with patch("notebook_lm.source_collector.settings") as mock_settings:
        mock_settings.RESEARCH_SETTINGS = {
            "google_search_api_key": "key",
            "google_search_cx": "cx",
        }
        with patch.object(collector.session, "get", side_effect=Exception("API down")):
            sources = await collector._search_sources("topic", 2)

    assert len(sources) == 2
    assert "simulated" in sources[0].url


# ---------------------------------------------------------------------------
# 4. _decode_response() fallback paths (lines 163-177)
# ---------------------------------------------------------------------------

def test_decode_response_returns_text_when_html_present(collector):
    """Early return when response.text already contains '<html' (line 164-165)."""
    resp = _make_response(b"<html><body>Hello</body></html>")
    result = collector._decode_response(resp)
    assert "<html>" in result


def test_decode_response_returns_text_when_doctype_present(collector):
    """Early return for '<!doctype' in response.text (line 164-165)."""
    resp = _make_response(b"<!DOCTYPE html><html><body>Hi</body></html>")
    result = collector._decode_response(resp)
    assert "<!DOCTYPE html>" in result


def test_decode_response_fallback_encoding_loop(collector):
    """When response.text lacks HTML markers, try encoding fallbacks (lines 167-175)."""
    # response.text is garbled (no html marker), but content can be decoded
    resp = MagicMock(spec=requests.Response)
    resp.text = "garbled no html markers"
    resp.encoding = None  # first candidate is None, should be skipped
    resp.apparent_encoding = "utf-8"
    resp.content = b"<html><body>Decoded via apparent encoding</body></html>"
    result = collector._decode_response(resp)
    assert "<html>" in result


def test_decode_response_returns_original_text_as_last_resort(collector):
    """When no encoding produces HTML markers, return original text (line 177)."""
    resp = MagicMock(spec=requests.Response)
    resp.text = "plain text with no markers at all"
    resp.encoding = "utf-8"
    resp.apparent_encoding = "utf-8"
    resp.content = b"plain text with no markers at all"
    result = collector._decode_response(resp)
    assert result == "plain text with no markers at all"


def test_decode_response_skips_lookup_error(collector):
    """LookupError during decode is caught and skipped (line 174)."""
    resp = MagicMock(spec=requests.Response)
    resp.text = "no html markers"
    resp.encoding = "bogus-codec-999"
    resp.apparent_encoding = "another-bogus"
    # Make content.decode raise LookupError
    content_mock = MagicMock()
    content_mock.decode = MagicMock(side_effect=LookupError("unknown encoding"))
    resp.content = content_mock
    result = collector._decode_response(resp)
    assert result == "no html markers"


# ---------------------------------------------------------------------------
# 5. _extract_title() with various tag types (lines 181-203)
# ---------------------------------------------------------------------------

def test_extract_title_og_title(collector):
    """og:title meta tag is first priority (line 182)."""
    html = '<html><head><meta property="og:title" content="OG Title" /><title>Fallback</title></head></html>'
    soup = BeautifulSoup(html, "html.parser")
    assert collector._extract_title(soup, "https://example.com") == "OG Title"


def test_extract_title_twitter_title(collector):
    """twitter:title meta tag is second priority (line 183)."""
    html = '<html><head><meta name="twitter:title" content="Twitter Title" /></head></html>'
    soup = BeautifulSoup(html, "html.parser")
    assert collector._extract_title(soup, "https://example.com") == "Twitter Title"


def test_extract_title_from_title_tag(collector):
    """<title> tag is third priority (line 184)."""
    html = "<html><head><title>Page Title</title></head></html>"
    soup = BeautifulSoup(html, "html.parser")
    assert collector._extract_title(soup, "https://example.com") == "Page Title"


def test_extract_title_from_h1(collector):
    """<h1> tag is fourth priority (line 185)."""
    html = "<html><body><h1>Heading One</h1></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    assert collector._extract_title(soup, "https://example.com") == "Heading One"


def test_extract_title_url_fallback(collector):
    """Falls back to URL slug when no HTML title found (line 202)."""
    html = "<html><body><p>No title tags here.</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    assert collector._extract_title(soup, "https://example.com/my-article") == "my article"


def test_extract_title_unavailable(collector):
    """Returns 'Title unavailable' when URL also yields nothing (line 203)."""
    html = "<html><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    assert collector._extract_title(soup, "https://example.com/") == "Title unavailable"


def test_extract_title_skips_empty_content(collector):
    """Tags with empty content are skipped (line 197-200)."""
    html = '<html><head><meta property="og:title" content="  " /><title>Real Title</title></head></html>'
    soup = BeautifulSoup(html, "html.parser")
    assert collector._extract_title(soup, "https://example.com") == "Real Title"


# ---------------------------------------------------------------------------
# 6. _extract_content_preview() (lines 207-238)
# ---------------------------------------------------------------------------

def test_extract_content_preview_from_description_meta(collector):
    """description meta tag is first choice (line 208)."""
    html = '<html><head><meta name="description" content="Short description." /></head></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = collector._extract_content_preview(soup, "https://example.com", "Title")
    assert result == "Short description."


def test_extract_content_preview_from_og_description(collector):
    """og:description is second choice (line 209)."""
    html = '<html><head><meta property="og:description" content="OG description." /></head></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = collector._extract_content_preview(soup, "https://example.com", "Title")
    assert result == "OG description."


def test_extract_content_preview_from_twitter_description(collector):
    """twitter:description is third choice (line 210)."""
    html = '<html><head><meta name="twitter:description" content="Twitter desc." /></head></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = collector._extract_content_preview(soup, "https://example.com", "Title")
    assert result == "Twitter desc."


def test_extract_content_preview_truncates_long_description(collector):
    """Descriptions over 500 chars are truncated (line 221)."""
    long_text = "A" * 600
    html = f'<html><head><meta name="description" content="{long_text}" /></head></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = collector._extract_content_preview(soup, "https://example.com", "Title")
    assert result.endswith("...")
    assert len(result) == 503  # 500 + "..."


def test_extract_content_preview_from_content_class_tags(collector):
    """Falls back to tags with content/article/text/body classes (lines 223-231)."""
    html = """<html><body>
        <div class="article-content">First block of text.</div>
        <p class="text-body">Second block.</p>
    </body></html>"""
    soup = BeautifulSoup(html, "html.parser")
    result = collector._extract_content_preview(soup, "https://example.com/no-slug", "Title unavailable")
    assert "First block" in result or "Second block" in result


def test_extract_content_preview_url_fallback(collector):
    """Falls back to URL slug when no meta or content (line 233-235)."""
    html = "<html><body><p>Random text.</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    result = collector._extract_content_preview(soup, "https://example.com/article-slug", "Title unavailable")
    assert "article slug" in result


def test_extract_content_preview_title_fallback(collector):
    """Falls back to title when URL gives nothing (line 236-237)."""
    html = "<html><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    result = collector._extract_content_preview(soup, "https://example.com/", "My Custom Title")
    assert "My Custom Title" in result


def test_extract_content_preview_unavailable(collector):
    """Returns 'Preview unavailable' as last resort (line 238)."""
    html = "<html><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    result = collector._extract_content_preview(soup, "https://example.com/", "Title unavailable")
    assert result == "Preview unavailable"


def test_extract_content_preview_skips_empty_meta_content(collector):
    """Meta tags with empty content are skipped (lines 216-217)."""
    html = '<html><head><meta name="description" content="  " /><meta property="og:description" content="Real OG." /></head></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = collector._extract_content_preview(soup, "https://example.com", "Title")
    # The first meta has whitespace-only, should skip to og:description
    # Actually, "  ".strip() == "" so it skips. The second should be used.
    assert result == "Real OG."


# ---------------------------------------------------------------------------
# 7. _fallback_title_from_url() edge cases (lines 242-249)
# ---------------------------------------------------------------------------

def test_fallback_title_from_url_normal(collector):
    """Normal URL path is converted to a title (line 244-247)."""
    assert collector._fallback_title_from_url("https://example.com/my-article") == "my article"


def test_fallback_title_from_url_underscores(collector):
    """Underscores are converted to spaces."""
    assert collector._fallback_title_from_url("https://example.com/my_article") == "my article"


def test_fallback_title_from_url_empty_path(collector):
    """Root path returns empty string (line 245-246)."""
    assert collector._fallback_title_from_url("https://example.com/") == ""
    assert collector._fallback_title_from_url("https://example.com") == ""


def test_fallback_title_from_url_long_slug(collector):
    """Long slugs are truncated to 120 chars (line 247)."""
    long_slug = "a" * 200
    result = collector._fallback_title_from_url(f"https://example.com/{long_slug}")
    assert len(result) <= 120


def test_fallback_title_from_url_exception(collector):
    """Exceptions return empty string (line 248-249)."""
    # Pass something that would cause urlparse to behave oddly; patch to raise
    with patch("notebook_lm.source_collector.urlparse", side_effect=ValueError("bad")):
        assert collector._fallback_title_from_url("not-a-url") == ""


# ---------------------------------------------------------------------------
# 8. _extract_key_claims() and _extract_article_chunks() (lines 274, 278, 283-284, 309, 312, 316)
# ---------------------------------------------------------------------------

def test_extract_key_claims_deduplication(collector):
    """Duplicate claims are deduplicated via normalize key (line 273-274)."""
    html = """<html><body><article>
        <p>Climate change is a serious global issue that affects everyone around the world today.</p>
        <p>Climate change is a serious global issue that affects everyone around the world today.</p>
        <p>Rising sea levels threaten coastal cities and island nations in the coming decades.</p>
    </article></body></html>"""
    soup = BeautifulSoup(html, "html.parser")
    claims = collector._extract_key_claims(
        "Climate change",
        "Climate change overview.",
        soup,
        "climate change effects",
    )
    # Duplicates should be merged; the exact same text should appear only once
    seen = set()
    for c in claims:
        key = collector._normalize_claim_key(c)
        assert key not in seen, f"Duplicate claim key: {key}"
        seen.add(key)


def test_extract_key_claims_max_six(collector):
    """At most 6 unique claims are returned (line 277-278)."""
    paragraphs = "\n".join(
        f"<p>Unique claim number {i} about the research topic at hand is very important.</p>"
        for i in range(20)
    )
    html = f"<html><body><article>{paragraphs}</article></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    claims = collector._extract_key_claims("research", "research overview", soup, "research topic")
    assert len(claims) <= 6


def test_extract_key_claims_fallback_to_title(collector):
    """When no article text, falls back to title (lines 283-284)."""
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")
    claims = collector._extract_key_claims(
        "A significant discovery in modern astrophysics research",
        "",
        soup,
        "astrophysics",
    )
    assert len(claims) >= 1
    assert "astrophysics" in claims[0].lower()


def test_extract_key_claims_fallback_to_content_preview(collector):
    """Falls back to content_preview when title also produces nothing (lines 283-284)."""
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")
    claims = collector._extract_key_claims(
        "short",  # too short to pass _clean_claim
        "This is a longer content preview about quantum computing research advances.",
        soup,
        "quantum computing",
    )
    assert len(claims) >= 1


def test_extract_article_chunks_from_article_p(collector):
    """Extracts from <article><p> selector (lines 286-318)."""
    html = """<html><body><article>
        <p>This is a paragraph with enough text to be over sixty characters long, used for testing purposes.</p>
        <p>Short.</p>
    </article></body></html>"""
    soup = BeautifulSoup(html, "html.parser")
    chunks = collector._extract_article_chunks(soup)
    assert len(chunks) == 1  # short paragraph is skipped (< 60 chars)


def test_extract_article_chunks_fallback_to_all_p(collector):
    """Falls back to all <p> tags when article selectors miss (line 303-304)."""
    html = """<html><body>
        <p>A standalone paragraph that is definitely longer than sixty characters for the test to work properly.</p>
    </body></html>"""
    soup = BeautifulSoup(html, "html.parser")
    chunks = collector._extract_article_chunks(soup)
    assert len(chunks) == 1


def test_extract_article_chunks_dedup(collector):
    """Duplicate paragraphs are deduplicated (line 311-312)."""
    html = """<html><body><article>
        <p>This same text is repeated in multiple places to test deduplication of article chunks.</p>
        <p>This same text is repeated in multiple places to test deduplication of article chunks.</p>
    </article></body></html>"""
    soup = BeautifulSoup(html, "html.parser")
    chunks = collector._extract_article_chunks(soup)
    assert len(chunks) == 1


def test_extract_article_chunks_max_six(collector):
    """At most 6 chunks are returned (line 315-316)."""
    paragraphs = "\n".join(
        f"<p>Paragraph number {i} with more than sixty characters of text to ensure it passes the length filter.</p>"
        for i in range(20)
    )
    html = f"<html><body><article>{paragraphs}</article></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    chunks = collector._extract_article_chunks(soup)
    assert len(chunks) <= 6


def test_extract_article_chunks_skips_short(collector):
    """Paragraphs under 60 chars are skipped (line 308-309)."""
    html = "<html><body><p>Too short.</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    chunks = collector._extract_article_chunks(soup)
    assert len(chunks) == 0


# ---------------------------------------------------------------------------
# 9. _clean_claim() edge cases (lines 323, 330, 334, 347, 349)
# ---------------------------------------------------------------------------

def test_clean_claim_empty_string(collector):
    """Empty string returns empty (line 329-330)."""
    assert collector._clean_claim("") == ""
    assert collector._clean_claim(None) == ""


def test_clean_claim_whitespace_only(collector):
    """Whitespace-only returns empty (line 333-334)."""
    assert collector._clean_claim("   ") == ""
    assert collector._clean_claim('"  "') == ""


def test_clean_claim_noisy_prefix_preview_unavailable(collector):
    """'preview unavailable' prefix is rejected (line 344-345)."""
    assert collector._clean_claim("Preview unavailable from direct scrape. Something.") == ""


def test_clean_claim_noisy_prefix_read_more(collector):
    """'read more' prefix is rejected."""
    assert collector._clean_claim("Read more about this fascinating topic in our blog.") == ""


def test_clean_claim_noisy_prefix_derived_title(collector):
    """'derived title:' prefix is rejected."""
    assert collector._clean_claim("Derived title: some title text here for testing purposes.") == ""


def test_clean_claim_too_short(collector):
    """Claims under 20 characters are rejected (line 346-347)."""
    assert collector._clean_claim("Short claim.") == ""
    assert collector._clean_claim("Exactly 19 chars!!") == ""


def test_clean_claim_long_text_truncated(collector):
    """Claims over 260 characters are truncated (line 348-349)."""
    long_claim = "A" * 300
    result = collector._clean_claim(long_claim)
    assert result.endswith("...")
    assert len(result) == 260  # 257 + "..."


def test_clean_claim_strips_quotes_and_brackets(collector):
    """Surrounding quotes, brackets, braces are stripped (line 332)."""
    result = collector._clean_claim('"[This is a valid claim with enough characters for testing.]"')
    assert not result.startswith('"')
    assert not result.startswith("[")


def test_clean_claim_normalizes_nbsp(collector):
    """Non-breaking spaces are normalized (line 331)."""
    text = "This\xa0is\xa0a\xa0claim\xa0with\xa0non\xa0breaking\xa0spaces\xa0inside\xa0it."
    result = collector._clean_claim(text)
    assert "\xa0" not in result
    # "This is a claim with non breaking spaces inside it." is 52 chars, passes 20-char minimum
    assert "This is a claim" in result


# ---------------------------------------------------------------------------
# 10. _calculate_relevance() and _calculate_reliability() (lines 367-370, 374-402)
# ---------------------------------------------------------------------------

def test_calculate_relevance_full_match(collector):
    """All topic words present gives 1.0 (line 367-370)."""
    score = collector._calculate_relevance("AI testing tools", "AI testing tools review", "AI testing tools")
    assert score == 1.0


def test_calculate_relevance_partial_match(collector):
    """Partial overlap gives proportional score."""
    score = collector._calculate_relevance("AI", "something else", "AI testing tools")
    # only "AI" matches out of 3 words => 1/3
    assert 0.3 <= score <= 0.4


def test_calculate_relevance_no_match(collector):
    """No overlap gives 0.0."""
    score = collector._calculate_relevance("cats", "dogs", "quantum physics")
    assert score == 0.0


def test_calculate_relevance_empty_topic(collector):
    """Empty topic returns 0.0 (line 370)."""
    score = collector._calculate_relevance("anything", "something", "")
    assert score == 0.0


def test_calculate_reliability_trusted_domain(collector):
    """Trusted domains get +0.3 boost (line 395-396)."""
    html = "<html><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    score = collector._calculate_reliability("https://www.nikkei.com/article", soup)
    # base 0.5 + 0.3 (trusted) + 0.1 (https)
    assert score >= 0.9


def test_calculate_reliability_https_bonus(collector):
    """HTTPS adds +0.1 (line 397-398)."""
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")
    score_https = collector._calculate_reliability("https://unknown.com/page", soup)
    score_http = collector._calculate_reliability("http://unknown.com/page", soup)
    assert score_https > score_http


def test_calculate_reliability_article_tag_bonus(collector):
    """<article> tag adds +0.1 (line 399-400)."""
    soup_with = BeautifulSoup("<html><body><article><p>Text</p></article></body></html>", "html.parser")
    soup_without = BeautifulSoup("<html><body><p>Text</p></body></html>", "html.parser")
    score_with = collector._calculate_reliability("https://unknown.com/page", soup_with)
    score_without = collector._calculate_reliability("https://unknown.com/page", soup_without)
    assert score_with > score_without


def test_calculate_reliability_time_tag_bonus(collector):
    """<time> tag also triggers +0.1."""
    soup = BeautifulSoup("<html><body><time>2026-01-01</time></body></html>", "html.parser")
    score = collector._calculate_reliability("https://unknown.com/page", soup)
    # 0.5 + 0.1 (https) + 0.1 (time tag) = 0.7
    assert score >= 0.7


def test_calculate_reliability_capped_at_one(collector):
    """Score is capped at 1.0 (line 402)."""
    soup = BeautifulSoup("<html><body><article><time>2026</time></article></body></html>", "html.parser")
    score = collector._calculate_reliability("https://www.bbc.com/news", soup)
    assert score <= 1.0


def test_calculate_reliability_bad_url(collector):
    """Malformed URL handles IndexError gracefully (line 377)."""
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")
    score = collector._calculate_reliability("not-a-url", soup)
    # base 0.5, no bonuses
    assert score == 0.5


# ---------------------------------------------------------------------------
# 11. _determine_source_type() (lines 406-423)
# ---------------------------------------------------------------------------

def test_determine_source_type_news(collector):
    """News domains return 'news' (line 412-413)."""
    soup = BeautifulSoup("<html></html>", "html.parser")
    assert collector._determine_source_type("https://www.nikkei.com/article", soup) == "news"
    assert collector._determine_source_type("https://www.nhk.or.jp/news", soup) == "news"
    assert collector._determine_source_type("https://apnews.com/article", soup) == "news"


def test_determine_source_type_academic(collector):
    """Academic domains return 'academic' (line 416-417)."""
    soup = BeautifulSoup("<html></html>", "html.parser")
    assert collector._determine_source_type("https://www.mit.edu/research", soup) == "academic"
    assert collector._determine_source_type("https://www.u-tokyo.ac.jp/en", soup) == "academic"
    assert collector._determine_source_type("https://scholar.google.com/article", soup) == "academic"
    assert collector._determine_source_type("https://www.researchgate.net/pub", soup) == "academic"


def test_determine_source_type_blog(collector):
    """Blog domains return 'blog' (line 420-421)."""
    soup = BeautifulSoup("<html></html>", "html.parser")
    assert collector._determine_source_type("https://myblog.wordpress.com/post", soup) == "blog"
    assert collector._determine_source_type("https://medium.com/@author/post", soup) == "blog"
    assert collector._determine_source_type("https://note.com/user/n/12345", soup) == "blog"


def test_determine_source_type_article_default(collector):
    """Unknown domains default to 'article' (line 423)."""
    soup = BeautifulSoup("<html></html>", "html.parser")
    assert collector._determine_source_type("https://example.com/page", soup) == "article"


def test_determine_source_type_bad_url(collector):
    """Malformed URL returns 'article' (line 408-409)."""
    soup = BeautifulSoup("<html></html>", "html.parser")
    assert collector._determine_source_type("no-slashes", soup) == "article"


# ---------------------------------------------------------------------------
# 12. save_sources_info() (lines 427-433)
# ---------------------------------------------------------------------------

def test_save_sources_info_writes_json(collector, tmp_path):
    """Sources are persisted as JSON array (lines 427-433)."""
    sources = [
        SourceInfo(
            url="https://example.com/1",
            title="Source 1",
            content_preview="Preview 1",
            relevance_score=0.9,
            reliability_score=0.8,
            source_type="news",
            key_claims=["Claim A"],
        ),
        SourceInfo(
            url="https://example.com/2",
            title="Source 2",
            content_preview="Preview 2",
            relevance_score=0.7,
            reliability_score=0.6,
            source_type="blog",
            adoption_status="accepted",
            adoption_reason="High quality",
        ),
    ]

    output_path = tmp_path / "sources.json"
    collector.save_sources_info(sources, output_path)

    assert output_path.exists()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["url"] == "https://example.com/1"
    assert data[0]["title"] == "Source 1"
    assert data[0]["key_claims"] == ["Claim A"]
    assert data[1]["adoption_status"] == "accepted"
    assert data[1]["adoption_reason"] == "High quality"


def test_save_sources_info_empty_list(collector, tmp_path):
    """Empty source list writes an empty JSON array."""
    output_path = tmp_path / "empty.json"
    collector.save_sources_info([], output_path)

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data == []


# ---------------------------------------------------------------------------
# Additional edge-case coverage
# ---------------------------------------------------------------------------

def test_split_claim_candidates_empty(collector):
    """Empty text returns empty list (line 322-323)."""
    assert collector._split_claim_candidates("") == []
    assert collector._split_claim_candidates(None) == []


def test_split_claim_candidates_multiple_sentences(collector):
    """Sentences are split on punctuation boundaries."""
    text = "First sentence. Second sentence! Third? Done."
    parts = collector._split_claim_candidates(text)
    assert len(parts) >= 3


@pytest.mark.asyncio
async def test_collect_sources_sorting_and_limit(collector):
    """Results are sorted by combined score and limited to max_sources."""
    collector.max_sources = 2

    async def mock_process(url, topic):
        # Assign different scores based on URL
        idx = int(url.split("/")[-1])
        return SourceInfo(
            url=url, title=f"T{idx}", content_preview="C",
            relevance_score=idx * 0.1, reliability_score=idx * 0.1,
            source_type="article",
        )

    with patch.object(collector, "_process_url", side_effect=mock_process):
        with patch.object(collector, "_search_sources", return_value=[]):
            sources = await collector.collect_sources(
                "topic",
                urls=[f"https://example.com/{i}" for i in range(5)],
            )

    assert len(sources) == 2
    # Highest scored should come first
    assert sources[0].relevance_score >= sources[1].relevance_score
