"""セグメント分類器 (SP-033 Phase 2/2c)

台本セグメントを「visual (ストック画像候補)」と「textual (テキストスライド維持)」に分類する。

方式:
1. ヒューリスティクス (デフォルト): ルールベースのスコアリング
2. Gemini (オプション): LLMによる分類 + 英語キーワード抽出の一括処理
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

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
        use_gemini: bool = False,
    ) -> None:
        """
        Args:
            threshold: visual判定の閾値。
            visual_ratio_target: 全体に占めるvisualセグメントの目標比率 (0.0~1.0)。
                指定時、分類後にスコア順で調整して目標比率に近づける。
                None の場合は閾値のみで判定。
            use_gemini: True で Gemini API による分類を試行。失敗時はヒューリスティクスにフォールバック。
        """
        self.threshold = threshold
        self.visual_ratio_target = visual_ratio_target
        self.use_gemini = use_gemini

    def classify(self, segments: List[Dict[str, Any]]) -> List[SegmentType]:
        """セグメント群を分類する。

        Args:
            segments: 台本セグメント群。各要素に content/text, section, key_points を期待。

        Returns:
            各セグメントの分類結果。
        """
        if not segments:
            return []

        # Gemini分類を試行
        if self.use_gemini:
            gemini_result = self._classify_with_gemini(segments)
            if gemini_result is not None:
                types = gemini_result
                # 目標比率調整はGemini結果にも適用
                if self.visual_ratio_target is not None:
                    scores = [self._score_segment(seg, i, len(segments)) for i, seg in enumerate(segments)]
                    types = self._adjust_to_target(scores, types)
                return types

        # ヒューリスティクスフォールバック
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

    def classify_with_keywords(
        self, segments: List[Dict[str, Any]], topic: str = ""
    ) -> Tuple[List[SegmentType], List[str]]:
        """分類と英語キーワード抽出を同時に行う。

        Gemini APIを使用。失敗時はヒューリスティクス分類 + 元のkey_pointsを返す。

        Args:
            segments: 台本セグメント群。
            topic: トピック名 (キーワード生成のコンテキスト用)。

        Returns:
            (分類結果リスト, 英語キーワードリスト) のタプル。
            キーワードリストはセグメントと同じ長さ。
        """
        types = self.classify(segments)

        # Geminiでキーワード抽出を試行
        keywords = self._extract_keywords_with_gemini(segments, topic)
        if keywords is None:
            # フォールバック: key_pointsをそのまま使用
            keywords = []
            for seg in segments:
                kps = seg.get("key_points", [])
                keywords.append(" ".join(kps[:2]) if kps else "")

        return types, keywords

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

    def _classify_with_gemini(
        self, segments: List[Dict[str, Any]]
    ) -> Optional[List[SegmentType]]:
        """Gemini APIでセグメントを分類する。

        Returns:
            分類結果リスト。API失敗時はNone (ヒューリスティクスにフォールバック)。
        """
        from config.settings import settings

        api_key = os.getenv("GEMINI_API_KEY", "") or settings.GEMINI_API_KEY
        if not api_key:
            return None

        try:
            from google import genai
            client = genai.Client(api_key=api_key)

            # セグメント要約を作成 (トークン節約)
            summaries = []
            for i, seg in enumerate(segments):
                content = seg.get("content", "") or seg.get("text", "")
                section = seg.get("section", "")
                kps = seg.get("key_points", [])
                summary = f"{i+1}. [{section}] {content[:80]} (kp: {', '.join(str(k) for k in kps[:2])})"
                summaries.append(summary)

            # バッチサイズ制限 (トークン上限対策)
            batch = "\n".join(summaries[:120])

            prompt = (
                "Classify each segment as 'visual' or 'textual' for a video production pipeline.\n"
                "- 'visual': narrative, conceptual, introduction, conclusion → show stock photo\n"
                "- 'textual': data-heavy, lists, procedures, technical details → show text slide\n\n"
                "Output ONLY one word per line: 'visual' or 'textual', matching the input numbering.\n\n"
                f"{batch}"
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            raw_text = response.text or ""
            text = raw_text.strip()

            types: List[SegmentType] = []
            for line in text.split("\n"):
                cleaned = re.sub(r"^\d+[.)]\s*", "", line.strip()).lower()
                if "visual" in cleaned:
                    types.append(SegmentType.VISUAL)
                elif "textual" in cleaned or "text" in cleaned:
                    types.append(SegmentType.TEXTUAL)

            # 件数が合わない場合はフォールバック
            if len(types) != len(segments):
                return None

            return types

        except Exception:
            return None

    def _extract_keywords_with_gemini(
        self, segments: List[Dict[str, Any]], topic: str = ""
    ) -> Optional[List[str]]:
        """Gemini APIで各セグメントの英語検索キーワードを抽出する。

        Returns:
            英語キーワードリスト (セグメントと同じ長さ)。失敗時はNone。
        """
        from config.settings import settings

        api_key = os.getenv("GEMINI_API_KEY", "") or settings.GEMINI_API_KEY
        if not api_key:
            return None

        try:
            from google import genai
            client = genai.Client(api_key=api_key)

            summaries = []
            for i, seg in enumerate(segments):
                content = seg.get("content", "") or seg.get("text", "")
                section = seg.get("section", "")
                summary = f"{i+1}. [{section}] {content[:80]}"
                summaries.append(summary)

            batch = "\n".join(summaries[:120])
            topic_ctx = f" Topic: {topic}." if topic else ""

            prompt = (
                f"For each segment below, provide 2-3 English keywords for stock photo search.{topic_ctx}\n"
                "Output ONLY keywords per line, numbered to match. No explanations.\n\n"
                f"{batch}"
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            raw_text = response.text or ""
            text = raw_text.strip()

            keywords: List[str] = []
            for line in text.split("\n"):
                cleaned = re.sub(r"^\d+[.)]\s*", "", line.strip())
                if cleaned:
                    keywords.append(cleaned)

            if len(keywords) != len(segments):
                return None

            return keywords

        except Exception:
            return None
