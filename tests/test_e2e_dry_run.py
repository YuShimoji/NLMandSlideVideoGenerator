"""E2E Dry-Run 自動テスト (モックベース, APIキー不要)

scripts/e2e_dry_run.py の全ステージを検証する。
外部APIへのリクエストは全てモックする。
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# e2e_dry_run モジュールをインポート
import sys
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from e2e_dry_run import (
    run_e2e_dry_run,
    stage_collect_sources,
    stage_generate_script,
    stage_validate_segments,
    stage_collect_images,
    stage_assemble_csv,
    _mock_sources,
    _mock_script_bundle,
)


# ---------------------------------------------------------------------------
# Unit tests for mock data generators
# ---------------------------------------------------------------------------

class TestMockGenerators:
    def test_mock_sources(self):
        sources = _mock_sources("AI")
        assert len(sources) == 5
        assert all("url" in s for s in sources)
        assert all("title" in s for s in sources)
        assert sources[0]["relevance_score"] > sources[-1]["relevance_score"]

    def test_mock_script_bundle(self):
        bundle = _mock_script_bundle("AI", 10)
        assert bundle["title"]
        assert len(bundle["segments"]) == 10
        for seg in bundle["segments"]:
            assert "speaker" in seg
            assert "content" in seg
            assert "key_points" in seg

    def test_mock_script_bundle_single_segment(self):
        bundle = _mock_script_bundle("test", 1)
        assert len(bundle["segments"]) == 1


# ---------------------------------------------------------------------------
# Unit tests for individual stages
# ---------------------------------------------------------------------------

class TestStageCollectSources:
    @pytest.mark.asyncio
    async def test_mock_mode(self):
        sources = await stage_collect_sources("AI", None, mock=True)
        assert len(sources) == 5
        assert all(isinstance(s, dict) for s in sources)

    @pytest.mark.asyncio
    async def test_mock_mode_with_urls(self):
        sources = await stage_collect_sources("AI", ["https://example.com"], mock=True)
        assert len(sources) == 5  # mock ignores URLs


class TestStageGenerateScript:
    @pytest.mark.asyncio
    async def test_mock_mode(self):
        sources = _mock_sources("test")
        bundle = await stage_generate_script("test", sources, mock=True, target_segments=5)
        assert "segments" in bundle
        assert len(bundle["segments"]) == 5

    @pytest.mark.asyncio
    async def test_mock_mode_large(self):
        sources = _mock_sources("test")
        bundle = await stage_generate_script("test", sources, mock=True, target_segments=30)
        assert len(bundle["segments"]) == 30


class TestStageValidateSegments:
    def test_valid_segments(self):
        bundle = _mock_script_bundle("test", 10)
        result = stage_validate_segments(bundle, 200.0)
        assert result["is_ok"] is True
        assert result["segment_count"] == 10

    def test_empty_segments(self):
        result = stage_validate_segments({"segments": []}, 100.0)
        assert result["status"] == "skip"
        assert result["is_ok"] is True

    def test_no_segments_key(self):
        result = stage_validate_segments({"title": "test"}, 100.0)
        assert result["status"] == "skip"


class TestStageCollectImages:
    def test_collect_images_with_mock_api(self, tmp_path):
        """画像収集をモックAPIで検証"""
        segments = _mock_script_bundle("AI", 3)["segments"]

        # StockImageClient をモックして外部APIを呼ばない
        mock_image = MagicMock()
        mock_image.id = "mock_1"
        mock_image.source = "pexels"
        mock_image.url = "https://example.com/img.jpg"
        mock_image.photographer = "Test User"
        mock_image.local_path = tmp_path / "test.jpg"
        mock_image.width = 1920
        mock_image.height = 1080
        # ダミーファイル作成
        mock_image.local_path.write_bytes(b"fake image data")

        with patch(
            "core.visual.stock_image_client.StockImageClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.search_for_segments.return_value = [mock_image] * 3
            instance.get_attribution.return_value = "Photo by Test User on Pexels"

            records, credits = stage_collect_images(segments, tmp_path)

        assert len(records) == 3
        assert all(r["source"] == "pexels" for r in records)
        assert "Test User" in credits


class TestStageAssembleCsv:
    def test_assemble_csv(self, tmp_path):
        """CSV組立の基本検証"""
        segments = _mock_script_bundle("test", 3)["segments"]
        image_records = [
            {"local_path": str(tmp_path / f"img_{i}.jpg")}
            for i in range(3)
        ]
        # ダミー画像作成
        for rec in image_records:
            Path(rec["local_path"]).write_bytes(b"fake")

        csv_path = stage_assemble_csv(
            segments, tmp_path / "test.csv", image_records=image_records,
        )
        assert csv_path.exists()

        lines = csv_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3

    def test_assemble_csv_no_images(self, tmp_path):
        """画像なしでもCSV生成可能"""
        segments = _mock_script_bundle("test", 3)["segments"]
        image_records = [{"local_path": None} for _ in range(3)]

        csv_path = stage_assemble_csv(
            segments, tmp_path / "test.csv", image_records=image_records,
        )
        assert csv_path.exists()


# ---------------------------------------------------------------------------
# Integration test: full E2E pipeline (mock mode)
# ---------------------------------------------------------------------------

class TestE2EIntegration:
    @pytest.mark.asyncio
    async def test_full_mock_pipeline(self, tmp_path):
        """モックモードでE2Eパイプライン全体を検証"""
        # 画像収集もモックして外部API呼び出しを排除
        mock_image = MagicMock()
        mock_image.id = "mock_1"
        mock_image.source = "pexels"
        mock_image.url = "https://example.com"
        mock_image.photographer = "Mock"
        mock_image.local_path = None
        mock_image.width = 1920
        mock_image.height = 1080

        with patch(
            "core.visual.stock_image_client.StockImageClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.search_for_segments.return_value = [mock_image] * 5
            instance.get_attribution.return_value = ""

            output_dir = await run_e2e_dry_run(
                topic="Test Topic",
                mock=True,
                target_segments=5,
                output_base=tmp_path,
            )

        assert output_dir.exists()

        # 全成果物が生成されていること
        assert (output_dir / "manifest.json").exists()
        assert (output_dir / "sources.json").exists()
        assert (output_dir / "script_bundle.json").exists()
        assert (output_dir / "validation.json").exists()
        assert (output_dir / "images_metadata.json").exists()
        assert (output_dir / "timeline.csv").exists()

        # manifest の内容検証
        manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["topic"] == "Test Topic"
        assert manifest["mode"] == "mock"
        assert manifest["stages"]["sources"]["status"] == "ok"
        assert manifest["stages"]["script"]["status"] == "ok"
        assert manifest["stages"]["csv"]["status"] == "ok"
        assert manifest["stages"]["script"]["segment_count"] == 5

    @pytest.mark.asyncio
    async def test_pipeline_zero_segments(self, tmp_path):
        """0セグメントでもクラッシュしないこと"""
        with patch(
            "e2e_dry_run.stage_generate_script",
            return_value={"title": "empty", "segments": []},
        ):
            output_dir = await run_e2e_dry_run(
                topic="Empty",
                mock=True,
                target_segments=0,
                output_base=tmp_path,
            )

        manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["stages"]["csv"]["status"] == "skip"

    @pytest.mark.asyncio
    async def test_manifest_completeness(self, tmp_path):
        """manifestに必須フィールドが全て存在すること"""
        with patch("core.visual.stock_image_client.StockImageClient") as MockClient:
            instance = MockClient.return_value
            mock_img = MagicMock(
                id="m1", source="pexels", url="", photographer="",
                local_path=None, width=1920, height=1080,
            )
            instance.search_for_segments.return_value = [mock_img] * 3
            instance.get_attribution.return_value = ""

            output_dir = await run_e2e_dry_run(
                topic="Manifest Test",
                mock=True,
                target_segments=3,
                output_base=tmp_path,
            )

        manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        assert "topic" in manifest
        assert "mode" in manifest
        assert "started_at" in manifest
        assert "completed_at" in manifest
        assert "total_elapsed_s" in manifest
        assert set(manifest["stages"].keys()) == {
            "sources", "script", "validation", "images", "csv",
        }
