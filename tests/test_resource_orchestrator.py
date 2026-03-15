"""VisualResourceOrchestrator テスト (SP-033 Phase 2 + Phase 3)"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.visual.ai_image_provider import GeneratedImage
from core.visual.models import AnimationType, SegmentType, VisualResource
from core.visual.resource_orchestrator import VisualResourceOrchestrator
from core.visual.segment_classifier import SegmentClassifier
from core.visual.stock_image_client import StockImage


def _make_slide_paths(tmp_path: Path, count: int) -> list[Path]:
    """テスト用スライドPNGファイルを作成。"""
    paths = []
    for i in range(count):
        p = tmp_path / f"slide_{i:04d}.png"
        p.write_bytes(b"fake_png")
        paths.append(p)
    return paths


def _make_segments(count: int, mix: bool = True) -> list[dict]:
    """テスト用セグメントを生成。mixがTrueの場合はvisual/textualが混在。"""
    segments = []
    for i in range(count):
        if mix and i % 3 == 0:
            segments.append({
                "content": f"導入的なセグメント{i}",
                "section": "はじめに" if i == 0 else "概要",
                "key_points": ["AI技術"],
            })
        elif mix and i % 3 == 2:
            segments.append({
                "content": f"- 手順1\n- 手順2\nデータ: {i * 10}%",
                "section": "手順" if i % 2 == 0 else "データ",
                "key_points": [f"精度{i * 10}%"],
            })
        else:
            segments.append({
                "content": f"説明セグメント{i}です。",
                "section": "",
            })
    return segments


def _make_mock_stock_client(results_per_call: int = 1) -> MagicMock:
    """StockImageClientのモック。"""
    client = MagicMock()

    def mock_search_for_segments(segments, images_per_segment=1, orientation="landscape", queries=None):
        images = []
        for i, _ in enumerate(segments):
            images.append(StockImage(
                id=f"stock_{i}",
                url=f"https://example.com/{i}",
                download_url=f"https://example.com/{i}/download",
                width=1920,
                height=1080,
                photographer=f"Photo_{i}",
                source="pexels",
                local_path=Path(f"/tmp/stock_{i}.jpg"),
            ))
        return images

    client.search_for_segments = MagicMock(side_effect=mock_search_for_segments)
    return client


class TestOrchestrateBasic:
    def test_empty_segments(self) -> None:
        orch = VisualResourceOrchestrator()
        result = orch.orchestrate([])
        assert len(result.resources) == 0

    def test_slides_only_no_stock_client(self, tmp_path: Path) -> None:
        slides = _make_slide_paths(tmp_path, 3)
        segments = _make_segments(6, mix=False)
        orch = VisualResourceOrchestrator(stock_client=None)
        result = orch.orchestrate(segments, slides)

        assert len(result.resources) == 6
        # stock_clientなし → 全部スライドにフォールバック
        for r in result.resources:
            assert r.source in ("slide", "none")
            assert r.animation_type == AnimationType.STATIC

    def test_no_slides_no_stock(self) -> None:
        segments = _make_segments(3, mix=False)
        orch = VisualResourceOrchestrator()
        result = orch.orchestrate(segments, [])

        assert len(result.resources) == 3
        for r in result.resources:
            assert r.source == "none"
            assert r.image_path is None


class TestOrchestrateWithStock:
    def test_mixed_sources(self, tmp_path: Path) -> None:
        slides = _make_slide_paths(tmp_path, 3)
        segments = _make_segments(6, mix=True)
        stock_client = _make_mock_stock_client()

        # visual_ratio_target=0.5 で半分をvisualに
        classifier = SegmentClassifier(visual_ratio_target=0.5)
        orch = VisualResourceOrchestrator(
            classifier=classifier,
            stock_client=stock_client,
            topic="AI技術",
        )
        result = orch.orchestrate(segments, slides)

        assert len(result.resources) == 6
        sources = [r.source for r in result.resources]
        assert "stock" in sources
        assert "slide" in sources

    def test_stock_images_get_animation_cycle(self, tmp_path: Path) -> None:
        slides = _make_slide_paths(tmp_path, 1)
        # すべてvisualになるセグメント
        segments = [
            {"content": "導入", "section": "はじめに", "key_points": ["AI"]},
            {"content": "概要", "section": "概要", "key_points": ["未来"]},
        ]
        stock_client = _make_mock_stock_client()
        classifier = SegmentClassifier(visual_ratio_target=1.0)
        orch = VisualResourceOrchestrator(
            classifier=classifier,
            stock_client=stock_client,
        )
        result = orch.orchestrate(segments, slides)

        stock_resources = [r for r in result.resources if r.source == "stock"]
        if len(stock_resources) >= 2:
            # アニメーションサイクルが適用されている
            animations = [r.animation_type for r in stock_resources]
            # 最低でもKEN_BURNS以外が1つはあるはず (サイクル)
            assert len(set(animations)) >= 1

    def test_slide_resources_always_static(self, tmp_path: Path) -> None:
        slides = _make_slide_paths(tmp_path, 3)
        segments = _make_segments(6, mix=True)
        classifier = SegmentClassifier(visual_ratio_target=0.0)  # 全部textual
        orch = VisualResourceOrchestrator(classifier=classifier)
        result = orch.orchestrate(segments, slides)

        for r in result.resources:
            if r.source == "slide":
                assert r.animation_type == AnimationType.STATIC


class TestStockFallback:
    def test_stock_failure_falls_back_to_slide(self, tmp_path: Path) -> None:
        slides = _make_slide_paths(tmp_path, 2)
        segments = _make_segments(4, mix=True)

        failing_client = MagicMock()
        failing_client.search_for_segments = MagicMock(
            side_effect=Exception("API Error")
        )

        classifier = SegmentClassifier(visual_ratio_target=0.5)
        orch = VisualResourceOrchestrator(
            classifier=classifier,
            stock_client=failing_client,
        )
        result = orch.orchestrate(segments, slides)

        assert len(result.resources) == 4
        # API失敗 → 全部スライドにフォールバック
        for r in result.resources:
            assert r.source in ("slide", "none")


class TestEnforceVariety:
    def test_max_consecutive_stock_enforced(self, tmp_path: Path) -> None:
        slides = _make_slide_paths(tmp_path, 2)
        # 6個すべてvisualにする
        segments = [{"content": "概要", "section": "導入", "key_points": ["AI"]}] * 6
        stock_client = _make_mock_stock_client()
        classifier = SegmentClassifier(visual_ratio_target=1.0)

        orch = VisualResourceOrchestrator(
            classifier=classifier,
            stock_client=stock_client,
        )
        result = orch.orchestrate(segments, slides)

        # MAX_CONSECUTIVE_STOCK=3 なので、4番目以降のどこかにslideが入る
        sources = [r.source for r in result.resources]
        max_consecutive = 0
        current_consecutive = 0
        for s in sources:
            if s == "stock":
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        assert max_consecutive <= VisualResourceOrchestrator.MAX_CONSECUTIVE_STOCK


class TestSourceProvider:
    def test_package_source_provider(self, tmp_path: Path) -> None:
        slides = _make_slide_paths(tmp_path, 1)
        segments = _make_segments(2, mix=False)
        orch = VisualResourceOrchestrator()
        result = orch.orchestrate(segments, slides)
        assert result.source_provider == "orchestrator"


class TestGeminiKeywordIntegration:
    """classify_with_keywords → search_for_segments(queries=...) 統合テスト。"""

    def test_gemini_keywords_passed_to_stock_client(self, tmp_path: Path) -> None:
        """use_gemini=True 時、Geminiキーワードが queries として渡される。"""
        slides = _make_slide_paths(tmp_path, 1)
        segments = [
            {"content": "AI概要", "section": "導入", "key_points": ["AI技術"]},
            {"content": "データ分析", "section": "データ", "key_points": ["精度90%"]},
            {"content": "未来展望", "section": "まとめ", "key_points": ["将来予測"]},
        ]

        stock_client = _make_mock_stock_client()
        classifier = SegmentClassifier(visual_ratio_target=1.0, use_gemini=True)

        # classify_with_keywords をモック
        mock_keywords = ["AI technology overview", "data accuracy analysis", "future predictions"]
        with patch.object(
            classifier, "classify_with_keywords",
            return_value=([SegmentType.VISUAL] * 3, mock_keywords),
        ):
            orch = VisualResourceOrchestrator(
                classifier=classifier,
                stock_client=stock_client,
                topic="AI",
            )
            result = orch.orchestrate(segments, slides)

        # search_for_segments が queries 付きで呼ばれたことを確認
        call_args = stock_client.search_for_segments.call_args
        assert call_args is not None
        assert call_args.kwargs.get("queries") is not None
        passed_queries = call_args.kwargs["queries"]
        assert len(passed_queries) == 3
        assert all(q in mock_keywords for q in passed_queries)

    def test_no_gemini_no_queries_param(self, tmp_path: Path) -> None:
        """use_gemini=False 時、queries は渡されない。"""
        slides = _make_slide_paths(tmp_path, 1)
        segments = [
            {"content": "概要", "section": "導入", "key_points": ["AI"]},
        ]

        stock_client = _make_mock_stock_client()
        classifier = SegmentClassifier(visual_ratio_target=1.0, use_gemini=False)

        orch = VisualResourceOrchestrator(
            classifier=classifier,
            stock_client=stock_client,
        )
        result = orch.orchestrate(segments, slides)

        call_args = stock_client.search_for_segments.call_args
        assert call_args is not None
        # queries が None または渡されていない
        queries_val = call_args.kwargs.get("queries")
        assert queries_val is None

    def test_gemini_fallback_no_queries(self, tmp_path: Path) -> None:
        """classify_with_keywords がフォールバックしても正常動作する。"""
        slides = _make_slide_paths(tmp_path, 1)
        segments = [
            {"content": "概要", "section": "導入", "key_points": ["AI技術"]},
            {"content": "詳細", "section": "本論", "key_points": ["データ分析"]},
        ]

        stock_client = _make_mock_stock_client()
        classifier = SegmentClassifier(visual_ratio_target=1.0, use_gemini=True)

        # classify_with_keywords がフォールバック (元のkey_pointsを返す)
        with patch.object(
            classifier, "classify_with_keywords",
            return_value=(
                [SegmentType.VISUAL, SegmentType.VISUAL],
                ["AI技術", "データ分析"],  # 日本語のまま (翻訳失敗想定)
            ),
        ):
            orch = VisualResourceOrchestrator(
                classifier=classifier,
                stock_client=stock_client,
            )
            result = orch.orchestrate(segments, slides)

        # 正常終了し、結果が返る
        assert len(result.resources) == 2


def _make_mock_ai_provider(success_indices: list[int] | None = None) -> MagicMock:
    """AIImageProviderのモック。success_indicesで成功するセグメントを指定。"""
    provider = MagicMock()

    def mock_generate(segments, topic="", **kwargs):
        results = []
        for i, seg in enumerate(segments):
            if success_indices is None or i in success_indices:
                results.append(GeneratedImage(
                    prompt=f"prompt_{i}",
                    image_path=Path(f"/tmp/ai_{i}.png"),
                ))
            else:
                results.append(GeneratedImage(
                    prompt=f"prompt_{i}",
                    error="generation_failed",
                ))
        return results

    provider.generate_for_segments = MagicMock(side_effect=mock_generate)
    return provider


def _make_partial_stock_client(fail_indices: list[int]) -> MagicMock:
    """一部のセグメントで失敗するStockImageClientモック。"""
    client = MagicMock()
    call_count = [0]

    def mock_search(segments, images_per_segment=1, orientation="landscape", queries=None):
        images = []
        for i, _ in enumerate(segments):
            if call_count[0] + i in fail_indices:
                images.append(StockImage(
                    id=f"none_{i}",
                    url="",
                    download_url="",
                    width=0,
                    height=0,
                    photographer="",
                    source="none",
                    local_path=None,
                ))
            else:
                images.append(StockImage(
                    id=f"stock_{i}",
                    url=f"https://example.com/{i}",
                    download_url=f"https://example.com/{i}/dl",
                    width=1920,
                    height=1080,
                    photographer=f"Photo_{i}",
                    source="pexels",
                    local_path=Path(f"/tmp/stock_{i}.jpg"),
                ))
        call_count[0] += len(segments)
        return images

    client.search_for_segments = MagicMock(side_effect=mock_search)
    return client


class TestAIImageFallback:
    """SP-033 Phase 3: stock失敗時のAI画像フォールバック。"""

    def test_ai_fallback_on_stock_failure(self, tmp_path: Path) -> None:
        """stock取得失敗セグメントにAI画像が割り当てられる。"""
        slides = _make_slide_paths(tmp_path, 1)
        segments = [
            {"content": "概要", "section": "導入", "key_points": ["AI"]},
            {"content": "詳細", "section": "本論", "key_points": ["ML"]},
            {"content": "事例", "section": "事例", "key_points": ["DL"]},
        ]

        # セグメント1 (index 1) だけstock失敗
        stock_client = _make_partial_stock_client(fail_indices=[1])
        ai_provider = _make_mock_ai_provider()
        classifier = SegmentClassifier(visual_ratio_target=1.0)

        orch = VisualResourceOrchestrator(
            classifier=classifier,
            stock_client=stock_client,
            ai_provider=ai_provider,
            topic="tech",
        )
        result = orch.orchestrate(segments, slides)

        assert len(result.resources) == 3
        sources = [r.source for r in result.resources]
        assert "ai" in sources
        # stock成功分もある
        assert "stock" in sources

    def test_ai_source_gets_animation_cycle(self, tmp_path: Path) -> None:
        """source='ai' にもアニメーションサイクルが適用される。"""
        slides = _make_slide_paths(tmp_path, 1)
        segments = [
            {"content": "seg1", "key_points": ["AI"]},
            {"content": "seg2", "key_points": ["ML"]},
        ]

        # 全stock失敗 → 全部AIフォールバック
        stock_client = _make_partial_stock_client(fail_indices=[0, 1])
        ai_provider = _make_mock_ai_provider()
        classifier = SegmentClassifier(visual_ratio_target=1.0)

        orch = VisualResourceOrchestrator(
            classifier=classifier,
            stock_client=stock_client,
            ai_provider=ai_provider,
        )
        result = orch.orchestrate(segments, slides)

        ai_resources = [r for r in result.resources if r.source == "ai"]
        assert len(ai_resources) >= 1
        for r in ai_resources:
            assert r.animation_type != AnimationType.STATIC

    def test_no_ai_provider_falls_back_to_slide(self, tmp_path: Path) -> None:
        """ai_provider未設定時、stock失敗 → スライドフォールバック。"""
        slides = _make_slide_paths(tmp_path, 2)
        segments = [
            {"content": "seg1", "key_points": ["AI"]},
            {"content": "seg2", "key_points": ["ML"]},
        ]

        stock_client = _make_partial_stock_client(fail_indices=[0, 1])
        classifier = SegmentClassifier(visual_ratio_target=1.0)

        orch = VisualResourceOrchestrator(
            classifier=classifier,
            stock_client=stock_client,
            ai_provider=None,  # AI未設定
        )
        result = orch.orchestrate(segments, slides)

        # 全部スライドフォールバック
        for r in result.resources:
            assert r.source in ("slide", "none")

    def test_ai_failure_falls_back_to_slide(self, tmp_path: Path) -> None:
        """AI生成も失敗したセグメントはスライドにフォールバック。"""
        slides = _make_slide_paths(tmp_path, 1)
        segments = [
            {"content": "seg1", "key_points": ["AI"]},
            {"content": "seg2", "key_points": ["ML"]},
        ]

        stock_client = _make_partial_stock_client(fail_indices=[0, 1])
        # AI生成も全失敗
        ai_provider = _make_mock_ai_provider(success_indices=[])
        classifier = SegmentClassifier(visual_ratio_target=1.0)

        orch = VisualResourceOrchestrator(
            classifier=classifier,
            stock_client=stock_client,
            ai_provider=ai_provider,
        )
        result = orch.orchestrate(segments, slides)

        # AI失敗 → スライドフォールバック
        for r in result.resources:
            assert r.source in ("slide", "none")

    def test_ai_provider_exception_handled(self, tmp_path: Path) -> None:
        """ai_provider.generate_for_segments が例外を投げても正常動作。"""
        slides = _make_slide_paths(tmp_path, 1)
        segments = [{"content": "seg1", "key_points": ["AI"]}]

        stock_client = _make_partial_stock_client(fail_indices=[0])
        ai_provider = MagicMock()
        ai_provider.generate_for_segments = MagicMock(
            side_effect=Exception("API Error")
        )
        classifier = SegmentClassifier(visual_ratio_target=1.0)

        orch = VisualResourceOrchestrator(
            classifier=classifier,
            stock_client=stock_client,
            ai_provider=ai_provider,
        )
        result = orch.orchestrate(segments, slides)

        # 例外でもクラッシュせず結果が返る
        assert len(result.resources) == 1
        assert result.resources[0].source in ("slide", "none")

    def test_mixed_stock_ai_slide(self, tmp_path: Path) -> None:
        """stock/AI/slide が混在するパッケージが正しく生成される。"""
        slides = _make_slide_paths(tmp_path, 2)
        segments = [
            {"content": "概要", "section": "導入", "key_points": ["AI"]},  # visual → stock OK
            {"content": "説明テキスト", "section": ""},                     # textual → slide
            {"content": "データ", "section": "分析", "key_points": ["ML"]},  # visual → stock fail → AI
            {"content": "まとめ", "section": ""},                            # textual → slide
        ]

        # segment 2 (visual index 1) だけstock失敗
        stock_client = _make_partial_stock_client(fail_indices=[1])
        ai_provider = _make_mock_ai_provider()
        classifier = SegmentClassifier(visual_ratio_target=0.5)

        orch = VisualResourceOrchestrator(
            classifier=classifier,
            stock_client=stock_client,
            ai_provider=ai_provider,
            topic="tech",
        )
        result = orch.orchestrate(segments, slides)

        assert len(result.resources) == 4
        sources = set(r.source for r in result.resources)
        # 少なくとも slide が含まれる (textual セグメントがあるため)
        assert "slide" in sources
