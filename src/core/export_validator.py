"""Pre-Export 検証モジュール (SP-031)

CSV出力のYMM4インポート前検証を行い、問題を事前に検出する。
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .visual.models import AnimationType


class Severity(Enum):
    """検証結果の重大度。"""

    ERROR = "error"      # インポート失敗の可能性
    WARNING = "warning"  # 品質低下の可能性
    INFO = "info"        # 参考情報


@dataclass
class ValidationIssue:
    """検証で検出された問題。"""

    severity: Severity
    code: str
    message: str
    row: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """検証結果全体。"""

    issues: List[ValidationIssue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        parts = [f"[{status}] {self.error_count} errors, {self.warning_count} warnings"]
        if self.stats:
            parts.append(f"  Rows: {self.stats.get('total_rows', '?')}")
            parts.append(f"  Images: {self.stats.get('rows_with_images', '?')}/{self.stats.get('total_rows', '?')}")
            parts.append(f"  Speakers: {', '.join(self.stats.get('speakers', []))}")
        return "\n".join(parts)


# 有効なアニメーション種別
_VALID_ANIMATIONS = {a.value for a in AnimationType}


class ExportValidator:
    """YMM4インポート用CSVの事前検証。

    検証項目:
    1. CSV構造 (列数、空行)
    2. 話者名の存在
    3. テキストの存在
    4. 画像ファイルの存在
    5. アニメーション種別の有効性
    6. 連続同一画像の検出 (視覚的単調さ)
    7. テンプレート整合性 (オプション)
    """

    def __init__(
        self,
        check_image_exists: bool = True,
        max_consecutive_same_image: int = 5,
        template: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Args:
            check_image_exists: 画像ファイルの存在チェックを行うか。
            max_consecutive_same_image: 連続同一画像の警告閾値。
            template: style_template.json の内容。指定時はテンプレート整合性も検証。
        """
        self.check_image_exists = check_image_exists
        self.max_consecutive_same_image = max_consecutive_same_image
        self.template = template

    def validate_csv(self, csv_path: Path) -> ValidationResult:
        """CSVファイルを検証する。

        Args:
            csv_path: 検証対象のCSVファイルパス。

        Returns:
            検証結果。
        """
        result = ValidationResult()

        if not csv_path.exists():
            result.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                code="FILE_NOT_FOUND",
                message=f"CSVファイルが見つかりません: {csv_path}",
            ))
            return result

        try:
            rows = self._read_csv(csv_path)
        except Exception as e:
            result.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                code="CSV_READ_ERROR",
                message=f"CSV読み込み失敗: {e}",
            ))
            return result

        if not rows:
            result.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                code="EMPTY_CSV",
                message="CSVが空です",
            ))
            return result

        # 統計情報収集
        speakers: set[str] = set()
        image_paths: list[str] = []
        animations: list[str] = []

        for row_idx, row in enumerate(rows):
            row_num = row_idx + 1

            # 列数チェック
            if len(row) < 2:
                result.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    code="INSUFFICIENT_COLUMNS",
                    message=f"列数不足 (期待: 2-4, 実際: {len(row)})",
                    row=row_num,
                ))
                continue

            speaker = row[0].strip()
            text = row[1].strip()
            image_path = row[2].strip() if len(row) > 2 else ""
            animation = row[3].strip() if len(row) > 3 else ""

            # 話者名チェック
            if not speaker:
                result.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    code="EMPTY_SPEAKER",
                    message="話者名が空です",
                    row=row_num,
                ))
            else:
                speakers.add(speaker)

            # テキストチェック
            if not text:
                result.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    code="EMPTY_TEXT",
                    message="テキストが空です",
                    row=row_num,
                ))

            # 画像パスチェック
            if image_path:
                image_paths.append(image_path)
                if self.check_image_exists and not Path(image_path).exists():
                    result.issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        code="IMAGE_NOT_FOUND",
                        message=f"画像ファイルが見つかりません: {image_path}",
                        row=row_num,
                    ))
            else:
                image_paths.append("")

            # アニメーション種別チェック
            if animation:
                animations.append(animation)
                if animation not in _VALID_ANIMATIONS:
                    result.issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        code="INVALID_ANIMATION",
                        message=f"不明なアニメーション種別: '{animation}'",
                        row=row_num,
                        details={"valid_types": list(_VALID_ANIMATIONS)},
                    ))
            else:
                animations.append("")

        # 連続同一画像チェック
        self._check_consecutive_images(image_paths, result)

        # テンプレート整合性チェック
        if self.template:
            self._check_template_consistency(animations, speakers, result)

        # 統計情報
        result.stats = {
            "total_rows": len(rows),
            "rows_with_images": sum(1 for p in image_paths if p),
            "rows_without_images": sum(1 for p in image_paths if not p),
            "speakers": sorted(speakers),
            "animation_distribution": self._count_distribution(animations),
            "unique_images": len(set(p for p in image_paths if p)),
        }

        return result

    def validate_rows(self, rows: List[List[str]]) -> ValidationResult:
        """メモリ上のCSV行データを検証する。

        Args:
            rows: CSV行のリスト。各行は [speaker, text, image_path, animation] 形式。

        Returns:
            検証結果。
        """
        result = ValidationResult()
        if not rows:
            result.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                code="EMPTY_CSV",
                message="データが空です",
            ))
            return result

        speakers: set[str] = set()
        image_paths: list[str] = []
        animations: list[str] = []

        for row_idx, row in enumerate(rows):
            row_num = row_idx + 1

            if len(row) < 2:
                result.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    code="INSUFFICIENT_COLUMNS",
                    message=f"列数不足 (期待: 2-4, 実際: {len(row)})",
                    row=row_num,
                ))
                continue

            speaker = row[0].strip()
            text = row[1].strip()
            image_path = row[2].strip() if len(row) > 2 else ""
            animation = row[3].strip() if len(row) > 3 else ""

            if not speaker:
                result.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    code="EMPTY_SPEAKER",
                    message="話者名が空です",
                    row=row_num,
                ))
            else:
                speakers.add(speaker)

            if not text:
                result.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    code="EMPTY_TEXT",
                    message="テキストが空です",
                    row=row_num,
                ))

            if image_path:
                image_paths.append(image_path)
                if self.check_image_exists and not Path(image_path).exists():
                    result.issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        code="IMAGE_NOT_FOUND",
                        message=f"画像ファイルが見つかりません: {image_path}",
                        row=row_num,
                    ))
            else:
                image_paths.append("")

            if animation:
                animations.append(animation)
                if animation not in _VALID_ANIMATIONS:
                    result.issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        code="INVALID_ANIMATION",
                        message=f"不明なアニメーション種別: '{animation}'",
                        row=row_num,
                    ))
            else:
                animations.append("")

        self._check_consecutive_images(image_paths, result)

        if self.template:
            self._check_template_consistency(animations, speakers, result)

        result.stats = {
            "total_rows": len(rows),
            "rows_with_images": sum(1 for p in image_paths if p),
            "rows_without_images": sum(1 for p in image_paths if not p),
            "speakers": sorted(speakers),
            "animation_distribution": self._count_distribution(animations),
            "unique_images": len(set(p for p in image_paths if p)),
        }

        return result

    def _read_csv(self, csv_path: Path) -> List[List[str]]:
        """CSVファイルを読み込む。"""
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            return [row for row in reader if row]

    def _check_consecutive_images(
        self, image_paths: List[str], result: ValidationResult
    ) -> None:
        """連続同一画像を検出する。"""
        if len(image_paths) < 2:
            return

        consecutive = 1
        max_consecutive = 1
        max_consecutive_path = ""
        max_consecutive_start = 0

        for i in range(1, len(image_paths)):
            if image_paths[i] and image_paths[i] == image_paths[i - 1]:
                consecutive += 1
                if consecutive > max_consecutive:
                    max_consecutive = consecutive
                    max_consecutive_path = image_paths[i]
                    max_consecutive_start = i - consecutive + 1
            else:
                consecutive = 1

        if max_consecutive > self.max_consecutive_same_image:
            result.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                code="CONSECUTIVE_SAME_IMAGE",
                message=(
                    f"同一画像が{max_consecutive}行連続 "
                    f"(閾値: {self.max_consecutive_same_image})"
                ),
                row=max_consecutive_start + 1,
                details={"image_path": max_consecutive_path, "count": max_consecutive},
            ))

    def _check_template_consistency(
        self,
        animations: List[str],
        speakers: set[str],
        result: ValidationResult,
    ) -> None:
        """テンプレート設定との整合性を検証する。"""
        template = self.template
        if not template:
            return

        # アニメーション設定との整合性
        anim_config = template.get("animation", {})
        if anim_config:
            pan_types = {"pan_left", "pan_right", "pan_up"}
            has_pan = any(a in pan_types for a in animations)
            if has_pan and "pan_zoom_ratio" not in anim_config:
                result.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    code="TEMPLATE_MISSING_PAN_CONFIG",
                    message="パンアニメーション使用中だが pan_zoom_ratio がテンプレートに未定義",
                ))

        # 話者色の充足確認
        speaker_colors = template.get("speaker_colors", [])
        if speaker_colors and len(speakers) > len(speaker_colors):
            result.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                code="INSUFFICIENT_SPEAKER_COLORS",
                message=(
                    f"話者数({len(speakers)})がテンプレートの色数"
                    f"({len(speaker_colors)})を超えています"
                ),
            ))

        # バリデーション設定のチェック
        validation_config = template.get("validation", {})
        max_duration = validation_config.get("max_total_duration_seconds")
        if max_duration:
            default_dur = template.get("timing", {}).get("default_duration_seconds", 3.0)
            estimated_duration = len(animations) * default_dur
            if estimated_duration > max_duration:
                result.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    code="ESTIMATED_DURATION_EXCEEDED",
                    message=(
                        f"推定動画長 ({estimated_duration:.0f}秒) が "
                        f"上限 ({max_duration:.0f}秒) を超える可能性"
                    ),
                    details={
                        "estimated_seconds": estimated_duration,
                        "max_seconds": max_duration,
                    },
                ))

    @staticmethod
    def _count_distribution(items: List[str]) -> Dict[str, int]:
        """アイテムの出現分布を計算する。"""
        dist: Dict[str, int] = {}
        for item in items:
            if item:
                dist[item] = dist.get(item, 0) + 1
        return dist
