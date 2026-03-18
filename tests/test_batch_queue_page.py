"""Tests for SP-040 Phase 3: Batch Queue Web UI page logic.

streamlit がテスト環境にない場合はスキップ。
ロジック関数のみをテストする。
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# streamlit が無ければ全スキップ
st_mock = MagicMock()
try:
    import streamlit  # noqa: F401
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False
    sys.modules["streamlit"] = st_mock

pytestmark = pytest.mark.skipif(
    not HAS_STREAMLIT and not st_mock,
    reason="streamlit not available",
)


class TestDefaultBatchConfig:
    """_default_batch_config のテスト"""

    def test_returns_valid_structure(self):
        from src.web.ui.pages.batch_queue import _default_batch_config

        config = _default_batch_config()
        assert "batch_name" in config
        assert "defaults" in config
        assert "topics" in config
        assert isinstance(config["topics"], list)
        assert len(config["topics"]) == 0

    def test_defaults_have_required_keys(self):
        from src.web.ui.pages.batch_queue import _default_batch_config

        defaults = _default_batch_config()["defaults"]
        assert "style" in defaults
        assert "duration" in defaults
        assert "auto_images" in defaults
        assert "auto_review" in defaults
        assert "speaker_map" in defaults


class TestLoadTopicsFromUpload:
    """_load_topics_from_upload のテスト"""

    def _make_upload(self, data: dict) -> MagicMock:
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        mock = MagicMock()
        mock.read.return_value = content
        return mock

    def test_valid_upload(self):
        from src.web.ui.pages.batch_queue import _load_topics_from_upload

        data = {
            "batch_name": "test",
            "topics": [{"topic": "A"}, {"topic": "B"}],
        }
        result = _load_topics_from_upload(self._make_upload(data))
        assert result is not None
        assert len(result["topics"]) == 2

    def test_missing_topics_key(self):
        from src.web.ui.pages.batch_queue import _load_topics_from_upload

        result = _load_topics_from_upload(self._make_upload({"batch_name": "x"}))
        assert result is None

    def test_invalid_json(self):
        from src.web.ui.pages.batch_queue import _load_topics_from_upload

        mock = MagicMock()
        mock.read.return_value = b"not json{"
        result = _load_topics_from_upload(mock)
        assert result is None


class TestExecuteBatch:
    """_execute_batch のテスト"""

    @pytest.mark.asyncio
    async def test_success_flow(self, tmp_path: Path):
        from src.web.ui.pages.batch_queue import _execute_batch

        config = {
            "batch_name": "test_batch",
            "defaults": {"style": "default", "duration": 300, "auto_images": True, "auto_review": True},
            "topics": [
                {"topic": "Topic A"},
                {"topic": "Topic B"},
            ],
        }

        progress = MagicMock()

        with patch("scripts.research_cli.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = Path("/fake/output.csv")
            result = await _execute_batch(config, tmp_path, interval=0, progress_container=progress)

        assert result["success"] is True
        assert len(result["results"]) == 2
        assert all(r["status"] == "success" for r in result["results"])

        # batch_result.json should exist
        result_path = Path(result["result_path"])
        assert result_path.exists()

    @pytest.mark.asyncio
    async def test_partial_failure(self, tmp_path: Path):
        from src.web.ui.pages.batch_queue import _execute_batch

        config = {
            "batch_name": "fail_batch",
            "defaults": {"style": "default", "duration": 300},
            "topics": [
                {"topic": "OK Topic"},
                {"topic": "Bad Topic"},
            ],
        }

        call_count = 0

        async def mock_pipeline(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("API quota exceeded")
            return Path("/fake/output.csv")

        progress = MagicMock()

        with patch("scripts.research_cli.run_pipeline", side_effect=mock_pipeline):
            result = await _execute_batch(config, tmp_path, interval=0, progress_container=progress)

        assert result["success"] is True
        statuses = [r["status"] for r in result["results"]]
        assert statuses == ["success", "failed"]

    @pytest.mark.asyncio
    async def test_empty_topic_skipped(self, tmp_path: Path):
        from src.web.ui.pages.batch_queue import _execute_batch

        config = {
            "batch_name": "skip_batch",
            "defaults": {},
            "topics": [
                {"topic": "Valid"},
                {"topic": ""},
                {"topic": "Also valid"},
            ],
        }

        progress = MagicMock()

        with patch("scripts.research_cli.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = Path("/fake/output.csv")
            result = await _execute_batch(config, tmp_path, interval=0, progress_container=progress)

        assert mock_pipeline.call_count == 2
        statuses = [r["status"] for r in result["results"]]
        assert statuses == ["success", "skipped", "success"]


class TestWebAppIntegration:
    """web_app.py へのバッチページ統合テスト"""

    def test_batch_page_in_options(self):
        from src.web.web_app import PAGE_OPTIONS, PAGE_ALIASES

        assert any("バッチ" in opt for opt in PAGE_OPTIONS)
        assert "batch" in PAGE_ALIASES

    def test_batch_page_importable(self):
        from src.web.ui.pages import show_batch_queue_page

        assert callable(show_batch_queue_page)
