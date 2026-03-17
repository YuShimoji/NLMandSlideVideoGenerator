"""Pre-Export検証テスト (SP-031)"""
import csv
from pathlib import Path

import pytest

from core.export_validator import ExportValidator, Severity, ValidationResult


def _write_csv(path: Path, rows: list[list[str]]) -> Path:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)
    return path


def _make_image(tmp_path: Path, name: str = "img.jpg") -> Path:
    p = tmp_path / name
    p.write_bytes(b"fake_image")
    return p


class TestBasicValidation:
    def test_file_not_found(self, tmp_path: Path) -> None:
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(tmp_path / "nonexistent.csv")
        assert not result.passed
        assert result.error_count == 1
        assert result.issues[0].code == "FILE_NOT_FOUND"

    def test_empty_csv(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("", encoding="utf-8")
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(csv_path)
        assert not result.passed
        assert result.issues[0].code == "EMPTY_CSV"

    def test_valid_csv(self, tmp_path: Path) -> None:
        img = _make_image(tmp_path)
        rows = [
            ["reimu", "テスト1", str(img), "ken_burns"],
            ["marisa", "テスト2", str(img), "zoom_in"],
        ]
        csv_path = _write_csv(tmp_path / "valid.csv", rows)
        v = ExportValidator()
        result = v.validate_csv(csv_path)
        assert result.passed
        assert result.error_count == 0
        assert result.stats["total_rows"] == 2
        assert set(result.stats["speakers"]) == {"marisa", "reimu"}

    def test_insufficient_columns(self, tmp_path: Path) -> None:
        rows = [["only_one_column"]]
        csv_path = _write_csv(tmp_path / "bad.csv", rows)
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(csv_path)
        assert not result.passed
        assert any(i.code == "INSUFFICIENT_COLUMNS" for i in result.issues)


class TestContentValidation:
    def test_empty_speaker_warning(self, tmp_path: Path) -> None:
        rows = [["", "テスト", "", "ken_burns"]]
        csv_path = _write_csv(tmp_path / "no_speaker.csv", rows)
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(csv_path)
        assert result.passed  # WARNING, not ERROR
        assert any(i.code == "EMPTY_SPEAKER" for i in result.issues)

    def test_empty_text_warning(self, tmp_path: Path) -> None:
        rows = [["reimu", "", "", "ken_burns"]]
        csv_path = _write_csv(tmp_path / "no_text.csv", rows)
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(csv_path)
        assert any(i.code == "EMPTY_TEXT" for i in result.issues)

    def test_image_not_found_error(self, tmp_path: Path) -> None:
        rows = [["reimu", "テスト", "/nonexistent/path.jpg", "ken_burns"]]
        csv_path = _write_csv(tmp_path / "bad_img.csv", rows)
        v = ExportValidator(check_image_exists=True)
        result = v.validate_csv(csv_path)
        assert not result.passed
        assert any(i.code == "IMAGE_NOT_FOUND" for i in result.issues)

    def test_image_check_disabled(self, tmp_path: Path) -> None:
        rows = [["reimu", "テスト", "/nonexistent/path.jpg", "ken_burns"]]
        csv_path = _write_csv(tmp_path / "ok.csv", rows)
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(csv_path)
        assert result.passed

    def test_invalid_animation_warning(self, tmp_path: Path) -> None:
        rows = [["reimu", "テスト", "", "invalid_type"]]
        csv_path = _write_csv(tmp_path / "bad_anim.csv", rows)
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(csv_path)
        assert any(i.code == "INVALID_ANIMATION" for i in result.issues)


class TestConsecutiveImages:
    def test_consecutive_same_image_warning(self, tmp_path: Path) -> None:
        img = _make_image(tmp_path)
        rows = [[f"s{i}", f"text{i}", str(img), "ken_burns"] for i in range(8)]
        csv_path = _write_csv(tmp_path / "monotone.csv", rows)
        v = ExportValidator(max_consecutive_same_image=3)
        result = v.validate_csv(csv_path)
        assert any(i.code == "CONSECUTIVE_SAME_IMAGE" for i in result.issues)

    def test_no_warning_under_threshold(self, tmp_path: Path) -> None:
        img = _make_image(tmp_path)
        rows = [[f"s{i}", f"text{i}", str(img), "ken_burns"] for i in range(3)]
        csv_path = _write_csv(tmp_path / "ok.csv", rows)
        v = ExportValidator(max_consecutive_same_image=5)
        result = v.validate_csv(csv_path)
        assert not any(i.code == "CONSECUTIVE_SAME_IMAGE" for i in result.issues)


class TestTemplateConsistency:
    def test_insufficient_speaker_colors(self, tmp_path: Path) -> None:
        template = {"speaker_colors": ["#FFF", "#000"], "animation": {}, "timing": {}, "subtitle": {}}
        rows = [
            ["s1", "text", "", "ken_burns"],
            ["s2", "text", "", "ken_burns"],
            ["s3", "text", "", "ken_burns"],
        ]
        csv_path = _write_csv(tmp_path / "many_speakers.csv", rows)
        v = ExportValidator(check_image_exists=False, template=template)
        result = v.validate_csv(csv_path)
        assert any(i.code == "INSUFFICIENT_SPEAKER_COLORS" for i in result.issues)

    def test_estimated_duration_exceeded(self, tmp_path: Path) -> None:
        template = {
            "speaker_colors": ["#FFF"],
            "animation": {},
            "timing": {"default_duration_seconds": 10.0},
            "subtitle": {},
            "validation": {"max_total_duration_seconds": 30},
        }
        rows = [["s", "text", "", "ken_burns"]] * 5  # 5 * 10 = 50s > 30s limit
        csv_path = _write_csv(tmp_path / "long.csv", rows)
        v = ExportValidator(check_image_exists=False, template=template)
        result = v.validate_csv(csv_path)
        assert any(i.code == "ESTIMATED_DURATION_EXCEEDED" for i in result.issues)


class TestValidateRows:
    def test_in_memory_validation(self) -> None:
        rows = [
            ["reimu", "テスト1", "", "ken_burns"],
            ["marisa", "テスト2", "", "zoom_in"],
        ]
        v = ExportValidator(check_image_exists=False)
        result = v.validate_rows(rows)
        assert result.passed
        assert result.stats["total_rows"] == 2

    def test_empty_rows(self) -> None:
        v = ExportValidator(check_image_exists=False)
        result = v.validate_rows([])
        assert not result.passed
        assert result.issues[0].code == "EMPTY_CSV"


class TestStats:
    def test_animation_distribution(self, tmp_path: Path) -> None:
        rows = [
            ["s", "t1", "", "ken_burns"],
            ["s", "t2", "", "zoom_in"],
            ["s", "t3", "", "ken_burns"],
            ["s", "t4", "", "pan_left"],
        ]
        csv_path = _write_csv(tmp_path / "dist.csv", rows)
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(csv_path)
        dist = result.stats["animation_distribution"]
        assert dist["ken_burns"] == 2
        assert dist["zoom_in"] == 1
        assert dist["pan_left"] == 1

    def test_summary_output(self, tmp_path: Path) -> None:
        rows = [["reimu", "テスト", "", "ken_burns"]]
        csv_path = _write_csv(tmp_path / "s.csv", rows)
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(csv_path)
        summary = result.summary()
        assert "[PASS]" in summary
        assert "reimu" in summary


# ---------------------------------------------------------------------------
# CSV read error & row validation branches
# ---------------------------------------------------------------------------

class TestCsvReadError:
    def test_unreadable_csv(self, tmp_path: Path) -> None:
        """バイナリファイルをCSVとして読むとエラー。"""
        bad_file = tmp_path / "bad.csv"
        bad_file.write_bytes(b"\x80\x81\x82\x83" * 100)
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(bad_file)
        # エラーまたは空CSVとして扱われる
        assert not result.passed or any(i.code in ("CSV_READ_ERROR", "EMPTY_CSV") for i in result.issues)


class TestRowValidationBranches:
    def test_insufficient_columns(self, tmp_path: Path) -> None:
        """1列だけの行はINSUFFICIENT_COLUMNS。"""
        rows = [["only_one_column"]]
        csv_path = _write_csv(tmp_path / "bad_cols.csv", rows)
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(csv_path)
        assert any(i.code == "INSUFFICIENT_COLUMNS" for i in result.issues)

    def test_empty_speaker_warning(self, tmp_path: Path) -> None:
        """speaker が空の行は警告。"""
        rows = [["", "テキスト"]]
        csv_path = _write_csv(tmp_path / "no_speaker.csv", rows)
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(csv_path)
        assert any(i.code == "EMPTY_SPEAKER" for i in result.issues)

    def test_empty_text_warning(self, tmp_path: Path) -> None:
        """text が空の行は警告。"""
        rows = [["Speaker", ""]]
        csv_path = _write_csv(tmp_path / "no_text.csv", rows)
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(csv_path)
        assert any(i.code == "EMPTY_TEXT" for i in result.issues)

    def test_image_not_found_warning(self, tmp_path: Path) -> None:
        """存在しない画像パスは警告。"""
        rows = [["Speaker", "Text", "/nonexistent/img.jpg"]]
        csv_path = _write_csv(tmp_path / "bad_img.csv", rows)
        v = ExportValidator(check_image_exists=True)
        result = v.validate_csv(csv_path)
        assert any(i.code == "IMAGE_NOT_FOUND" for i in result.issues)

    def test_invalid_animation_warning(self, tmp_path: Path) -> None:
        """不正なアニメーション種別は警告。"""
        rows = [["Speaker", "Text", "", "flying_rainbow"]]
        csv_path = _write_csv(tmp_path / "bad_anim.csv", rows)
        v = ExportValidator(check_image_exists=False)
        result = v.validate_csv(csv_path)
        assert any(i.code == "INVALID_ANIMATION" for i in result.issues)


class TestTemplateConsistencyBranches:
    def test_pan_without_zoom_ratio(self, tmp_path: Path) -> None:
        """pan_left 使用時に pan_zoom_ratio がテンプレートに未定義だと警告。"""
        template = {
            "speaker_colors": ["#FFF"],
            "animation": {"ken_burns_zoom_ratio": 1.05},  # pan_zoom_ratio なし
            "timing": {},
            "subtitle": {},
        }
        rows = [["s", "t", "", "pan_left"]]
        csv_path = _write_csv(tmp_path / "pan.csv", rows)
        v = ExportValidator(template=template, check_image_exists=False)
        result = v.validate_csv(csv_path)
        assert any(i.code == "TEMPLATE_MISSING_PAN_CONFIG" for i in result.issues)

    def test_no_template_skips_consistency(self, tmp_path: Path) -> None:
        """テンプレートがなければtemplate consistency チェックをスキップ。"""
        rows = [["s", "t", "", "pan_left"]]
        csv_path = _write_csv(tmp_path / "no_tmpl.csv", rows)
        v = ExportValidator(template=None, check_image_exists=False)
        result = v.validate_csv(csv_path)
        assert not any(i.code == "TEMPLATE_MISSING_PAN_CONFIG" for i in result.issues)
