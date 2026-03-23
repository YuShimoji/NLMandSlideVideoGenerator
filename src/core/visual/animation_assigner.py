"""アニメーション自動割当 (SP-033 Phase 1, SP-052 Phase 3 場面別判定)

セグメント列に対して視覚的多様性を確保するアニメーション種別を自動割当する。
SP-052: セグメントの性質（スライド/統計/トピック変更/章開始）に基づく判定を追加。
"""
from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import AnimationType, VisualResource, VisualResourcePackage

# Statistics detection regex (shared with overlay_planner)
_STAT_RE = re.compile(
    r"[\$￥€]?\d[\d,\.]*\s*"
    r"(?:億|万|千|兆|百万|%|人|件|回|円|ドル|[KMBT](?:illion)?)?",
    re.IGNORECASE,
)


class AnimationAssigner:
    """セグメントごとにアニメーション種別を自動割当する。

    ルール:
    1. 同一アニメーションを2回連続で使用しない
    2. サイクル方式で順に割当
    3. 同一画像が連続する場合、異なるアニメーションを適用
    4. 画像なしセグメントには STATIC を割当
    5. text_slides=True のとき、全画像に STATIC を割当（テキスト主体スライド用）
    """

    def __init__(
        self,
        cycle: Optional[List[AnimationType]] = None,
        text_slides: bool = True,
    ):
        """
        Args:
            cycle: アニメーション種別のサイクル順序。
            text_slides: True の場合、全画像に STATIC を割当。
                Google Slides等のテキスト主体画像ではズーム/パンで
                文字が動いて視認性が低下するため、デフォルトTrue。
                写真・イラスト主体の画像ではFalseに設定してサイクルを有効化する。
        """
        self._text_slides = text_slides
        self._cycle = cycle or AnimationType.cycle_types()

    def assign(
        self,
        segment_count: int,
        image_paths: Optional[List[Optional[Path]]] = None,
    ) -> VisualResourcePackage:
        """セグメント数と画像パス群からVisualResourcePackageを生成する。

        Args:
            segment_count: セグメント数。
            image_paths: 各セグメントの画像パス。Noneまたは要素がNoneの場合は画像なし。

        Returns:
            アニメーション割当済みのVisualResourcePackage。
        """
        if segment_count <= 0:
            return VisualResourcePackage()

        image_paths = image_paths or [None] * segment_count
        # image_pathsがsegment_countより短い場合はNoneで埋める
        while len(image_paths) < segment_count:
            image_paths.append(None)

        resources: List[VisualResource] = []
        cycle_idx = 0
        prev_animation: Optional[AnimationType] = None

        for i in range(segment_count):
            img = image_paths[i]

            if img is None:
                # 画像なし → STATIC
                resources.append(
                    VisualResource(
                        image_path=None,
                        animation_type=AnimationType.STATIC,
                        source="none",
                    )
                )
                prev_animation = AnimationType.STATIC
                continue

            if self._text_slides:
                # テキスト主体スライド: ズーム/パンで文字が動くため STATIC 固定
                resources.append(
                    VisualResource(
                        image_path=img,
                        animation_type=AnimationType.STATIC,
                        source="slide",
                    )
                )
                prev_animation = AnimationType.STATIC
                continue

            # アニメーション選択: サイクルから取得
            animation = self._cycle[cycle_idx % len(self._cycle)]

            # 連続回避: 前と同じなら次へ進める
            if animation == prev_animation and len(self._cycle) > 1:
                cycle_idx += 1
                animation = self._cycle[cycle_idx % len(self._cycle)]

            resources.append(
                VisualResource(
                    image_path=img,
                    animation_type=animation,
                    source="slide",
                )
            )
            prev_animation = animation
            cycle_idx += 1

        return VisualResourcePackage(resources=resources, source_provider="slide")

    def assign_from_segments(
        self,
        segments: List[Dict[str, Any]],
        slide_image_paths: Optional[List[Path]] = None,
        segment_to_slide: Optional[Dict[int, Optional[int]]] = None,
        context_aware: bool = True,
    ) -> VisualResourcePackage:
        """台本セグメント + スライドマッピングからアニメーションを割当する。

        CsvAssemblerと連携して使用する。

        Args:
            segments: 台本セグメント群。
            slide_image_paths: スライドPNG画像パス群。
            segment_to_slide: セグメント→スライドインデックスのマッピング。
            context_aware: True の場合、セグメント性質に基づく場面別判定を行う (SP-052)。
        """
        segment_count = len(segments)
        if not slide_image_paths:
            none_list: List[Optional[Path]] = [None] * segment_count
            return self.assign(segment_count, none_list)

        # 画像パスの解決
        if segment_to_slide is None:
            img_list: List[Optional[Path]] = []
            for i in range(segment_count):
                if i < len(slide_image_paths):
                    img_list.append(slide_image_paths[i])
                else:
                    img_list.append(None)
        else:
            img_list = []
            for i in range(segment_count):
                slide_idx = segment_to_slide.get(i)
                if slide_idx is not None and slide_idx < len(slide_image_paths):
                    img_list.append(slide_image_paths[slide_idx])
                else:
                    img_list.append(None)

        if not context_aware or self._text_slides:
            return self.assign(segment_count, img_list)

        # SP-052: 場面別判定
        return self._assign_context_aware(segments, img_list)

    def _assign_context_aware(
        self,
        segments: List[Dict[str, Any]],
        image_paths: List[Optional[Path]],
    ) -> VisualResourcePackage:
        """SP-052: セグメントの性質に基づくアニメーション自動判定。

        判定優先度:
        1. 画像なし → STATIC
        2. スライド画像 (source == "slide") → STATIC (テキスト可読性優先)
        3. 統計データあり → STATIC (数値の可読性優先)
        4. 章の開始 (section 変化) → ZOOM_IN (注目を集める)
        5. トピック変更 (section 変化の直後) → PAN_LEFT or PAN_RIGHT (場面転換)
        6. デフォルト → KEN_BURNS (写真・イラスト向け)
        """
        resources: List[VisualResource] = []
        prev_section: Optional[str] = None

        for i, seg in enumerate(segments):
            img = image_paths[i]
            section = seg.get("section", "")
            content = seg.get("content", "") or seg.get("text", "")
            source = seg.get("image_source", "")

            if img is None:
                resources.append(VisualResource(
                    image_path=None, animation_type=AnimationType.STATIC, source="none",
                ))
                prev_section = section or prev_section
                continue

            # スライド画像 → STATIC
            if source == "slide":
                resources.append(VisualResource(
                    image_path=img, animation_type=AnimationType.STATIC, source="slide",
                ))
                prev_section = section or prev_section
                continue

            # 統計データ含有 → STATIC
            if _STAT_RE.search(content):
                resources.append(VisualResource(
                    image_path=img, animation_type=AnimationType.STATIC, source="stock",
                ))
                prev_section = section or prev_section
                continue

            # 章の開始 (section 変化) → ZOOM_IN
            if section and section != prev_section:
                resources.append(VisualResource(
                    image_path=img, animation_type=AnimationType.ZOOM_IN, source="stock",
                ))
                prev_section = section
                continue

            # デフォルト → KEN_BURNS
            resources.append(VisualResource(
                image_path=img, animation_type=AnimationType.KEN_BURNS, source="stock",
            ))
            prev_section = section or prev_section

        return VisualResourcePackage(resources=resources, source_provider="context_aware")
