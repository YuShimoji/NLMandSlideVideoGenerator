"""Source collection utilities for research workflow."""

import asyncio
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config.settings import settings
from core.utils.logger import logger


@dataclass
class SourceInfo:
    """Source metadata stored in ResearchPackage."""

    url: str
    title: str
    content_preview: str
    relevance_score: float
    reliability_score: float
    source_type: str
    adoption_status: str = "pending"
    adoption_reason: str = ""
    key_claims: List[str] = field(default_factory=list)


class SourceCollector:
    """Collect and score web sources."""

    def __init__(self) -> None:
        self.max_sources = settings.NOTEBOOK_LM_SETTINGS["max_sources"]
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            }
        )

    async def collect_sources(self, topic: str, urls: Optional[List[str]] = None) -> List[SourceInfo]:
        """Collect seed URLs first, then search for additional sources if needed."""
        logger.info(f"Source collection start: {topic}")
        sources: List[SourceInfo] = []

        if urls:
            logger.info(f"Processing seed URLs: {len(urls)}")
            for url in urls:
                source = await self._process_url(url, topic)
                if source:
                    sources.append(source)

        remaining_count = self.max_sources - len(sources)
        if remaining_count > 0:
            logger.info(f"Searching additional sources: {remaining_count}")
            auto_sources = await self._search_sources(topic, remaining_count)
            sources.extend(auto_sources)

        sources.sort(key=lambda item: (item.reliability_score + item.relevance_score) / 2, reverse=True)
        logger.info(f"Source collection complete: {len(sources)}")
        return sources[: self.max_sources]

    async def _process_url(self, url: str, topic: str) -> Optional[SourceInfo]:
        """Fetch and parse one URL into SourceInfo."""
        try:
            logger.debug(f"Processing URL: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            html = self._decode_response(response)
            soup = BeautifulSoup(html, "html.parser")

            title = self._extract_title(soup, url)
            content_preview = self._extract_content_preview(soup, url, title)
            relevance_score = self._calculate_relevance(title, content_preview, topic)
            reliability_score = self._calculate_reliability(url, soup)
            source_type = self._determine_source_type(url, soup)
            key_claims = self._extract_key_claims(title, content_preview, soup, topic)

            return SourceInfo(
                url=url,
                title=title,
                content_preview=content_preview,
                relevance_score=relevance_score,
                reliability_score=reliability_score,
                source_type=source_type,
                key_claims=key_claims,
            )
        except requests.exceptions.RequestException as exc:
            logger.warning(f"URL processing failed: {url} - {exc}")
            return None
        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as exc:
            logger.warning(f"URL processing failed: {url} - {exc}")
            return None
        except Exception as exc:
            logger.warning(f"URL processing failed: {url} - {exc}")
            return None

    async def _search_sources(self, topic: str, count: int) -> List[SourceInfo]:
        """Search sources via Brave Search API."""
        brave_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
        if brave_key:
            return await self._brave_search(topic, count, brave_key)

        logger.warning("No search API configured (set BRAVE_SEARCH_API_KEY); falling back to simulation.")
        return await self._simulate_search_sources(topic, count)

    async def _brave_search(self, topic: str, count: int, api_key: str) -> List[SourceInfo]:
        """Brave Search API でソースを検索する。"""
        logger.info(f"Brave Search API query: {topic} (max={count})")
        try:
            response = self.session.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": api_key},
                params={
                    "q": topic,
                    "count": str(min(count, 20)),
                    "search_lang": "jp",
                    "extra_snippets": "true",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            sources: List[SourceInfo] = []
            web_results = data.get("web", {}).get("results", [])
            for item in web_results[:count]:
                search_url = item.get("url")
                if not search_url:
                    continue
                source = await self._process_url(search_url, topic)
                if source:
                    sources.append(source)

            logger.info(f"Brave Search complete: {len(sources)}")
            return sources
        except Exception as exc:
            logger.error(f"Brave Search API failed: {exc}")
            return await self._simulate_search_sources(topic, count)

    async def _simulate_search_sources(self, topic: str, count: int) -> List[SourceInfo]:
        """Fallback simulation for environments without search API."""
        await asyncio.sleep(0.5)
        simulated_sources: List[SourceInfo] = []
        for index in range(count):
            simulated_sources.append(
                SourceInfo(
                    url=f"https://example.com/simulated-source-{index + 1}",
                    title=f"{topic} related source {index + 1}",
                    content_preview=f"Simulated source for {topic}.",
                    relevance_score=0.85 - (index * 0.05),
                    reliability_score=0.9 - (index * 0.02),
                    source_type="article",
                    key_claims=[f"Simulated source {index + 1} is related to {topic}."],
                )
            )
        return simulated_sources

    def _decode_response(self, response: requests.Response) -> str:
        """Decode response text with a couple of fallbacks."""
        text = response.text
        if "<html" in text.lower() or "<!doctype" in text.lower():
            return text

        for encoding in (response.encoding, response.apparent_encoding, "utf-8", "latin-1"):
            if not encoding:
                continue
            try:
                decoded = response.content.decode(encoding, errors="ignore")
                if "<html" in decoded.lower() or "<!doctype" in decoded.lower():
                    return decoded
            except (LookupError, UnicodeDecodeError):
                continue

        return text

    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """Extract title from HTML, falling back to URL slug."""
        candidates = [
            soup.find("meta", property="og:title"),
            soup.find("meta", attrs={"name": "twitter:title"}),
            soup.find("title"),
            soup.find("h1"),
        ]

        for tag in candidates:
            if not tag:
                continue
            # Check if tag is a Tag (not NavigableString)
            from bs4 import Tag
            if isinstance(tag, Tag):
                content = tag.get("content") if tag.has_attr("content") else tag.get_text()
            else:
                content = str(tag)
            if content:
                cleaned = str(content).strip()
                if cleaned:
                    return cleaned

        fallback = self._fallback_title_from_url(url)
        return fallback or "Title unavailable"

    def _extract_content_preview(self, soup: BeautifulSoup, url: str, title: str) -> str:
        """Extract content preview from metadata or text blocks."""
        candidates = [
            soup.find("meta", attrs={"name": "description"}),
            soup.find("meta", property="og:description"),
            soup.find("meta", attrs={"name": "twitter:description"}),
        ]
        for tag in candidates:
            from bs4 import Tag
            if tag and isinstance(tag, Tag):
                content = tag.get("content")
            else:
                content = None
            if content:
                cleaned = str(content).strip()
                if cleaned:
                    return cleaned[:500] + "..." if len(cleaned) > 500 else cleaned

        content_tags = soup.find_all(
            ["p", "div"],
            class_=lambda value: value
            and any(keyword in value.lower() for keyword in ["content", "article", "text", "body"]),
        )
        if content_tags:
            text = " ".join(tag.get_text().strip() for tag in content_tags[:3]).strip()
            if text:
                return text[:500] + "..." if len(text) > 500 else text

        fallback = self._fallback_title_from_url(url)
        if fallback:
            return f"Preview unavailable from direct scrape. Derived title: {fallback}"
        if title and title != "Title unavailable":
            return f"Preview unavailable from direct scrape. Derived title: {title}"
        return "Preview unavailable"

    def _fallback_title_from_url(self, url: str) -> str:
        """Build a basic title from the final path segment."""
        try:
            parsed = urlparse(url)
            slug = parsed.path.rstrip("/").split("/")[-1]
            if not slug:
                return ""
            return slug.replace("-", " ").replace("_", " ").strip()[:120]
        except (ValueError, AttributeError, IndexError):
            return ""

    def _extract_key_claims(
        self,
        title: str,
        content_preview: str,
        soup: BeautifulSoup,
        topic: str,
    ) -> List[str]:
        """Build short claim candidates from title, preview, and article text."""
        candidates: List[tuple[int, str]] = []

        for text in [title, content_preview, *self._extract_article_chunks(soup)]:
            for chunk in self._split_claim_candidates(text):
                cleaned = self._clean_claim(chunk)
                if not cleaned:
                    continue
                priority = self._score_claim_candidate(cleaned, topic)
                candidates.append((priority, cleaned))

        unique: List[str] = []
        seen: set[str] = set()
        for _, claim in sorted(candidates, key=lambda item: item[0], reverse=True):
            key = self._normalize_claim_key(claim)
            if key in seen:
                continue
            seen.add(key)
            unique.append(claim)
            if len(unique) >= 6:
                break

        if unique:
            return unique

        fallback = self._clean_claim(title) or self._clean_claim(content_preview)
        return [fallback] if fallback else []

    def _extract_article_chunks(self, soup: BeautifulSoup) -> List[str]:
        """Extract article-like text blocks for claim generation."""
        article_chunks: List[str] = []
        seen: set[str] = set()

        selectors = [
            "article p",
            "main p",
            "[role='main'] p",
            ".article p",
            ".content p",
            ".story p",
        ]

        tags: List[Any] = []
        for selector in selectors:
            tags.extend(soup.select(selector))
        if not tags:
            tags = soup.find_all("p")

        for tag in tags:
            text = " ".join(tag.get_text(" ", strip=True).split())
            if len(text) < 60:
                continue
            key = self._normalize_claim_key(text)
            if key in seen:
                continue
            seen.add(key)
            article_chunks.append(text)
            if len(article_chunks) >= 6:
                break

        return article_chunks

    def _split_claim_candidates(self, text: str) -> List[str]:
        """Split a text blob into sentence-like claim candidates."""
        if not text:
            return []
        parts = re.split(r"(?<=[.!?。！？])\s+|[;\n]+", text)
        return [part.strip(" -\t\r\n") for part in parts if part.strip()]

    def _clean_claim(self, text: str) -> str:
        """Normalize candidate claim text."""
        if not text:
            return ""
        cleaned = " ".join(text.replace("\u00a0", " ").split())
        cleaned = cleaned.strip(" \"'“”‘’[](){}")
        if not cleaned:
            return ""

        lower = cleaned.lower()
        noisy_prefixes = (
            "preview unavailable",
            "derived title:",
            "read more",
            "watch:",
            "listen:",
        )
        if lower.startswith(noisy_prefixes):
            return ""
        if len(cleaned) < 20:
            return ""
        if len(cleaned) > 260:
            cleaned = cleaned[:257].rstrip() + "..."
        return cleaned

    def _score_claim_candidate(self, claim: str, topic: str) -> int:
        """Rank claim candidates with simple topic overlap heuristics."""
        claim_lower = claim.lower()
        topic_keywords = [word for word in re.findall(r"[a-z0-9]+", topic.lower()) if len(word) >= 3]
        overlap = sum(1 for keyword in topic_keywords if keyword in claim_lower)
        has_digit = bool(re.search(r"\d", claim))
        base = 10 if len(claim) <= 160 else 6
        return base + (overlap * 5) + (2 if has_digit else 0)

    def _normalize_claim_key(self, text: str) -> str:
        """Build a dedupe key for extracted claims."""
        return re.sub(r"[^a-z0-9一-龥ぁ-んァ-ヶ]+", "", text.lower())

    def _calculate_relevance(self, title: str, content: str, topic: str) -> float:
        """Simple keyword-based relevance score."""
        text = f"{title} {content}".lower()
        topic_words = topic.lower().split()
        matches = sum(1 for word in topic_words if word in text)
        return min(matches / len(topic_words), 1.0) if topic_words else 0.0

    def _calculate_reliability(self, url: str, soup: BeautifulSoup) -> float:
        """Heuristic reliability score."""
        score = 0.5
        try:
            domain = url.split("/")[2].lower()
        except (IndexError, AttributeError):
            domain = ""

        trusted_domains = [
            "nikkei.com",
            "asahi.com",
            "mainichi.jp",
            "yomiuri.co.jp",
            "nhk.or.jp",
            "reuters.com",
            "bbc.com",
            "cnn.com",
            "apnews.com",
            "theguardian.com",
            "euronews.com",
            "wikipedia.org",
        ]

        if any(trusted in domain for trusted in trusted_domains):
            score += 0.3
        if url.startswith("https"):
            score += 0.1
        if soup.find("article") or soup.find("time") or soup.find("author"):
            score += 0.1

        return min(score, 1.0)

    def _determine_source_type(self, url: str, soup: BeautifulSoup) -> str:
        """Infer source type from domain."""
        try:
            domain = url.split("/")[2].lower()
        except (IndexError, AttributeError):
            domain = ""

        news_indicators = ["news", "nikkei", "asahi", "mainichi", "yomiuri", "nhk", "apnews", "guardian", "euronews"]
        if any(indicator in domain for indicator in news_indicators):
            return "news"

        academic_indicators = ["edu", "ac.jp", "scholar", "researchgate"]
        if any(indicator in domain for indicator in academic_indicators):
            return "academic"

        blog_indicators = ["blog", "wordpress", "medium", "note"]
        if any(indicator in domain for indicator in blog_indicators):
            return "blog"

        return "article"

    def save_sources_info(self, sources: List[SourceInfo], output_path: Path) -> None:
        """Persist SourceInfo list as JSON."""
        import json
        from dataclasses import asdict

        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump([asdict(source) for source in sources], handle, ensure_ascii=False, indent=2)

        logger.info(f"Saved source metadata: {output_path}")
