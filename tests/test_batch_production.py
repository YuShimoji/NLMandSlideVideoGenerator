"""Tests for SP-040 Batch Production Queue."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.research_cli import run_batch


@pytest.fixture
def topics_file(tmp_path: Path) -> Path:
    """Create a sample topics.json file."""
    data = {
        "batch_name": "test_batch",
        "defaults": {
            "style": "default",
            "duration": 300,
            "auto_images": True,
            "auto_review": True,
        },
        "topics": [
            {"topic": "Topic A"},
            {"topic": "Topic B", "style": "news", "duration": 600},
            {"topic": "Topic C"},
        ],
    }
    path = tmp_path / "topics.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def empty_topics_file(tmp_path: Path) -> Path:
    """Create a topics.json with no topics."""
    data = {"batch_name": "empty", "topics": []}
    path = tmp_path / "empty_topics.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def topics_with_empty(tmp_path: Path) -> Path:
    """Create a topics.json with one empty topic."""
    data = {
        "batch_name": "has_empty",
        "topics": [
            {"topic": "Valid topic"},
            {"topic": ""},
            {"topic": "Another valid"},
        ],
    }
    path = tmp_path / "has_empty.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


class TestBatchProduction:
    """SP-040 Batch Production Queue のテスト"""

    @pytest.mark.asyncio
    async def test_batch_nonexistent_file(self, tmp_path: Path, capsys):
        """存在しないファイルを指定した場合"""
        await run_batch(tmp_path / "nonexistent.json", output_dir=tmp_path / "out")
        captured = capsys.readouterr()
        assert "ERROR" in captured.out

    @pytest.mark.asyncio
    async def test_batch_empty_topics(self, empty_topics_file: Path, tmp_path: Path, capsys):
        """トピックが空の場合"""
        await run_batch(empty_topics_file, output_dir=tmp_path / "out")
        captured = capsys.readouterr()
        assert "no topics" in captured.out.lower() or "ERROR" in captured.out

    @pytest.mark.asyncio
    async def test_batch_success_flow(self, topics_file: Path, tmp_path: Path):
        """正常バッチ実行（run_pipeline をモック）"""
        output_dir = tmp_path / "batch_output"

        with patch("scripts.research_cli.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = Path("/fake/output.csv")
            await run_batch(topics_file, output_dir=output_dir, interval=0)

        # run_pipeline should be called 3 times
        assert mock_pipeline.call_count == 3

        # batch_result.json should be created
        result_path = output_dir / "batch_result.json"
        assert result_path.exists()
        results = json.loads(result_path.read_text(encoding="utf-8"))
        assert results["batch_name"] == "test_batch"
        assert len(results["results"]) == 3
        assert all(r["status"] == "success" for r in results["results"])

    @pytest.mark.asyncio
    async def test_batch_partial_failure(self, topics_file: Path, tmp_path: Path):
        """一部トピック失敗時に他は続行"""
        output_dir = tmp_path / "batch_output"

        call_count = 0

        async def mock_pipeline(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("API error on topic 2")
            return Path("/fake/output.csv")

        with patch("scripts.research_cli.run_pipeline", side_effect=mock_pipeline):
            await run_batch(topics_file, output_dir=output_dir, interval=0)

        result_path = output_dir / "batch_result.json"
        results = json.loads(result_path.read_text(encoding="utf-8"))
        statuses = [r["status"] for r in results["results"]]
        assert statuses == ["success", "failed", "success"]

    @pytest.mark.asyncio
    async def test_batch_skips_empty_topics(self, topics_with_empty: Path, tmp_path: Path):
        """空トピックはスキップ"""
        output_dir = tmp_path / "batch_output"

        with patch("scripts.research_cli.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = Path("/fake/output.csv")
            await run_batch(topics_with_empty, output_dir=output_dir, interval=0)

        # Only 2 non-empty topics should be processed
        assert mock_pipeline.call_count == 2

        result_path = output_dir / "batch_result.json"
        results = json.loads(result_path.read_text(encoding="utf-8"))
        statuses = [r["status"] for r in results["results"]]
        assert statuses == ["success", "skipped", "success"]

    @pytest.mark.asyncio
    async def test_batch_merges_defaults(self, topics_file: Path, tmp_path: Path):
        """defaults と個別設定のマージ確認"""
        output_dir = tmp_path / "batch_output"
        calls = []

        async def capture_pipeline(**kwargs):
            calls.append(kwargs)
            return Path("/fake/output.csv")

        with patch("scripts.research_cli.run_pipeline", side_effect=capture_pipeline):
            await run_batch(topics_file, output_dir=output_dir, interval=0)

        # Topic B overrides style and duration
        assert calls[1]["style"] == "news"
        assert calls[1]["target_duration"] == 600

        # Topic A and C use defaults
        assert calls[0]["style"] == "default"
        assert calls[0]["target_duration"] == 300
        assert calls[2]["style"] == "default"

    @pytest.mark.asyncio
    async def test_batch_output_directory_structure(self, topics_file: Path, tmp_path: Path):
        """出力ディレクトリ構造の確認"""
        output_dir = tmp_path / "batch_output"

        with patch("scripts.research_cli.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = Path("/fake/output.csv")
            await run_batch(topics_file, output_dir=output_dir, interval=0)

        # Topic directories should exist
        assert (output_dir / "topic_01").exists()
        assert (output_dir / "topic_02").exists()
        assert (output_dir / "topic_03").exists()


class TestSampleTopicsFile:
    """samples/batch_topics_example.json の妥当性テスト"""

    SAMPLE_PATH = Path(__file__).resolve().parent.parent / "samples" / "batch_topics_example.json"

    def test_sample_exists(self):
        assert self.SAMPLE_PATH.exists()

    def test_sample_valid_json(self):
        with open(self.SAMPLE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_sample_has_required_fields(self):
        with open(self.SAMPLE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "topics" in data
        assert isinstance(data["topics"], list)
        assert len(data["topics"]) >= 1

    def test_sample_topics_have_topic_field(self):
        with open(self.SAMPLE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for t in data["topics"]:
            assert "topic" in t
            assert isinstance(t["topic"], str)
            assert len(t["topic"]) > 0
