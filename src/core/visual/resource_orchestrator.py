"""VisualResourceOrchestrator (SP-033 Phase 2)

スライドPNGとストック画像を統合し、セグメント分類に基づいて
最適なビジュアルリソースパッケージを生成する。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.utils.logger import logger

from .animation_assigner import AnimationAssigner
from .models import (
    AnimationType,
    SegmentType,
    VisualResource,
    VisualResourcePackage,
)
from .segment_classifier import SegmentClassifier


class VisualResourceOrchestrator:
    """スライド + ストック画像を統合し、VisualResourcePackageを生成する。

    責務:
    1. SegmentClassifier でセグメントを分類
    2. visual セグメント → StockImageClient で画像検索・ダウンロード
    3. textual セグメント → 既存スライドPNGを割当
    4. stock取得失敗 → スライドPNGにフォールバック
    5. アニメーション自動割当
    6. 連続同一ソース回避
    """

    # ストック画像が連続する最大セグメント数
    MAX_CONSECUTIVE_STOCK = 3
    # テキストスライドが連続する最大セグメント数 (超えたらstock挿入を検討)
    MAX_CONSECUTIVE_SLIDE = 5

    def __init__(
        self,
        classifier: Optional[SegmentClassifier] = None,
        stock_client: Optional[Any] = None,  # StockImageClient (Optional import)
        topic: str = "",
    ) -> None:
        """
        Args:
            classifier: セグメント分類器。None時はデフォルト設定で生成。
            stock_client: StockImageClient インスタンス。Noneの場合はスライドのみ使用。
            topic: 動画トピック (ストック画像検索のコンテキスト用)。
        """
        self.classifier = classifier or SegmentClassifier()
        self.stock_client = stock_client
        self.topic = topic

    def orchestrate(
        self,
        segments: List[Dict[str, Any]],
        slide_image_paths: Optional[List[Path]] = None,
    ) -> VisualResourcePackage:
        """セグメント群に対してビジュアルリソースを統合割当する。

        Args:
            segments: 台本セグメント群。
            slide_image_paths: スライドPNG画像パス群。

        Returns:
            混合ソースのVisualResourcePackage。
        """
        if not segments:
            return VisualResourcePackage()

        slide_image_paths = slide_image_paths or []
        num_segments = len(segments)
        num_slides = len(slide_image_paths)

        # Step 1: セグメント分類 (+Geminiキーワード抽出)
        keywords: Optional[List[str]] = None
        if self.classifier.use_gemini:
            classifications, keywords = self.classifier.classify_with_keywords(
                segments, self.topic
            )
            logger.info("Gemini classify_with_keywords 使用")
        else:
            classifications = self.classifier.classify(segments)

        visual_count = sum(1 for c in classifications if c == SegmentType.VISUAL)
        textual_count = num_segments - visual_count
        logger.info(f"セグメント分類: visual={visual_count}, textual={textual_count}")

        # Step 2: textual セグメントにスライドを割当
        slide_mapping = self._map_slides_to_textual(
            classifications, num_slides
        )

        # Step 3: visual セグメントにストック画像を取得・割当
        stock_mapping = self._fetch_stock_images(
            segments, classifications, keywords=keywords
        )

        # Step 4: リソース統合 + フォールバック
        resources = self._merge_resources(
            segments, classifications, slide_image_paths,
            slide_mapping, stock_mapping,
        )

        # Step 5: 連続同一ソース回避
        resources = self._enforce_variety(resources, slide_image_paths)

        # Step 6: アニメーション割当
        resources = self._assign_animations(resources)

        return VisualResourcePackage(
            resources=resources,
            source_provider="orchestrator",
        )

    def _map_slides_to_textual(
        self,
        classifications: List[SegmentType],
        num_slides: int,
    ) -> Dict[int, int]:
        """textualセグメントにスライドインデックスを均等割当する。

        Returns:
            {segment_index: slide_index} マッピング。
        """
        textual_indices = [
            i for i, c in enumerate(classifications)
            if c == SegmentType.TEXTUAL
        ]
        if not textual_indices or num_slides == 0:
            return {}

        mapping: Dict[int, int] = {}
        if len(textual_indices) <= num_slides:
            for i, seg_idx in enumerate(textual_indices):
                mapping[seg_idx] = i
        else:
            # 均等分割
            per_slide = len(textual_indices) / num_slides
            for i, seg_idx in enumerate(textual_indices):
                slide_idx = min(int(i / per_slide), num_slides - 1)
                mapping[seg_idx] = slide_idx

        return mapping

    def _fetch_stock_images(
        self,
        segments: List[Dict[str, Any]],
        classifications: List[SegmentType],
        keywords: Optional[List[str]] = None,
    ) -> Dict[int, Path]:
        """visualセグメントにストック画像を取得する。

        Args:
            segments: 全セグメント群。
            classifications: 分類結果。
            keywords: Gemini抽出済み英語キーワード群 (全セグメント分)。
                指定時はvisualセグメントのキーワードを検索クエリとして直接使用。

        Returns:
            {segment_index: local_image_path} マッピング。
        """
        if self.stock_client is None:
            logger.info("StockImageClient未設定。visualセグメントはスライドにフォールバック。")
            return {}

        visual_segments = []
        visual_indices = []
        visual_queries: Optional[List[str]] = [] if keywords else None
        for i, (seg, cls) in enumerate(zip(segments, classifications)):
            if cls == SegmentType.VISUAL:
                # トピックコンテキストをセグメントに追加
                enriched = dict(seg)
                if self.topic and "key_points" not in enriched:
                    enriched["key_points"] = [self.topic]
                elif self.topic:
                    # トピックをkey_pointsの先頭に追加（重複回避: 部分一致もチェック）
                    kps = list(enriched.get("key_points", []))
                    already_contains = any(
                        self.topic in kp or kp in self.topic for kp in kps
                    )
                    if not already_contains:
                        kps.insert(0, self.topic)
                    enriched["key_points"] = kps
                visual_segments.append(enriched)
                visual_indices.append(i)
                if visual_queries is not None and keywords:
                    visual_queries.append(keywords[i])

        if not visual_segments:
            return {}

        logger.info(f"ストック画像検索開始: {len(visual_segments)}セグメント対象")
        if visual_queries:
            logger.info(f"Gemini抽出キーワード使用: {len(visual_queries)}件")

        try:
            stock_images = self.stock_client.search_for_segments(
                visual_segments,
                images_per_segment=1,
                orientation="landscape",
                queries=visual_queries if visual_queries else None,
            )
        except Exception as e:
            logger.warning(f"ストック画像一括検索失敗: {e}")
            logger.info("全visualセグメントをスライドにフォールバック")
            return {}

        mapping: Dict[int, Path] = {}
        failed_indices: List[int] = []
        for i, (seg_idx, img) in enumerate(zip(visual_indices, stock_images)):
            if img.local_path and img.source != "none":
                mapping[seg_idx] = img.local_path
            else:
                failed_indices.append(seg_idx)

        logger.info(f"ストック画像取得: {len(mapping)}/{len(visual_indices)}件成功")
        if failed_indices:
            logger.info(f"スライドにフォールバック: セグメント {failed_indices}")
        return mapping

    def _merge_resources(
        self,
        segments: List[Dict[str, Any]],
        classifications: List[SegmentType],
        slide_paths: List[Path],
        slide_mapping: Dict[int, int],
        stock_mapping: Dict[int, Path],
    ) -> List[VisualResource]:
        """分類結果・スライド・ストック画像を統合してリソースリストを生成する。"""
        resources: List[VisualResource] = []
        fallback_slide_idx = 0

        for i, cls in enumerate(classifications):
            if cls == SegmentType.VISUAL and i in stock_mapping:
                # ストック画像がある
                resources.append(VisualResource(
                    image_path=stock_mapping[i],
                    animation_type=AnimationType.KEN_BURNS,  # 後でassignで上書き
                    source="stock",
                ))
            elif cls == SegmentType.TEXTUAL and i in slide_mapping:
                # テキストスライドがある
                slide_idx = slide_mapping[i]
                if slide_idx < len(slide_paths):
                    resources.append(VisualResource(
                        image_path=slide_paths[slide_idx],
                        animation_type=AnimationType.STATIC,
                        source="slide",
                    ))
                else:
                    resources.append(VisualResource(
                        image_path=None,
                        animation_type=AnimationType.STATIC,
                        source="none",
                    ))
            else:
                # フォールバック: スライドを割当
                if slide_paths:
                    fb_path = slide_paths[fallback_slide_idx % len(slide_paths)]
                    resources.append(VisualResource(
                        image_path=fb_path,
                        animation_type=AnimationType.STATIC,
                        source="slide",
                    ))
                    fallback_slide_idx += 1
                else:
                    resources.append(VisualResource(
                        image_path=None,
                        animation_type=AnimationType.STATIC,
                        source="none",
                    ))

        return resources

    def _enforce_variety(
        self,
        resources: List[VisualResource],
        slide_paths: List[Path],
    ) -> List[VisualResource]:
        """連続同一ソースを回避する。

        - ストック画像がMAX_CONSECUTIVE_STOCK以上連続 → 中間にスライド挿入
        - テキストスライドがMAX_CONSECUTIVE_SLIDE以上連続 → 変更なし (ストック不足時は仕方ない)
        """
        if len(resources) < 2:
            return resources

        result = list(resources)
        consecutive_stock = 0

        for i, r in enumerate(result):
            if r.source == "stock":
                consecutive_stock += 1
                if consecutive_stock > self.MAX_CONSECUTIVE_STOCK and slide_paths:
                    # スライドに差し替え
                    fb_idx = i % len(slide_paths)
                    result[i] = VisualResource(
                        image_path=slide_paths[fb_idx],
                        animation_type=AnimationType.STATIC,
                        source="slide",
                    )
                    consecutive_stock = 0
            else:
                consecutive_stock = 0

        return result

    def _assign_animations(
        self, resources: List[VisualResource]
    ) -> List[VisualResource]:
        """ソースに応じたアニメーションを割当する。

        - stock: サイクル方式 (ken_burns, pan, zoom)
        - slide: STATIC
        - none: STATIC
        """
        cycle = AnimationType.cycle_types()
        cycle_idx = 0
        prev_animation: Optional[AnimationType] = None

        for r in resources:
            if r.source == "stock" and r.image_path:
                animation = cycle[cycle_idx % len(cycle)]
                if animation == prev_animation and len(cycle) > 1:
                    cycle_idx += 1
                    animation = cycle[cycle_idx % len(cycle)]
                r.animation_type = animation
                prev_animation = animation
                cycle_idx += 1
            else:
                r.animation_type = AnimationType.STATIC
                prev_animation = AnimationType.STATIC

        return resources
