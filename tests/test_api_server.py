"""Tests for src/server/api_server.py — OperationalAPIServer endpoints."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def server_instance():
    """Create a fresh OperationalAPIServer instance."""
    with patch("src.server.api_server.build_default_pipeline"):
        from src.server.api_server import OperationalAPIServer
        return OperationalAPIServer()


@pytest.fixture()
def client(server_instance):
    """TestClient for the operational API."""
    return TestClient(server_instance.app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_check_healthy(self, client: TestClient, server_instance):
        """Health check returns 200 when all checks pass."""
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "healthy" in body
        assert "checks" in body
        assert "timestamp" in body

    def test_health_check_database(self, server_instance):
        """Database check always returns healthy (file-based)."""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(server_instance.check_database())
        assert result["status"] == "healthy"

    def test_health_check_file_system(self, server_instance, tmp_path: Path):
        """File system check passes when dirs exist and are writable."""
        import asyncio
        with patch("src.server.api_server.settings") as mock_settings:
            mock_settings.DATA_DIR = tmp_path
            mock_settings.VIDEOS_DIR = tmp_path / "videos"
            mock_settings.AUDIO_DIR = tmp_path / "audio"
            mock_settings.SLIDES_DIR = tmp_path / "slides"
            for d in [mock_settings.VIDEOS_DIR, mock_settings.AUDIO_DIR, mock_settings.SLIDES_DIR]:
                d.mkdir()
            result = asyncio.get_event_loop().run_until_complete(server_instance.check_file_system())
            assert result["status"] == "healthy"

    def test_health_check_file_system_missing_dir(self, server_instance, tmp_path: Path):
        """File system check fails when directory is missing."""
        import asyncio
        with patch("src.server.api_server.settings") as mock_settings:
            mock_settings.DATA_DIR = tmp_path
            mock_settings.VIDEOS_DIR = tmp_path / "nonexistent"
            mock_settings.AUDIO_DIR = tmp_path / "audio"
            mock_settings.SLIDES_DIR = tmp_path / "slides"
            result = asyncio.get_event_loop().run_until_complete(server_instance.check_file_system())
            assert result["status"] == "unhealthy"

    def test_health_check_api_keys_configured(self, server_instance):
        """API keys check returns healthy when keys are set."""
        import asyncio
        with patch("src.server.api_server.settings") as mock_settings:
            mock_settings.PIPELINE_COMPONENTS = {"script_provider": "gemini"}
            mock_settings.GEMINI_API_KEY = "test_key"
            result = asyncio.get_event_loop().run_until_complete(server_instance.check_api_keys())
            assert result["status"] == "healthy"

    def test_health_check_api_keys_missing(self, server_instance):
        """API keys check warns when required key is missing."""
        import asyncio
        with patch("src.server.api_server.settings") as mock_settings:
            mock_settings.PIPELINE_COMPONENTS = {"script_provider": "gemini"}
            mock_settings.GEMINI_API_KEY = ""
            result = asyncio.get_event_loop().run_until_complete(server_instance.check_api_keys())
            assert result["status"] == "warning"

    def test_health_check_pipeline_success(self, server_instance):
        """Pipeline check succeeds when build_default_pipeline works."""
        import asyncio
        with patch("src.server.api_server.build_default_pipeline", return_value=MagicMock()):
            result = asyncio.get_event_loop().run_until_complete(server_instance.check_pipeline())
            assert result["status"] == "healthy"

    def test_health_check_pipeline_failure(self, server_instance):
        """Pipeline check fails when build raises."""
        import asyncio
        with patch("src.server.api_server.build_default_pipeline", side_effect=ImportError("missing")):
            result = asyncio.get_event_loop().run_until_complete(server_instance.check_pipeline())
            assert result["status"] == "unhealthy"


# ---------------------------------------------------------------------------
# /metrics
# ---------------------------------------------------------------------------

class TestMetrics:
    def test_metrics_endpoint(self, client: TestClient):
        resp = client.get("/metrics")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------------

class TestStatus:
    def test_system_status(self, client: TestClient):
        resp = client.get("/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "system_health" in body
        assert "active_jobs_count" in body
        assert "timestamp" in body


# ---------------------------------------------------------------------------
# /jobs
# ---------------------------------------------------------------------------

class TestJobs:
    def test_list_jobs_empty(self, client: TestClient):
        resp = client.get("/jobs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_active"] == 0

    def test_cancel_job_not_found(self, client: TestClient):
        resp = client.post("/jobs/nonexistent/cancel")
        assert resp.status_code == 404

    def test_cancel_job_success(self, client: TestClient, server_instance):
        server_instance.system_status["active_jobs"]["job1"] = {"status": "running"}
        resp = client.post("/jobs/job1/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"


# ---------------------------------------------------------------------------
# /logs
# ---------------------------------------------------------------------------

class TestLogs:
    def test_get_logs_empty(self, client: TestClient):
        resp = client.get("/logs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_lines"] == 0

    def test_get_logs_with_entries(self, client: TestClient, server_instance):
        server_instance.log_activity("test message 1")
        server_instance.log_activity("test message 2")
        resp = client.get("/logs?limit=1")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["logs"]) == 1


# ---------------------------------------------------------------------------
# /config
# ---------------------------------------------------------------------------

class TestConfig:
    def test_get_config(self, client: TestClient):
        resp = client.get("/config")
        assert resp.status_code == 200
        body = resp.json()
        assert "APP_NAME" in body
        assert "VERSION" in body
        # API keys should NOT be in the response
        assert "GEMINI_API_KEY" not in body


# ---------------------------------------------------------------------------
# /maintenance/cleanup
# ---------------------------------------------------------------------------

class TestCleanup:
    def test_cleanup_scheduled(self, client: TestClient):
        resp = client.post("/maintenance/cleanup?days=3")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "scheduled"
        assert body["cleanup_days"] == 3


# ---------------------------------------------------------------------------
# Helper methods
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_log_activity(self, server_instance):
        server_instance.log_activity("test entry")
        logs = server_instance.system_status["recent_logs"]
        assert len(logs) == 1
        assert logs[0]["message"] == "test entry"

    def test_log_activity_limit(self, server_instance):
        """Logs are capped at 1000 entries."""
        for i in range(1005):
            server_instance.log_activity(f"entry {i}")
        logs = server_instance.system_status["recent_logs"]
        assert len(logs) == 1000

    def test_update_performance_stats(self, server_instance):
        server_instance.update_performance_stats({"avg_latency": 0.5})
        assert server_instance.system_status["performance_stats"]["avg_latency"] == 0.5

    def test_increment_request_count(self, server_instance):
        """Should not raise even with mock metrics."""
        server_instance._increment_request_count("GET", "/test", "200")

    def test_perform_cleanup(self, server_instance, tmp_path: Path):
        """Cleanup deletes old files."""
        import asyncio
        with patch("src.server.api_server.settings") as mock_settings:
            cleanup_dir = tmp_path / "videos"
            cleanup_dir.mkdir()
            old_file = cleanup_dir / "old.mp4"
            old_file.write_text("old")
            import os
            os.utime(str(old_file), (1_000_000, 1_000_000))  # very old

            mock_settings.VIDEOS_DIR = cleanup_dir
            mock_settings.AUDIO_DIR = tmp_path / "audio"
            mock_settings.SLIDES_DIR = tmp_path / "slides"
            mock_settings.SCRIPTS_DIR = tmp_path / "scripts"

            asyncio.get_event_loop().run_until_complete(server_instance.perform_cleanup(1))
            assert not old_file.exists()
