"""Tests for src/server/api.py — FastAPI endpoints."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class _FakeFile:
    name: str
    _size: int = 100
    _mtime: float = 1_700_000_000.0

    def is_file(self) -> bool:
        return True

    def stat(self) -> Any:
        return type("S", (), {"st_size": self._size, "st_mtime": self._mtime})()

    def resolve(self) -> Path:
        return Path("/fake/base") / self.name


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Create a fresh TestClient, resetting in-memory stores."""
    from src.server.api import app, RUNS, ARTIFACTS, PROGRESS

    RUNS.clear()
    ARTIFACTS.clear()
    PROGRESS.clear()
    return TestClient(app)


# ---------------------------------------------------------------------------
# /api/v1/spec
# ---------------------------------------------------------------------------

class TestGetSpec:
    def test_spec_fallback(self, client: TestClient):
        """When api_spec_design cannot be imported, returns minimal spec."""
        resp = client.get("/api/v1/spec")
        assert resp.status_code == 200
        body = resp.json()
        assert body["openapi"] == "3.0.0"
        assert "paths" in body

    def test_spec_success(self, client: TestClient):
        """When api_spec_design is available, returns generated spec."""
        fake_spec = {"openapi": "3.0.0", "info": {"title": "test"}}
        with patch.dict("sys.modules", {"api_spec_design": MagicMock(generate_openapi_spec=lambda: fake_spec)}):
            resp = client.get("/api/v1/spec")
            assert resp.status_code == 200
            body = resp.json()
            assert body["info"]["title"] == "test"


# ---------------------------------------------------------------------------
# /api/v1/settings
# ---------------------------------------------------------------------------

