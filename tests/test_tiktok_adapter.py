"""Tests for src/core/platforms/tiktok_adapter.py."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.platforms.tiktok_adapter import TikTokPlatformAdapter


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestInit:
    def test_default(self):
        adapter = TikTokPlatformAdapter()
        assert adapter.api_key is None
        assert adapter.access_token is None
        assert "tiktok" in adapter.base_url

    def test_with_keys(self):
        adapter = TikTokPlatformAdapter(api_key="k", access_token="t")
        assert adapter.api_key == "k"
        assert adapter.access_token == "t"


# ---------------------------------------------------------------------------
# _adapt_metadata_for_tiktok
# ---------------------------------------------------------------------------

class TestAdaptMetadata:
    def test_normal_video(self):
        adapter = TikTokPlatformAdapter()
        result = adapter._adapt_metadata_for_tiktok(
            {"title": "Test Video", "description": "A test。Second sentence.", "tags": ["ai", "tech"]},
            is_shorts=False,
        )
        assert result["title"] == "Test Video"
        assert "#ai" in result["tags"]
        assert "#tech" in result["tags"]
        assert result["privacy_level"] == "private"  # default

    def test_shorts_truncates_description(self):
        adapter = TikTokPlatformAdapter()
        result = adapter._adapt_metadata_for_tiktok(
            {"title": "Short", "description": "First。Second。Third.", "tags": ["tag1"]},
            is_shorts=True,
        )
        # Shorts only keeps first sentence
        assert "Second" not in result["description"]
        assert "First" in result["description"]

    def test_title_truncation(self):
        adapter = TikTokPlatformAdapter()
        long_title = "A" * 3000
        result = adapter._adapt_metadata_for_tiktok(
            {"title": long_title, "description": ""},
            is_shorts=False,
        )
        assert len(result["title"]) == 2200

    def test_privacy_mapping(self):
        adapter = TikTokPlatformAdapter()
        for yt_status, expected in [("public", "public"), ("private", "private"), ("unlisted", "public")]:
            result = adapter._adapt_metadata_for_tiktok(
                {"title": "", "description": "", "privacy_status": yt_status},
                is_shorts=False,
            )
            assert result["privacy_level"] == expected

    def test_max_10_hashtags(self):
        adapter = TikTokPlatformAdapter()
        result = adapter._adapt_metadata_for_tiktok(
            {"title": "", "description": "", "tags": [f"tag{i}" for i in range(20)]},
            is_shorts=False,
        )
        assert len(result["tags"]) == 10


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------

class TestPublish:
    @pytest.mark.asyncio
    async def test_publish_no_video(self):
        """Publish fails gracefully when no video in package."""
        adapter = TikTokPlatformAdapter()
        result = await adapter.publish({"metadata": {}})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_publish_file_not_found(self, tmp_path: Path):
        """Publish fails when video file doesn't exist."""
        adapter = TikTokPlatformAdapter()
        video = MagicMock()
        video.file_path = tmp_path / "nonexistent.mp4"
        result = await adapter.publish({"video": video, "metadata": {}})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_publish_success(self, tmp_path: Path):
        """Successful publish returns success=True."""
        adapter = TikTokPlatformAdapter()
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video" * 100)
        video = MagicMock()
        video.file_path = video_file

        result = await adapter.publish(
            {"video": video, "metadata": {"title": "Test", "description": "desc"}},
            options={"format": "video"},
        )
        assert result["success"] is True
        assert result["platform"] == "tiktok"

    @pytest.mark.asyncio
    async def test_publish_shorts(self, tmp_path: Path):
        """Shorts format is correctly passed."""
        adapter = TikTokPlatformAdapter()
        video_file = tmp_path / "short.mp4"
        video_file.write_bytes(b"fake" * 100)
        video = MagicMock()
        video.file_path = video_file

        result = await adapter.publish(
            {"video": video, "metadata": {}},
            options={"format": "shorts"},
        )
        assert result["success"] is True
        assert result["is_shorts"] is True


# ---------------------------------------------------------------------------
# get_video_status / delete_video
# ---------------------------------------------------------------------------

class TestStatusAndDelete:
    @pytest.mark.asyncio
    async def test_get_video_status(self):
        adapter = TikTokPlatformAdapter()
        result = await adapter.get_video_status("vid_123")
        assert result["video_id"] == "vid_123"
        assert result["status"] == "published"

    @pytest.mark.asyncio
    async def test_delete_video(self):
        adapter = TikTokPlatformAdapter()
        result = await adapter.delete_video("vid_123")
        assert result is True
