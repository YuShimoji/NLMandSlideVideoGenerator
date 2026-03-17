"""
CSV自動合成モジュール (SP-032 Gap 1, SP-033 拡張)

台本セグメント + スライドPNG → YMM4インポート用CSV (話者,テキスト,画像パス[,アニメーション種別])
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils.logger import logger
from .visual.models import AnimationType, VisualResourcePackage
from .visual.animation_assigner import AnimationAssigner


_SPEAKER_PREFIX_RE = re.compile(r"^(Host\d*|Speaker\d*|ナレーター)\s*[:：]\s*", re.IGNORECASE)


def _strip_speaker_prefix(text: str) -> str:
    """テキスト先頭の話者プレフィックス (Host1: 等) を除去する。

    Gemini生成台本の content に ``Host1: 皆さん...`` のような
    プレフィックスが含まれることがある。CSV の speaker 列で話者を識別する
    ため、content 内の重複プレフィックスは不要。
    """
    return _SPEAKER_PREFIX_RE.sub("", text).strip()


class CsvAssembler:
    """台本とスライド画像からYMM4用CSVを自動合成する。

    マッチング戦略:
    - セグメント数 >= スライド数: 均等分割（複数セグメントが同一スライドを共有）
    - セグメント数 < スライド数: 1:1マッチ、余剰スライドは無視
    - スライド0件: 画像パス空欄でCSV生成（後方互換）
    """

    def assemble(
        self,
        script_segments: List[Dict[str, Any]],
        slide_image_paths: List[Path],
        output_path: Path,
        speaker_mapping: Optional[Dict[str, str]] = None,
        auto_animation: bool = True,
    ) -> Path:
        """台本セグメント + スライドPNG群 → CSV 4列形式で出力。

        Args:
            script_segments: 台本セグメント群。各要素に speaker, content/text キーを期待。
            slide_image_paths: スライドPNG画像のパス群（順序はスライド番号順）。
            output_path: 出力CSVファイルパス。
            speaker_mapping: 台本上の話者名 → YMM4ボイス名のマッピング。
            auto_animation: True の場合、アニメーション種別を自動割当する (SP-033)。

        Returns:
            出力CSVのパス。
        """
        if not script_segments:
            raise ValueError("台本セグメントが空です。CSVを生成できません。")

        speaker_mapping = speaker_mapping or {}
        num_segments = len(script_segments)
        num_slides = len(slide_image_paths)

        # セグメント→スライドのマッピングを計算
        segment_to_slide = self._compute_mapping(num_segments, num_slides)

        # アニメーション割当 (SP-033)
        animation_types: List[str] = []
        if auto_animation:
            assigner = AnimationAssigner()
            image_list: List[Optional[Path]] = []
            for i in range(num_segments):
                slide_idx = segment_to_slide.get(i)
                if slide_idx is not None and slide_idx < num_slides:
                    image_list.append(slide_image_paths[slide_idx])
                else:
                    image_list.append(None)
            package = assigner.assign(num_segments, image_list)
            animation_types = [r.animation_type.value for r in package.resources]
        else:
            animation_types = [AnimationType.KEN_BURNS.value] * num_segments

        rows: List[List[str]] = []
        for i, segment in enumerate(script_segments):
            speaker = segment.get("speaker", "")
            text = segment.get("content", "") or segment.get("text", "")
            text = _strip_speaker_prefix(text)

            # 話者名マッピング適用
            if speaker in speaker_mapping:
                speaker = speaker_mapping[speaker]

            # 画像パス
            slide_idx = segment_to_slide.get(i)
            image_path = ""
            if slide_idx is not None and slide_idx < num_slides:
                image_path = str(slide_image_paths[slide_idx].resolve())

            rows.append([speaker, text, image_path, animation_types[i]])

        # CSV書き出し
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

        logger.info(
            f"CSV自動合成完了: {len(rows)}行, スライド{num_slides}枚 → {output_path}"
        )
        return output_path

    @staticmethod
    def _compute_mapping(
        num_segments: int, num_slides: int
    ) -> Dict[int, Optional[int]]:
        """セグメントインデックス → スライドインデックスのマッピングを計算。

        均等分割: セグメント群をスライド数で均等に分け、各グループに同一スライドを割り当て。
        """
        if num_slides == 0:
            return {i: None for i in range(num_segments)}

        if num_segments <= num_slides:
            # 1:1マッチ
            return {i: i for i in range(num_segments)}

        # 均等分割
        mapping: Dict[int, Optional[int]] = {}
        segments_per_slide = num_segments / num_slides
        for i in range(num_segments):
            slide_idx = min(int(i / segments_per_slide), num_slides - 1)
            mapping[i] = slide_idx
        return mapping

    def assemble_from_package(
        self,
        script_segments: List[Dict[str, Any]],
        package: VisualResourcePackage,
        output_path: Path,
        speaker_mapping: Optional[Dict[str, str]] = None,
    ) -> Path:
        """VisualResourcePackage (Orchestrator出力) からCSVを生成する。

        Orchestratorが画像パスとアニメーション種別を決定済みなので、
        本メソッドはセグメントとリソースを結合してCSVに書き出すのみ。

        Args:
            script_segments: 台本セグメント群。
            package: Orchestrator出力のVisualResourcePackage。
            output_path: 出力CSVファイルパス。
            speaker_mapping: 話者名マッピング。

        Returns:
            出力CSVのパス。
        """
        if not script_segments:
            raise ValueError("台本セグメントが空です。CSVを生成できません。")

        speaker_mapping = speaker_mapping or {}
        resources = package.resources

        rows: List[List[str]] = []
        for i, segment in enumerate(script_segments):
            speaker = segment.get("speaker", "")
            text = segment.get("content", "") or segment.get("text", "")
            text = _strip_speaker_prefix(text)

            if speaker in speaker_mapping:
                speaker = speaker_mapping[speaker]

            # リソースから画像パスとアニメーションを取得
            if i < len(resources):
                r = resources[i]
                image_path = str(r.image_path.resolve()) if r.image_path else ""
                animation = r.animation_type.value
            else:
                image_path = ""
                animation = AnimationType.STATIC.value

            rows.append([speaker, text, image_path, animation])

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

        stock_count = sum(1 for r in resources if r.source == "stock")
        slide_count = sum(1 for r in resources if r.source == "slide")
        logger.info(
            f"CSV合成完了 (Orchestrator): {len(rows)}行, "
            f"stock={stock_count}, slide={slide_count} → {output_path}"
        )
        return output_path

    @classmethod
    def from_script_bundle(
        cls,
        script_bundle: Dict[str, Any],
        slides_dir: Path,
        output_path: Path,
        speaker_mapping: Optional[Dict[str, str]] = None,
        slide_pattern: str = "slide_{:04d}.png",
        auto_animation: bool = True,
    ) -> Path:
        """ScriptBundle辞書 + スライドディレクトリからCSVを生成する便利メソッド。

        Args:
            script_bundle: GeminiProvider等が出力するscript_bundle辞書。
            slides_dir: スライドPNG群が保存されているディレクトリ。
            output_path: 出力CSVファイルパス。
            speaker_mapping: 話者名マッピング。
            slide_pattern: スライドファイル名パターン (0-indexed)。
            auto_animation: アニメーション自動割当を有効にする (SP-033)。

        Returns:
            出力CSVのパス。
        """
        segments = script_bundle.get("segments", [])

        # スライドPNG群を検索（パターンマッチ or ソート済み一覧）
        slide_paths: List[Path] = []
        if slides_dir.exists():
            # パターンベースで探索
            png_files = sorted(slides_dir.glob("*.png"))
            if png_files:
                slide_paths = png_files
            else:
                logger.warning(f"スライドディレクトリにPNGが見つかりません: {slides_dir}")

        assembler = cls()
        return assembler.assemble(
            script_segments=segments,
            slide_image_paths=slide_paths,
            output_path=output_path,
            speaker_mapping=speaker_mapping,
            auto_animation=auto_animation,
        )
