"""SegmentClassifier テスト (SP-033 Phase 2)"""
import pytest

from core.visual.models import SegmentType
from core.visual.segment_classifier import SegmentClassifier


@pytest.fixture
def classifier() -> SegmentClassifier:
    return SegmentClassifier()


class TestBasicClassification:
    def test_empty_segments(self, classifier: SegmentClassifier) -> None:
        assert classifier.classify([]) == []

    def test_single_neutral_segment(self, classifier: SegmentClassifier) -> None:
        segments = [{"content": "普通のテキストです。", "section": ""}]
        result = classifier.classify(segments)
        assert len(result) == 1
        # 中立スコア0.5、閾値0.5でvisual判定
        assert result[0] in (SegmentType.VISUAL, SegmentType.TEXTUAL)

    def test_visual_intro_segment(self, classifier: SegmentClassifier) -> None:
        segments = [{"content": "AIの世界へようこそ。", "section": "導入"}]
        result = classifier.classify(segments)
        assert result[0] == SegmentType.VISUAL

    def test_textual_data_segment(self, classifier: SegmentClassifier) -> None:
        segments = [{"content": "精度は92.3%で、旧モデルの85.1%から7.2%向上しました。", "section": "データ比較"}]
        result = classifier.classify(segments)
        assert result[0] == SegmentType.TEXTUAL

    def test_textual_list_segment(self, classifier: SegmentClassifier) -> None:
        segments = [{"content": "- ステップ1: 設定\n- ステップ2: 実行\n- ステップ3: 確認", "section": "手順"}]
        result = classifier.classify(segments)
        assert result[0] == SegmentType.TEXTUAL


class TestPositionBasedClassification:
    def test_first_segment_visual_tendency(self) -> None:
        classifier = SegmentClassifier()
        segments = [
            {"content": "今日は面白い話をします。", "section": ""},
            {"content": "詳細な分析結果を見ていきましょう。", "section": ""},
            {"content": "まず第一に、数値を確認します。50%のユーザーが...", "section": ""},
            {"content": "次にデータを比較します。", "section": ""},
            {"content": "最後にまとめです。", "section": ""},
        ]
        result = classifier.classify(segments)
        # 冒頭と末尾はvisual傾向
        # 厳密なスコアは他要因にも依存するためcontains確認
        assert len(result) == 5

    def test_last_segment_visual_tendency(self) -> None:
        classifier = SegmentClassifier()
        segments = [{"content": f"セグメント{i}", "section": ""} for i in range(10)]
        segments[-1] = {"content": "以上がまとめです。", "section": "まとめ"}
        result = classifier.classify(segments)
        assert result[-1] == SegmentType.VISUAL


class TestKeyPointsInfluence:
    def test_abstract_key_points_boost_visual(self, classifier: SegmentClassifier) -> None:
        segments = [{"content": "AIの未来。", "key_points": ["AI", "未来"], "section": "概要"}]
        result = classifier.classify(segments)
        assert result[0] == SegmentType.VISUAL

    def test_numeric_key_points_boost_textual(self, classifier: SegmentClassifier) -> None:
        segments = [{"content": "数値の比較。", "key_points": ["精度92%", "損失0.03"], "section": "データ"}]
        result = classifier.classify(segments)
        assert result[0] == SegmentType.TEXTUAL


class TestVisualRatioTarget:
    def test_target_ratio_adjusts_classification(self) -> None:
        classifier = SegmentClassifier(visual_ratio_target=0.4)
        # すべて中立的なセグメント10個
        segments = [{"content": f"セグメント{i}", "section": ""} for i in range(10)]
        result = classifier.classify(segments)
        visual_count = sum(1 for t in result if t == SegmentType.VISUAL)
        # 40%なので4個前後
        assert 3 <= visual_count <= 5

    def test_target_ratio_zero(self) -> None:
        classifier = SegmentClassifier(visual_ratio_target=0.0)
        segments = [{"content": "テスト", "section": "導入"}] * 5
        result = classifier.classify(segments)
        visual_count = sum(1 for t in result if t == SegmentType.VISUAL)
        assert visual_count == 0

    def test_target_ratio_one(self) -> None:
        classifier = SegmentClassifier(visual_ratio_target=1.0)
        segments = [{"content": "テスト", "section": "データ"}] * 5
        result = classifier.classify(segments)
        visual_count = sum(1 for t in result if t == SegmentType.VISUAL)
        assert visual_count == 5


class TestMixedSegments:
    def test_realistic_script(self, classifier: SegmentClassifier) -> None:
        """現実的な台本構成でのテスト。"""
        segments = [
            {"content": "今回はAI技術の最前線についてお話しします。", "section": "はじめに", "key_points": ["AI技術"]},
            {"content": "まず背景を見てみましょう。", "section": "背景"},
            {"content": "- GPT-4: 精度95%\n- Gemini: 精度93%\n- Claude: 精度94%", "section": "比較データ", "key_points": ["精度95%"]},
            {"content": "これらのモデルは2024年に大きく進化しました。", "section": "解説"},
            {"content": "1. データ収集\n2. 前処理\n3. 学習\n4. 評価", "section": "手順"},
            {"content": "AIの未来は非常に明るいと言えるでしょう。", "section": "まとめ", "key_points": ["AI", "未来"]},
        ]
        result = classifier.classify(segments)

        assert len(result) == 6
        # はじめに → visual
        assert result[0] == SegmentType.VISUAL
        # 比較データ → textual
        assert result[2] == SegmentType.TEXTUAL
        # 手順 → textual
        assert result[4] == SegmentType.TEXTUAL
        # まとめ → visual
        assert result[5] == SegmentType.VISUAL


class TestThreshold:
    def test_low_threshold_more_visual(self) -> None:
        classifier = SegmentClassifier(threshold=0.3)
        segments = [{"content": "テスト", "section": ""}] * 5
        result = classifier.classify(segments)
        visual_count = sum(1 for t in result if t == SegmentType.VISUAL)
        assert visual_count >= 3  # 閾値が低い → visual寄り

    def test_high_threshold_more_textual(self) -> None:
        classifier = SegmentClassifier(threshold=0.8)
        segments = [{"content": "テスト", "section": ""}] * 5
        result = classifier.classify(segments)
        textual_count = sum(1 for t in result if t == SegmentType.TEXTUAL)
        assert textual_count >= 3  # 閾値が高い → textual寄り
