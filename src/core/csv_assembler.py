"""
CSV自動合成モジュール (SP-032 Gap 1)

台本セグメント + スライドPNG → YMM4インポート用CSV (話者,テキスト,画像パス)
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils.logger import logger


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
    ) -> Path:
        """台本セグメント + スライドPNG群 → CSV 3列形式で出力。

        Args:
            script_segments: 台本セグメント群。各要素に speaker, content/text キーを期待。
            slide_image_paths: スライドPNG画像のパス群（順序はスライド番号順）。
            output_path: 出力CSVファイルパス。
            speaker_mapping: 台本上の話者名 → YMM4ボイス名のマッピング。

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

        rows: List[List[str]] = []
        for i, segment in enumerate(script_segments):
            speaker = segment.get("speaker", "")
            text = segment.get("content", "") or segment.get("text", "")

            # 話者名マッピング適用
            if speaker in speaker_mapping:
                speaker = speaker_mapping[speaker]

            # 画像パス
            slide_idx = segment_to_slide.get(i)
            image_path = ""
            if slide_idx is not None and slide_idx < num_slides:
                image_path = str(slide_image_paths[slide_idx].resolve())

            rows.append([speaker, text, image_path])

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

    @classmethod
    def from_script_bundle(
        cls,
        script_bundle: Dict[str, Any],
        slides_dir: Path,
        output_path: Path,
        speaker_mapping: Optional[Dict[str, str]] = None,
        slide_pattern: str = "slide_{:04d}.png",
    ) -> Path:
        """ScriptBundle辞書 + スライドディレクトリからCSVを生成する便利メソッド。

        Args:
            script_bundle: GeminiProvider等が出力するscript_bundle辞書。
            slides_dir: スライドPNG群が保存されているディレクトリ。
            output_path: 出力CSVファイルパス。
            speaker_mapping: 話者名マッピング。
            slide_pattern: スライドファイル名パターン (0-indexed)。

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
        )
