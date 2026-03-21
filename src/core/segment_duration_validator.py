"""セグメント粒度制御 (SP-044)

台本生成後にセグメント数・推定尺を検証し、過不足を検出・自動調整する。
Phase 1: 検証 + 警告
Phase 2: LLM経由の自動調整 (追加/統合)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.utils.logger import logger


# セグメント数の目安テーブル (target_seconds → (min, recommended_min, recommended_max, max))
# 15-25秒/セグメント基準 (YouTube解説の視覚変化テンポに合わせて短縮)
_SEGMENT_TABLE: List[Tuple[float, int, int, int, int]] = [
    (300, 8, 12, 20, 30),
    (900, 25, 36, 60, 80),
    (1800, 50, 72, 120, 160),
    (3600, 100, 144, 240, 320),
]

# ゆっくりボイスの読み上げ速度 (文字/秒)
_JA_CHARS_PER_SEC = 4.0
# 英語の読み上げ速度 (単語/秒)
_EN_WORDS_PER_SEC = 2.5
# 1セグメントあたりのパディング (秒)
_SEGMENT_PADDING = 0.5


@dataclass
class SegmentValidationResult:
    """検証結果。"""
    status: str  # "ok" | "too_short" | "too_long" | "too_few" | "too_many"
    segment_count: int
    estimated_duration: float
    target_duration: float
    ratio: float
    expected_min: int
    expected_max: int
    suggestion: str  # "" | "add_segments" | "trim_segments" | "merge_segments"
    message: str = ""

    @property
    def is_ok(self) -> bool:
        return self.status == "ok"


def estimate_segment_duration(segment: Dict[str, object]) -> float:
    """1セグメントの推定読み上げ時間(秒)を算出する。"""
    text = str(segment.get("content", "") or segment.get("text", "") or "")
    if not text:
        return 3.0  # デフォルト

    # 日本語文字数 (CJK統合漢字 + ひらがな + カタカナ + 全角記号)
    ja_chars = sum(1 for c in text if _is_ja_char(c))

    # 英語単語数 (日本語文字を除いた残りの単語数)
    ascii_part = "".join(c if not _is_ja_char(c) else " " for c in text)
    en_words = len([w for w in ascii_part.split() if w.strip()])

    duration = ja_chars / _JA_CHARS_PER_SEC + en_words / _EN_WORDS_PER_SEC
    return max(duration, 1.0) + _SEGMENT_PADDING


def _is_ja_char(c: str) -> bool:
    """日本語文字かどうか。"""
    cp = ord(c)
    return (
        0x3000 <= cp <= 0x303F  # 句読点
        or 0x3040 <= cp <= 0x309F  # ひらがな
        or 0x30A0 <= cp <= 0x30FF  # カタカナ
        or 0x4E00 <= cp <= 0x9FFF  # CJK統合漢字
        or 0xFF00 <= cp <= 0xFFEF  # 全角英数
    )


def _get_segment_range(target_duration: float) -> Tuple[int, int]:
    """target_durationに対する(min, max)セグメント数を返す。"""
    if target_duration <= 0:
        return (1, 10)

    # テーブル内の最も近いエントリを補間
    for i, (threshold, seg_min, _, _, seg_max) in enumerate(_SEGMENT_TABLE):
        if target_duration <= threshold:
            if i == 0:
                # テーブルの最小エントリ以下
                scale = target_duration / threshold
                return (max(1, int(seg_min * scale)), max(2, int(seg_max * scale)))
            # 前エントリとの線形補間
            prev_t, prev_min, _, _, prev_max = _SEGMENT_TABLE[i - 1]
            frac = (target_duration - prev_t) / (threshold - prev_t)
            interp_min = int(prev_min + frac * (seg_min - prev_min))
            interp_max = int(prev_max + frac * (seg_max - prev_max))
            return (max(1, interp_min), max(2, interp_max))

    # テーブルの最大エントリ以上
    last_t, last_min, _, _, last_max = _SEGMENT_TABLE[-1]
    scale = target_duration / last_t
    return (max(1, int(last_min * scale)), int(last_max * scale))


def validate_segments(
    segments: List[Dict[str, object]],
    target_duration: float,
) -> SegmentValidationResult:
    """セグメント群を検証する。

    Args:
        segments: 台本セグメント群。
        target_duration: 目標動画尺(秒)。

    Returns:
        SegmentValidationResult: 検証結果。
    """
    seg_count = len(segments)
    estimated = sum(estimate_segment_duration(s) for s in segments)
    ratio = estimated / target_duration if target_duration > 0 else 0.0
    expected_min, expected_max = _get_segment_range(target_duration)

    if ratio < 0.5:
        return SegmentValidationResult(
            status="too_short",
            segment_count=seg_count,
            estimated_duration=round(estimated, 1),
            target_duration=target_duration,
            ratio=round(ratio, 3),
            expected_min=expected_min,
            expected_max=expected_max,
            suggestion="add_segments",
            message=f"推定尺 {estimated:.0f}秒 は目標 {target_duration:.0f}秒 の {ratio:.0%} (不足)",
        )
    elif ratio > 1.5:
        return SegmentValidationResult(
            status="too_long",
            segment_count=seg_count,
            estimated_duration=round(estimated, 1),
            target_duration=target_duration,
            ratio=round(ratio, 3),
            expected_min=expected_min,
            expected_max=expected_max,
            suggestion="trim_segments",
            message=f"推定尺 {estimated:.0f}秒 は目標 {target_duration:.0f}秒 の {ratio:.0%} (超過)",
        )
    elif seg_count < expected_min:
        return SegmentValidationResult(
            status="too_few",
            segment_count=seg_count,
            estimated_duration=round(estimated, 1),
            target_duration=target_duration,
            ratio=round(ratio, 3),
            expected_min=expected_min,
            expected_max=expected_max,
            suggestion="add_segments",
            message=f"セグメント数 {seg_count} は期待範囲 {expected_min}-{expected_max} を下回る",
        )
    elif seg_count > expected_max:
        return SegmentValidationResult(
            status="too_many",
            segment_count=seg_count,
            estimated_duration=round(estimated, 1),
            target_duration=target_duration,
            ratio=round(ratio, 3),
            expected_min=expected_min,
            expected_max=expected_max,
            suggestion="merge_segments",
            message=f"セグメント数 {seg_count} は期待範囲 {expected_min}-{expected_max} を上回る",
        )
    else:
        return SegmentValidationResult(
            status="ok",
            segment_count=seg_count,
            estimated_duration=round(estimated, 1),
            target_duration=target_duration,
            ratio=round(ratio, 3),
            expected_min=expected_min,
            expected_max=expected_max,
            suggestion="",
            message=f"推定尺 {estimated:.0f}秒 / 目標 {target_duration:.0f}秒 ({ratio:.0%}), {seg_count}セグメント",
        )


# --- Phase 2: 自動調整 ---

async def adjust_segments(
    segments: List[Dict[str, Any]],
    validation: SegmentValidationResult,
    topic: str = "",
    speaker_mapping: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """検証結果に基づいてセグメントを自動調整する。

    too_short/too_few → LLMに追加セグメント生成を依頼
    too_long/too_many → 短いセグメントを統合

    Args:
        segments: 元のセグメント群。
        validation: validate_segments()の結果。
        topic: トピック名 (追加生成用プロンプトのコンテキスト)。
        speaker_mapping: 話者マッピング。

    Returns:
        調整済みのセグメント群。調整できなかった場合は元のsegmentsを返す。
    """
    if validation.is_ok:
        return segments

    if validation.suggestion == "add_segments":
        return await _expand_segments(segments, validation, topic, speaker_mapping)
    elif validation.suggestion in ("trim_segments", "merge_segments"):
        return _merge_short_segments(segments, validation)

    return segments


async def _expand_segments(
    segments: List[Dict[str, Any]],
    validation: SegmentValidationResult,
    topic: str,
    speaker_mapping: Optional[Dict[str, str]],
) -> List[Dict[str, Any]]:
    """セグメントを追加して尺を伸ばす。"""
    try:
        from core.llm_provider import create_llm_provider
        provider = create_llm_provider()
    except Exception:
        logger.warning("LLMプロバイダー取得失敗: セグメント自動追加をスキップ")
        return segments

    # 既存セグメントの話者を取得
    speakers = list({s.get("speaker", "Host1") for s in segments})
    if speaker_mapping:
        speakers = list(speaker_mapping.values()) or speakers

    deficit_seconds = validation.target_duration - validation.estimated_duration
    additional_count = max(1, int(deficit_seconds / 15))  # 1セグメント≒15秒と概算

    existing_topics = [s.get("content", "")[:50] for s in segments[:5]]
    prompt = (
        f"以下のトピック「{topic}」について、既存の台本を補強する追加セグメントを{additional_count}件生成してください。\n"
        f"話者: {', '.join(speakers)}\n"
        f"既存セグメントの冒頭:\n" + "\n".join(f"- {t}" for t in existing_topics) + "\n\n"
        f"出力はJSON配列のみ。各要素は {{'speaker': '...', 'content': '...', 'section': '補足', 'key_points': [...]}} の形式。\n"
        f"```json から始めないこと。JSONのみ出力。"
    )

    try:
        response = await provider.generate_text(prompt, max_tokens=2048)
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1] if "\n" in response else response[7:]
        if response.endswith("```"):
            response = response[:-3]

        new_segments = json.loads(response)
        if not isinstance(new_segments, list):
            logger.warning("LLM応答がリスト形式でない: セグメント追加をスキップ")
            return segments

        # 既存セグメントの末尾に追加
        result = list(segments)
        for seg in new_segments:
            if isinstance(seg, dict) and seg.get("content"):
                seg.setdefault("speaker", speakers[0] if speakers else "Host1")
                seg.setdefault("section", "補足")
                seg.setdefault("key_points", [])
                result.append(seg)

        logger.info(f"SP-044 自動追加: {len(result) - len(segments)}セグメント追加 ({len(segments)}→{len(result)})")
        return result

    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        logger.warning(f"セグメント追加のLLM応答解析失敗: {e}")
        return segments
    except Exception as e:
        logger.warning(f"セグメント追加失敗: {e}")
        return segments


def _merge_short_segments(
    segments: List[Dict[str, Any]],
    validation: SegmentValidationResult,
) -> List[Dict[str, Any]]:
    """短いセグメントを統合して数を減らす。"""
    if len(segments) <= validation.expected_max:
        return segments

    # 推定尺が短い順にソートして統合候補を見つける
    indexed = [(i, estimate_segment_duration(s)) for i, s in enumerate(segments)]
    indexed.sort(key=lambda x: x[1])

    # 統合対象: 最も短いセグメントを次のセグメントに統合
    merge_count = len(segments) - validation.expected_max
    to_merge = set()
    for idx, (seg_idx, _) in enumerate(indexed):
        if idx >= merge_count:
            break
        to_merge.add(seg_idx)

    result: List[Dict[str, Any]] = []
    pending_merge: Optional[Dict[str, Any]] = None

    for i, seg in enumerate(segments):
        if i in to_merge:
            if pending_merge is None:
                pending_merge = dict(seg)
            else:
                # 前のpendingを次のセグメントに統合
                pending_merge["content"] = (
                    str(pending_merge.get("content", ""))
                    + " "
                    + str(seg.get("content", ""))
                )
                kps = list(pending_merge.get("key_points", []))
                kps.extend(seg.get("key_points", []))
                pending_merge["key_points"] = kps
        else:
            if pending_merge is not None:
                # pending_mergeを現在のセグメントに統合
                seg = dict(seg)
                seg["content"] = (
                    str(pending_merge.get("content", ""))
                    + " "
                    + str(seg.get("content", ""))
                )
                kps = list(pending_merge.get("key_points", []))
                kps.extend(seg.get("key_points", []))
                seg["key_points"] = kps
                pending_merge = None
            result.append(seg)

    if pending_merge is not None:
        if result:
            last = dict(result[-1])
            last["content"] = str(last.get("content", "")) + " " + str(pending_merge.get("content", ""))
            result[-1] = last
        else:
            result.append(pending_merge)

    logger.info(f"SP-044 自動統合: {len(segments) - len(result)}セグメント統合 ({len(segments)}→{len(result)})")
    return result


# --- Phase 3: 手動モード ---

class DurationModeAction:
    """手動モードのユーザー選択結果。"""
    CONTINUE = "continue"
    ADJUST = "adjust"
    ABORT = "abort"


def prompt_manual_decision(validation: SegmentValidationResult) -> str:
    """CLIで検証結果を表示し、ユーザーに続行/調整/中断を選択させる。

    Returns:
        DurationModeAction の値 (continue/adjust/abort)。
    """
    print("\n" + "=" * 60)
    print("セグメント粒度検証結果 (SP-044)")
    print("=" * 60)
    print(f"  ステータス: {validation.status}")
    print(f"  セグメント数: {validation.segment_count}")
    print(f"  推定尺: {validation.estimated_duration:.0f}秒")
    print(f"  目標尺: {validation.target_duration:.0f}秒")
    print(f"  比率: {validation.ratio:.0%}")
    print(f"  期待範囲: {validation.expected_min}-{validation.expected_max}セグメント")
    if validation.message:
        print(f"  詳細: {validation.message}")
    if validation.suggestion:
        print(f"  推奨: {validation.suggestion}")
    print("=" * 60)
    print("\n選択してください:")
    print("  [c] 続行 (現在のセグメントをそのまま使用)")
    print("  [a] 自動調整 (LLM経由で追加/統合)")
    print("  [q] 中断 (パイプライン停止)")

    while True:
        try:
            choice = input("\n> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return DurationModeAction.ABORT

        if choice in ("c", "continue"):
            return DurationModeAction.CONTINUE
        elif choice in ("a", "adjust", "auto"):
            return DurationModeAction.ADJUST
        elif choice in ("q", "quit", "abort"):
            return DurationModeAction.ABORT
        else:
            print("  [c] 続行 / [a] 自動調整 / [q] 中断 のいずれかを入力してください")
