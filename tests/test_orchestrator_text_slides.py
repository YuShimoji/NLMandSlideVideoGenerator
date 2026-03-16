"""Orchestrator + TextSlideGenerator 統合テスト (SP-033 Phase 3)

work_dir 指定時に source="none" セグメントがテキストスライドに置換されることを検証。
"""
from pathlib import Path

import pytest

from core.visual.models import AnimationType, SegmentType, VisualResource
from core.visual.resource_orchestrator import VisualResourceOrchestrator
from core.visual.segment_classifier import SegmentClassifier


def _make_segments(n: int) -> list[dict]:
    """テスト用セグメント群を生成する。"""
    segments = []
    for i in range(n):
        segments.append({
            "section": f"Section {i+1}",
            "content": f"Content for segment {i+1} about topic details.",
            "key_points": [f"Point {i+1}a", f"Point {i+1}b"],
            "speaker": "Host1" if i % 2 == 0 else "Host2",
        })
    return segments


class TestOrchestratorFillNone:
    """work_dir設定時にsource=noneがgenerated textスライドに置換される。"""

    def test_no_slides_no_stock_fills_with_generated(self, tmp_path: Path) -> None:
        """スライドもストック画像もない場合、全セグメントがgenerated。"""
        orchestrator = VisualResourceOrchestrator(
            classifier=SegmentClassifier(threshold=0.5),
            stock_client=None,
            topic="テスト",
            work_dir=tmp_path,
        )
        segments = _make_segments(5)
        package = orchestrator.orchestrate(segments, slide_image_paths=[])

        assert len(package.resources) == 5
        for r in package.resources:
            assert r.source == "generated", f"Expected generated, got {r.source}"
            assert r.image_path is not None
            assert r.image_path.exists()
            assert r.animation_type == AnimationType.STATIC

    def test_generated_slides_saved_in_work_dir(self, tmp_path: Path) -> None:
        """生成されたスライドが work_dir/generated_slides/ に保存される。"""
        orchestrator = VisualResourceOrchestrator(
            classifier=SegmentClassifier(threshold=0.5),
            stock_client=None,
            topic="AI",
            work_dir=tmp_path,
        )
        segments = _make_segments(3)
        orchestrator.orchestrate(segments, slide_image_paths=[])

        gen_dir = tmp_path / "generated_slides"
        assert gen_dir.exists()
        pngs = list(gen_dir.glob("*.png"))
        assert len(pngs) == 3

    def test_with_slides_no_none_segments(self, tmp_path: Path) -> None:
        """既存スライドが十分ある場合、テキストスライド生成は不要。"""
        # ダミースライドPNG作成
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        slide_paths = []
        for i in range(5):
            p = slides_dir / f"slide_{i}.png"
            from PIL import Image
            img = Image.new("RGB", (1920, 1080), (100, 100, 100))
            img.save(str(p))
            slide_paths.append(p)

        orchestrator = VisualResourceOrchestrator(
            classifier=SegmentClassifier(threshold=0.5),
            stock_client=None,
            topic="テスト",
            work_dir=tmp_path,
        )
        segments = _make_segments(5)
        package = orchestrator.orchestrate(segments, slide_image_paths=slide_paths)

        # スライドがあるので none はゼロ、generated もゼロ
        none_count = sum(1 for r in package.resources if r.source == "none")
        assert none_count == 0

    def test_without_work_dir_none_remains(self, tmp_path: Path) -> None:
        """work_dir未指定では source=none が残る。"""
        orchestrator = VisualResourceOrchestrator(
            classifier=SegmentClassifier(threshold=0.5),
            stock_client=None,
            topic="テスト",
            work_dir=None,  # work_dir未指定
        )
        segments = _make_segments(3)
        package = orchestrator.orchestrate(segments, slide_image_paths=[])

        none_count = sum(1 for r in package.resources if r.source == "none")
        assert none_count > 0

    def test_slides_available_cycles_no_none(self, tmp_path: Path) -> None:
        """スライドが少数でもある場合、サイクルして全セグメントをカバー（noneゼロ）。"""
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        from PIL import Image

        # 2枚だけスライド
        slide_paths = []
        for i in range(2):
            p = slides_dir / f"slide_{i}.png"
            img = Image.new("RGB", (1920, 1080), (100, 100, 100))
            img.save(str(p))
            slide_paths.append(p)

        orchestrator = VisualResourceOrchestrator(
            classifier=SegmentClassifier(threshold=0.5),
            stock_client=None,
            topic="テスト",
            work_dir=tmp_path,
        )
        segments = _make_segments(10)
        package = orchestrator.orchestrate(segments, slide_image_paths=slide_paths)

        assert len(package.resources) == 10
        none_count = sum(1 for r in package.resources if r.source == "none")
        assert none_count == 0
        # スライドが存在する場合はサイクルで全カバー (generated不要)
        slide_count = sum(1 for r in package.resources if r.source == "slide")
        assert slide_count == 10

    def test_large_segment_count_all_generated(self, tmp_path: Path) -> None:
        """90セグメント、スライドなし → 全90がgenerated。30分動画シナリオ。"""
        orchestrator = VisualResourceOrchestrator(
            classifier=SegmentClassifier(threshold=0.5),
            stock_client=None,
            topic="量子コンピュータの最新動向",
            work_dir=tmp_path,
        )
        segments = _make_segments(90)
        package = orchestrator.orchestrate(segments, slide_image_paths=[])

        assert len(package.resources) == 90
        none_count = sum(1 for r in package.resources if r.source == "none")
        gen_count = sum(1 for r in package.resources if r.source == "generated")
        assert none_count == 0
        assert gen_count == 90