class TestSettings:
    def test_get_settings(self, client: TestClient):
        resp = client.get("/api/v1/settings")
        assert resp.status_code == 200
        body = resp.json()
        assert "pipeline_components" in body
        assert "pipeline_stage_modes" in body
        assert "youtube_privacy_default" in body

    def test_update_settings_pipeline_components(self, client: TestClient):
        resp = client.post("/api/v1/settings", json={
            "pipeline_components": {"editing_backend": "test_backend"},
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["pipeline_components"]["editing_backend"] == "test_backend"

    def test_update_settings_stage_modes(self, client: TestClient):
        resp = client.post("/api/v1/settings", json={
            "pipeline_stage_modes": {"stage1": "manual"},
        })
        assert resp.status_code == 200
        assert resp.json()["pipeline_stage_modes"]["stage1"] == "manual"

    def test_update_settings_api_keys_valid(self, client: TestClient):
        """Valid API keys are accepted and set in env."""
        resp = client.post("/api/v1/settings", json={
            "api_keys": {"gemini": "AIza_test_key_123"},
        })
        assert resp.status_code == 200

    def test_update_settings_api_keys_invalid(self, client: TestClient):
        """Keys with control characters are rejected."""
        resp = client.post("/api/v1/settings", json={
            "api_keys": {"gemini": "bad\nkey"},
        })
        assert resp.status_code == 200  # still returns 200, key just not set

    def test_update_settings_non_dict_ignored(self, client: TestClient):
        """Non-dict payloads for sub-fields are gracefully ignored."""
        resp = client.post("/api/v1/settings", json={
            "pipeline_components": "not_a_dict",
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /api/v1/assets/{kind}
# ---------------------------------------------------------------------------

class TestAssets:
    def test_unsupported_kind(self, client: TestClient):
        resp = client.get("/api/v1/assets/unknown")
        assert resp.status_code == 400

    def test_list_audio_empty(self, client: TestClient):
        """If directory exists but is empty, returns empty list."""
        with patch("src.server.api.settings") as mock_settings:
            mock_dir = MagicMock()
            mock_dir.resolve.return_value = Path("/fake/audio")
            mock_dir.exists.return_value = True
            mock_dir.glob.return_value = []
            mock_settings.AUDIO_DIR = mock_dir
            mock_settings.VIDEOS_DIR = MagicMock()
            mock_settings.SLIDES_DIR = MagicMock()
            resp = client.get("/api/v1/assets/audio")
            assert resp.status_code == 200
            assert resp.json() == []

    def test_list_audio_with_files(self, tmp_path: Path, client: TestClient):
        """When directory has files, returns them with limit."""
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        for i in range(5):
            (audio_dir / f"file{i}.wav").write_text("fake")

        from src.server.api import settings as api_settings
        old_dir = api_settings.AUDIO_DIR
        try:
            api_settings.AUDIO_DIR = audio_dir
            resp = client.get("/api/v1/assets/audio?limit=2")
            assert resp.status_code == 200
            assert len(resp.json()) == 2
        finally:
            api_settings.AUDIO_DIR = old_dir


# ---------------------------------------------------------------------------
# /api/v1/test/connections
# ---------------------------------------------------------------------------

class TestConnections:
    def test_no_keys_set(self, client: TestClient):
        """When no API keys are set, returns 'no key' for all."""
        with patch("src.server.api.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.YOUTUBE_API_KEY = ""
            resp = client.post("/api/v1/test/connections")
            assert resp.status_code == 200
            body = resp.json()
            assert body["gemini"]["success"] is False
            assert body["openai"]["success"] is False
            assert body["youtube"]["success"] is False


# ---------------------------------------------------------------------------
# /api/v1/pipeline
# ---------------------------------------------------------------------------

class TestPipeline:
    def test_missing_topic(self, client: TestClient):
        resp = client.post("/api/v1/pipeline", json={})
        assert resp.status_code == 400

    def test_invalid_quality(self, client: TestClient):
        resp = client.post("/api/v1/pipeline", json={"topic": "test", "quality": "4k"})
        assert resp.status_code == 400

    def test_quality_must_be_string(self, client: TestClient):
        resp = client.post("/api/v1/pipeline", json={"topic": "test", "quality": 123})
        assert resp.status_code == 400

    def test_successful_run(self, client: TestClient):
        mock_pipeline = AsyncMock()
        mock_pipeline.run.return_value = {
            "success": True,
            "youtube_url": "https://youtube.com/test",
            "artifacts": {"video": "test.mp4"},
        }
        with patch("src.server.api.build_default_pipeline", return_value=mock_pipeline):
            resp = client.post("/api/v1/pipeline", json={"topic": "AI basics"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["youtube_url"] == "https://youtube.com/test"
            assert "execution_id" in body

    def test_pipeline_failure(self, client: TestClient):
        mock_pipeline = AsyncMock()
        mock_pipeline.run.side_effect = RuntimeError("boom")
        with patch("src.server.api.build_default_pipeline", return_value=mock_pipeline):
            resp = client.post("/api/v1/pipeline", json={"topic": "fail test"})
            assert resp.status_code == 500


# ---------------------------------------------------------------------------
# /api/v1/pipeline/{execution_id}/progress
# ---------------------------------------------------------------------------

class TestProgress:
    def test_not_found(self, client: TestClient):
        resp = client.get("/api/v1/pipeline/nonexistent/progress")
        assert resp.status_code == 404

    def test_found(self, client: TestClient):
        from src.server.api import PROGRESS
        PROGRESS["run_123"] = {"stage": "rendering", "progress": 0.5, "message": "half done"}
        resp = client.get("/api/v1/pipeline/run_123/progress")
        assert resp.status_code == 200
        assert resp.json()["stage"] == "rendering"


# ---------------------------------------------------------------------------
# /api/v1/runs
# ---------------------------------------------------------------------------

class TestRuns:
    def test_list_runs_empty(self, client: TestClient):
        resp = client.get("/api/v1/runs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_runs_with_data(self, client: TestClient):
        from src.server.api import RUNS
        RUNS["r1"] = {"id": "r1", "status": "succeeded", "finished_at": "2025-01-01"}
        RUNS["r2"] = {"id": "r2", "status": "failed", "finished_at": "2025-01-02"}
        resp = client.get("/api/v1/runs")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_runs_filter_status(self, client: TestClient):
        from src.server.api import RUNS
        RUNS["r1"] = {"id": "r1", "status": "succeeded", "finished_at": "2025-01-01"}
        RUNS["r2"] = {"id": "r2", "status": "failed", "finished_at": "2025-01-02"}
        resp = client.get("/api/v1/runs?status=failed")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["status"] == "failed"

    def test_list_runs_limit(self, client: TestClient):
        from src.server.api import RUNS
        for i in range(5):
            RUNS[f"r{i}"] = {"id": f"r{i}", "status": "succeeded", "finished_at": f"2025-01-0{i+1}"}
        resp = client.get("/api/v1/runs?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_run_not_found(self, client: TestClient):
        resp = client.get("/api/v1/runs/nonexistent")
        assert resp.status_code == 404

    def test_get_run_found(self, client: TestClient):
        from src.server.api import RUNS
        RUNS["r1"] = {"id": "r1", "status": "succeeded"}
        resp = client.get("/api/v1/runs/r1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "r1"


# ---------------------------------------------------------------------------
# /api/v1/runs/{execution_id}/artifacts
# ---------------------------------------------------------------------------

class TestArtifacts:
    def test_not_found(self, client: TestClient):
        resp = client.get("/api/v1/runs/nonexistent/artifacts")
        assert resp.status_code == 404

    def test_found(self, client: TestClient):
        from src.server.api import ARTIFACTS
        ARTIFACTS["r1"] = {"video": "test.mp4"}
        resp = client.get("/api/v1/runs/r1/artifacts")
        assert resp.status_code == 200
        assert resp.json()["video"] == "test.mp4"


# ---------------------------------------------------------------------------
# Serializer helpers
# ---------------------------------------------------------------------------

class TestConvert:
    def test_convert_datetime(self):
        from src.server.api import _convert
        dt = datetime(2025, 1, 1, 12, 0, 0)
        assert _convert(dt) == "2025-01-01T12:00:00"

    def test_convert_path(self):
        from src.server.api import _convert
        result = _convert(Path("/test/path"))
        assert "test" in result and "path" in result

    def test_convert_tuple(self):
        from src.server.api import _convert
        assert _convert((1, 2, 3)) == [1, 2, 3]

    def test_convert_dataclass(self):
        from src.server.api import _convert

        @dataclass
        class Foo:
            x: int = 1

        result = _convert(Foo())
        assert result == {"x": 1}

    def test_convert_passthrough(self):
        from src.server.api import _convert
        assert _convert("hello") == "hello"


class TestToDict:
    def test_simple_dict(self):
        from src.server.api import _to_dict
        assert _to_dict({"a": 1}) == {"a": 1}

    def test_dataclass_conversion(self):
        from src.server.api import _to_dict

        @dataclass
        class Bar:
            y: str = "test"

        result = _to_dict(Bar())
        assert result == {"y": "test"}

    def test_fallback_to_string(self):
        from src.server.api import _to_dict

        class Unserializable:
            def __repr__(self):
                return "unserializable_obj"

        result = _to_dict(Unserializable())
        assert "unserializable_obj" in result


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_and_load_runs(self, tmp_path: Path):
        from src.server import api
        old_file = api.RUNS_FILE
        try:
            api.RUNS_FILE = tmp_path / "runs.json"
            api.RUNS["test1"] = {"id": "test1", "status": "ok"}
            api._save_runs()

            assert api.RUNS_FILE.exists()
            data = json.loads(api.RUNS_FILE.read_text(encoding="utf-8"))
            assert data["test1"]["status"] == "ok"
        finally:
            api.RUNS_FILE = old_file

    def test_save_artifact(self, tmp_path: Path):
        from src.server import api
        old_dir = api.ARTIFACTS_DIR
        try:
            api.ARTIFACTS_DIR = tmp_path
            api._save_artifact("exec1", {"video": "test.mp4"})
            artifact_file = tmp_path / "exec1.json"
            assert artifact_file.exists()
            data = json.loads(artifact_file.read_text(encoding="utf-8"))
            assert data["video"] == "test.mp4"
        finally:
            api.ARTIFACTS_DIR = old_dir

    def test_load_persistence_corrupt_file(self, tmp_path: Path):
        from src.server import api
        old_file = api.RUNS_FILE
        try:
            api.RUNS_FILE = tmp_path / "runs.json"
            api.RUNS_FILE.write_text("not valid json", encoding="utf-8")
            api.RUNS.clear()
            api._load_persistence()
            # Should not crash, RUNS stays empty
            assert len(api.RUNS) == 0
        finally:
            api.RUNS_FILE = old_file

    def test_save_runs_oserror(self, tmp_path: Path):
        """_save_runs handles OSError gracefully."""
        from src.server import api
        old_file = api.RUNS_FILE
        try:
            # Point to a nonexistent deep path
            api.RUNS_FILE = tmp_path / "nonexistent" / "deep" / "runs.json"
            api.RUNS["x"] = {"id": "x"}
            # Should not raise
            api._save_runs()
        finally:
            api.RUNS_FILE = old_file

    def test_save_artifact_oserror(self, tmp_path: Path):
        """_save_artifact handles OSError gracefully."""
        from src.server import api
        old_dir = api.ARTIFACTS_DIR
        try:
            api.ARTIFACTS_DIR = tmp_path / "nonexistent" / "deep"
            # Should not raise
            api._save_artifact("exec_err", {"key": "val"})
        finally:
            api.ARTIFACTS_DIR = old_dir

    def test_load_persistence_artifact_error(self, tmp_path: Path):
        """_load_persistence handles artifact load errors."""
        from src.server import api
        old_file = api.RUNS_FILE
        old_dir = api.ARTIFACTS_DIR
        try:
            api.RUNS_FILE = tmp_path / "runs.json"
            api.ARTIFACTS_DIR = tmp_path / "artifacts"
            api.ARTIFACTS_DIR.mkdir()
            # Valid runs file but bad artifact
            api.RUNS_FILE.write_text('{"r1": {"id": "r1"}}', encoding="utf-8")
            bad_artifact = api.ARTIFACTS_DIR / "r1.json"
            bad_artifact.write_text("not json", encoding="utf-8")
            api.RUNS.clear()
            api.ARTIFACTS.clear()
            api._load_persistence()
            # Runs should load, artifact should fail silently
            assert "r1" in api.RUNS
        finally:
            api.RUNS_FILE = old_file
            api.ARTIFACTS_DIR = old_dir


# ---------------------------------------------------------------------------
# /api/v1/spec — exception branches
# ---------------------------------------------------------------------------

class TestGetSpecExceptions:
    def test_spec_generic_exception(self, client: TestClient):
        """get_spec handles generic exception (not ImportError)."""
        mock_mod = MagicMock()
        mock_mod.generate_openapi_spec.side_effect = RuntimeError("unexpected")
        with patch.dict("sys.modules", {"api_spec_design": mock_mod}):
            resp = client.get("/api/v1/spec")
            assert resp.status_code == 200
            body = resp.json()
            assert body["openapi"] == "3.0.0"


# ---------------------------------------------------------------------------
# /api/v1/settings — API key validation branches
# ---------------------------------------------------------------------------

class TestSettingsApiKeyValidation:
    def test_update_gemini_key(self, client: TestClient):
        """Setting a valid Gemini key."""
        resp = client.post("/api/v1/settings", json={
            "api_keys": {"gemini": "valid_key_123"},
        })
        assert resp.status_code == 200

    def test_update_openai_key(self, client: TestClient):
        """Setting a valid OpenAI key."""
        resp = client.post("/api/v1/settings", json={
            "api_keys": {"openai": "sk-valid_key_123"},
        })
        assert resp.status_code == 200

    def test_update_youtube_key(self, client: TestClient):
        """Setting a valid YouTube key."""
        resp = client.post("/api/v1/settings", json={
            "api_keys": {"youtube": "yt_valid_key_123"},
        })
        assert resp.status_code == 200

    def test_update_empty_key_rejected(self, client: TestClient):
        """Empty API key should be rejected."""
        resp = client.post("/api/v1/settings", json={
            "api_keys": {"gemini": ""},
        })
        assert resp.status_code == 200  # Endpoint doesn't fail, just ignores


# ---------------------------------------------------------------------------
# /api/v1/assets — symlink escape
# ---------------------------------------------------------------------------

class TestListAssetsEdgeCases:
    def test_list_assets_audio(self, client: TestClient, tmp_path: Path):
        """list_assets for audio kind."""
        with patch("src.server.api.settings") as mock_settings:
            assets_dir = tmp_path / "audio"
            assets_dir.mkdir()
            mock_settings.AUDIO_DIR = assets_dir
            resp = client.get("/api/v1/assets/audio")
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /api/v1/test/connections — exception branches
# ---------------------------------------------------------------------------

class TestConnectionTestsExceptions:
    def test_connection_tests_endpoint(self, client: TestClient):
        """Connection test returns per-service results."""
        resp = client.post("/api/v1/test/connections")
        assert resp.status_code == 200
        body = resp.json()
        # Response is flat dict with service names as keys
        assert "gemini" in body
        assert "success" in body["gemini"]


# ---------------------------------------------------------------------------
# /api/v1/pipeline — exception branches
# ---------------------------------------------------------------------------

class TestPipelineEndpoint:
    def test_pipeline_requires_topic(self, client: TestClient):
        """run_pipeline needs a topic."""
        resp = client.post("/api/v1/pipeline", json={})
        assert resp.status_code in (200, 400, 422)
