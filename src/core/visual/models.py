"""ビジュアルリソースパイプライン データモデル (SP-033)"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SegmentType(Enum):
    """セグメントの視覚的分類。"""

    VISUAL = "visual"    # ストック画像候補 (物語的・描写的・概念的)
    TEXTUAL = "textual"  # テキストスライド維持 (データ・手順・リスト)


class AnimationType(Enum):
    """YMM4 ImageItem に適用するアニメーション種別。

    CSV 4列目の文字列値に対応する。
    """

    KEN_BURNS = "ken_burns"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    PAN_UP = "pan_up"
    PAN_DOWN = "pan_down"
    STATIC = "static"

    @classmethod
    def from_str(cls, value: str) -> AnimationType:
        """文字列からAnimationTypeを取得。不明な値はKEN_BURNSにフォールバック。"""
        try:
            return cls(value.lower().strip())
        except ValueError:
            return cls.KEN_BURNS

    @classmethod
    def cycle_types(cls) -> List[AnimationType]:
        """自動割当に使用するサイクル順序。staticは除外。"""
        return [
            cls.KEN_BURNS,
            cls.PAN_LEFT,
            cls.ZOOM_IN,
            cls.PAN_RIGHT,
            cls.ZOOM_OUT,
            cls.PAN_UP,
            cls.PAN_DOWN,
        ]


@dataclass
class VisualResource:
    """1セグメントに対応するビジュアルリソース。"""

    image_path: Optional[Path] = None
    animation_type: AnimationType = AnimationType.KEN_BURNS
    source: str = "slide"  # "slide", "stock", "ai", "generated", "manual", "none"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualResourcePackage:
    """セグメント群に対応するビジュアルリソースのまとまり。"""

    resources: List[VisualResource] = field(default_factory=list)
    source_provider: str = "slide"
