"""セグメント分類器 (SP-033 Phase 2)

台本セグメントを「visual (ストック画像候補)」と「textual (テキストスライド維持)」に
ヒューリスティクスで自動分類する。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .models import SegmentType


# textual傾向を示すキーワード (section名・content内)
_TEXTUAL_SECTION_KEYWORDS = {
    "手順", "ステップ", "比較", "データ", "数値", "一覧", "表",
    "リスト", "仕様", "設定", "コード", "実装", "技術",
    "step", "comparison", "data", "list", "spec", "code",
}

# visual傾向を示すキーワード (section名)
_VISUAL_SECTION_KEYWORDS = {
    "導入", "はじめに", "背景", "まとめ", "結論", "展望", "概要",
    "物語", "イメージ", "ビジョン", "歴史", "将来",
    "intro", "introduction", "background", "summary", "conclusion",
    "overview", "vision", "history", "future",
}

# 数値・記号パターン
_NUMERIC_PATTERN = re.compile(r"\d+[.,%]|\d+/\d+|\d{2,}")
# リスト構造パターン (箇条書き、番号付き)
_LIST_PATTERN = re.compile(r"^[\s]*[-・•※▶]\s|^\s*\d+[.)]\s", re.MULTILINE)


class SegmentClassifier:
    """セグメントをvisual/textualに分類する。

    スコアリング方式: 0.0 (完全textual) ~ 1.0 (完全visual)
    threshold (デフォルト0.5) 以上で visual 判定。
    """

    def __init__(
        self,
        threshold: float = 0.5,
        visual_ratio_target: Optional[float] = None,
    ) -> None:
        """
        Args:
            threshold: visual判定の閾値。
            visual_ratio_target: 全体に占めるvisualセグメントの目標比率 (0.0~1.0)。
                指定時、分類後にスコア順で調整して目標比率に近づける。
                None の場合は閾値のみで判定。
        """
        self.threshold = threshold
        self.visual_ratio_target = visual_ratio_target

    def classify(self, segments: List[Dict[str, Any]]) -> List[SegmentType]:
        """セグメント群を分類する。

        Args:
            segments: 台本セグメント群。各要素に content/text, section, key_points を期待。

        Returns:
            各セグメントの分類結果。
        """
        if not segments:
            return []

        scores = [self._score_segment(seg, i, len(segments)) for i, seg in enumerate(segments)]

        # 閾値ベースの初期分類
        types = [
            SegmentType.VISUAL if s >= self.threshold else SegmentType.TEXTUAL
            for s in scores
        ]

        # 目標比率調整
        if self.visual_ratio_target is not None and len(segments) > 0:
            types = self._adjust_to_target(scores, types)

        return types

    def _score_segment(
        self, segment: Dict[str, Any], index: int, total: int
    ) -> float:
        """セグメントのvisualスコアを算出 (0.0~1.0)。"""
        score = 0.5  # 中立スタート
        content = segment.get("content", "") or segment.get("text", "")
        section = segment.get("section", "")
        key_points = segment.get("key_points", [])

        # --- section名による判定 ---
        section_lower = section.lower()
        for kw in _VISUAL_SECTION_KEYWORDS:
            if kw in section_lower:
                score += 0.2
                break
        for kw in _TEXTUAL_SECTION_KEYWORDS:
            if kw in section_lower:
                score -= 0.2
                break

        # --- セグメント位置 ---
        # 冒頭と末尾は導入/まとめ → visual傾向
        if total > 3:
            relative_pos = index / max(total - 1, 1)
            if relative_pos < 0.1 or relative_pos > 0.9:
                score += 0.1
            elif 0.3 < relative_pos < 0.7:
                score -= 0.05  # 中盤は詳細説明が多い

        # --- 数値・記号密度 ---
        if content:
            numeric_matches = len(_NUMERIC_PATTERN.findall(content))
            char_count = max(len(content), 1)
            numeric_density = numeric_matches / (char_count / 50)  # 50文字あたりの数値出現数
            if numeric_density > 0.5:
                score -= 0.15
            elif numeric_density > 0.2:
                score -= 0.08

        # --- リスト構造 ---
        if content and _LIST_PATTERN.search(content):
            score -= 0.15

        # --- contentの長さ ---
        if content:
            if len(content) > 200:
                score -= 0.08  # 長い → 詳細説明 → textual傾向
            elif len(content) < 60:
                score += 0.05  # 短い → 概念的 → visual傾向

        # --- key_points の抽象度 ---
        if key_points:
            abstract_count = 0
            for kp in key_points:
                # 数値を含まないkey_pointは抽象的
                if not _NUMERIC_PATTERN.search(str(kp)):
                    abstract_count += 1
            if abstract_count == len(key_points):
                score += 0.08
            elif abstract_count == 0:
                score -= 0.08

        return max(0.0, min(1.0, score))

    def _adjust_to_target(
        self,
        scores: List[float],
        types: List[SegmentType],
    ) -> List[SegmentType]:
        """目標比率に近づくよう分類を調整する。"""
        assert self.visual_ratio_target is not None
        total = len(types)
        target_visual_count = round(total * self.visual_ratio_target)
        current_visual_count = sum(1 for t in types if t == SegmentType.VISUAL)

        if current_visual_count == target_visual_count:
            return types

        result = list(types)
        indexed_scores = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

        if current_visual_count < target_visual_count:
            # visualが足りない → スコアが高いtextualをvisualに変更
            needed = target_visual_count - current_visual_count
            for idx, _ in indexed_scores:
                if needed <= 0:
                    break
                if result[idx] == SegmentType.TEXTUAL:
                    result[idx] = SegmentType.VISUAL
                    needed -= 1
        else:
            # visualが多すぎる → スコアが低いvisualをtextualに変更
            excess = current_visual_count - target_visual_count
            for idx, _ in reversed(indexed_scores):
                if excess <= 0:
                    break
                if result[idx] == SegmentType.VISUAL:
                    result[idx] = SegmentType.TEXTUAL
                    excess -= 1

        return result
