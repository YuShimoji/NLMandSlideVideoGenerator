"""アニメーション自動割当 (SP-033 Phase 1)

セグメント列に対して視覚的多様性を確保するアニメーション種別を自動割当する。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import AnimationType, VisualResource, VisualResourcePackage


class AnimationAssigner:
    """セグメントごとにアニメーション種別を自動割当する。

    ルール:
    1. 同一アニメーションを2回連続で使用しない
    2. サイクル方式で順に割当
    3. 同一画像が連続する場合、異なるアニメーションを適用
    4. 画像なしセグメントには STATIC を割当
    """

    def __init__(self, cycle: Optional[List[AnimationType]] = None):
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
    ) -> VisualResourcePackage:
        """台本セグメント + スライドマッピングからアニメーションを割当する。

        CsvAssemblerと連携して使用する。

        Args:
            segments: 台本セグメント群。
            slide_image_paths: スライドPNG画像パス群。
            segment_to_slide: セグメント→スライドインデックスのマッピング。
        """
        segment_count = len(segments)
        if not slide_image_paths:
            none_list: List[Optional[Path]] = [None] * segment_count
            return self.assign(segment_count, none_list)

        # マッピングが無い場合は1:1で割当
        if segment_to_slide is None:
            img_list: List[Optional[Path]] = []
            for i in range(segment_count):
                if i < len(slide_image_paths):
                    img_list.append(slide_image_paths[i])
                else:
                    img_list.append(None)
            return self.assign(segment_count, img_list)

        # マッピングに基づいて画像パスを解決
        mapped_list: List[Optional[Path]] = []
        for i in range(segment_count):
            slide_idx = segment_to_slide.get(i)
            if slide_idx is not None and slide_idx < len(slide_image_paths):
                mapped_list.append(slide_image_paths[slide_idx])
            else:
                mapped_list.append(None)

        return self.assign(segment_count, mapped_list)
