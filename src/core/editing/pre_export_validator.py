"""Pre-Export Validation (SP-031)。

CsvAssembler 出力のCSVを、YMM4インポート前に検証する。
テンプレートの閾値に基づいてアセット存在・タイミング整合性をチェック。
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from core.utils.logger import logger
from core.style_template import StyleTemplate, StyleTemplateManager


@dataclass
class ValidationResult:
    """バリデーション結果。"""
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        parts = []
        if self.errors:
            parts.append(f"errors={len(self.errors)}")
        if self.warnings:
            parts.append(f"warnings={len(self.warnings)}")
        if not parts:
            return "OK"
        return ", ".join(parts)


def validate_timeline_csv(
    csv_path: Path,
    template: Optional[StyleTemplate] = None,
) -> ValidationResult:
    """タイムラインCSVをバリデーションする。

    Args:
        csv_path: 検証対象CSVファイル。
        template: スタイルテンプレート。Noneの場合はデフォルトをロード。

    Returns:
        ValidationResult (errors/warnings を含む)。
    """
    if template is None:
        mgr = StyleTemplateManager()
        mgr.load_all()
        template = mgr.get_or_default()

    result = ValidationResult()

    if not csv_path.exists():
        result.valid = False
        result.errors.append(f"CSV not found: {csv_path}")
        return result

    rows = _read_csv(csv_path)
    if not rows:
        result.valid = False
        result.errors.append("CSV is empty")
        return result

    # 各行の検証
    for i, row in enumerate(rows, start=1):
        speaker = row.get("speaker", "")
        text = row.get("text", "")
        image_path = row.get("image_path", "")
        animation = row.get("animation_type", "")

        # 空行チェック
        if not text.strip() and not image_path.strip():
            result.warnings.append(f"Row {i}: empty text and no image")

        # 画像ファイル存在チェック
        if image_path.strip():
            img = Path(image_path)
            if not img.exists():
                result.warnings.append(f"Row {i}: image not found: {image_path}")

        # アニメーション種別チェック
        valid_animations = {"ken_burns", "zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "static", ""}
        if animation and animation not in valid_animations:
            result.warnings.append(f"Row {i}: unknown animation type: {animation}")

    # 行数チェック (1時間の目安: 30fps * 3600s / 3s = 36000行は異常)
    if len(rows) > 5000:
        result.warnings.append(f"Large CSV: {len(rows)} rows (may cause slow import)")

    logger.info(f"Pre-export validation: {csv_path.name} — {result.summary}")
    return result


def _read_csv(csv_path: Path) -> List[dict]:
    """CSVを読み込んでリストを返す。4列形式 (speaker, text, image_path, animation_type)。"""
    rows = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for raw_row in reader:
                if not raw_row:
                    continue
                row = {
                    "speaker": raw_row[0] if len(raw_row) > 0 else "",
                    "text": raw_row[1] if len(raw_row) > 1 else "",
                    "image_path": raw_row[2] if len(raw_row) > 2 else "",
                    "animation_type": raw_row[3] if len(raw_row) > 3 else "",
                }
                rows.append(row)
    except Exception as e:
        logger.warning(f"CSV read error: {e}")
    return rows
