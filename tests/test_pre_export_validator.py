"""Pre-Export Validator テスト (core.editing.pre_export_validator)"""
import csv
from pathlib import Path

import pytest

from core.editing.pre_export_validator import (
    ValidationResult,
    _read_csv,
    validate_timeline_csv,
)


def _write_csv(path: Path, rows: list[list[str]]) -> Path:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)
    return path


class TestValidationResult:
    def test_default_valid(self):
        r = ValidationResult()
        assert r.valid is True
        assert r.errors == []
        assert r.warnings == []

    def test_summary_ok(self):
        r = ValidationResult()
        assert r.summary == "OK"

    def test_summary_errors_only(self):
        r = ValidationResult(errors=["e1", "e2"])
        assert r.summary == "errors=2"

    def test_summary_warnings_only(self):
        r = ValidationResult(warnings=["w1"])
        assert r.summary == "warnings=1"

    def test_summary_both(self):
        r = ValidationResult(errors=["e"], warnings=["w1", "w2"])
        assert r.summary == "errors=1, warnings=2"


class TestReadCsv:
    def test_valid_4col(self, tmp_path: Path):
        rows = [["reimu", "hello", "/img.jpg", "ken_burns"]]
        csv_path = _write_csv(tmp_path / "test.csv", rows)
        result = _read_csv(csv_path)
        assert len(result) == 1
        assert result[0]["speaker"] == "reimu"
        assert result[0]["text"] == "hello"
        assert result[0]["image_path"] == "/img.jpg"
        assert result[0]["animation_type"] == "ken_burns"

    def test_2col_csv(self, tmp_path: Path):
        rows = [["reimu", "hello"]]
        csv_path = _write_csv(tmp_path / "test.csv", rows)
        result = _read_csv(csv_path)
        assert result[0]["image_path"] == ""
        assert result[0]["animation_type"] == ""

    def test_empty_csv(self, tmp_path: Path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("", encoding="utf-8")
        result = _read_csv(csv_path)
        assert result == []

    def test_skips_empty_rows(self, tmp_path: Path):
        csv_path = tmp_path / "gaps.csv"
        csv_path.write_text("reimu,hello,,\n\nmarisa,world,,\n", encoding="utf-8")
        result = _read_csv(csv_path)
        assert len(result) == 2

    def test_nonexistent_file(self, tmp_path: Path):
        result = _read_csv(tmp_path / "no_such.csv")
        assert result == []


class TestValidateTimelineCsv:
    def test_missing_file(self, tmp_path: Path):
        result = validate_timeline_csv(tmp_path / "missing.csv")
        assert result.valid is False
        assert any("not found" in e for e in result.errors)

    def test_empty_csv(self, tmp_path: Path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("", encoding="utf-8")
        result = validate_timeline_csv(csv_path)
        assert result.valid is False
        assert any("empty" in e.lower() for e in result.errors)

    def test_valid_csv(self, tmp_path: Path):
        img = tmp_path / "img.jpg"
        img.write_bytes(b"fake")
        rows = [
            ["reimu", "text1", str(img), "ken_burns"],
            ["marisa", "text2", str(img), "zoom_in"],
        ]
        csv_path = _write_csv(tmp_path / "valid.csv", rows)
        result = validate_timeline_csv(csv_path)
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_empty_text_and_image_warning(self, tmp_path: Path):
        rows = [["reimu", "", "", "ken_burns"]]
        csv_path = _write_csv(tmp_path / "empty.csv", rows)
        result = validate_timeline_csv(csv_path)
        assert any("empty text" in w.lower() for w in result.warnings)

    def test_image_not_found_warning(self, tmp_path: Path):
        rows = [["reimu", "text", "/nonexistent/img.jpg", "ken_burns"]]
        csv_path = _write_csv(tmp_path / "bad_img.csv", rows)
        result = validate_timeline_csv(csv_path)
        assert any("image not found" in w.lower() for w in result.warnings)

    def test_unknown_animation_warning(self, tmp_path: Path):
        rows = [["reimu", "text", "", "invalid_anim"]]
        csv_path = _write_csv(tmp_path / "bad_anim.csv", rows)
        result = validate_timeline_csv(csv_path)
        assert any("unknown animation" in w.lower() for w in result.warnings)

    def test_valid_animation_types(self, tmp_path: Path):
        valid_types = ["ken_burns", "zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down", "static", ""]
        rows = [[f"s{i}", f"text{i}", "", t] for i, t in enumerate(valid_types)]
        csv_path = _write_csv(tmp_path / "all_anims.csv", rows)
        result = validate_timeline_csv(csv_path)
        assert not any("unknown animation" in w.lower() for w in result.warnings)

    def test_large_csv_warning(self, tmp_path: Path):
        rows = [["s", "text", "", ""] for _ in range(5001)]
        csv_path = _write_csv(tmp_path / "large.csv", rows)
        result = validate_timeline_csv(csv_path)
        assert any("large csv" in w.lower() for w in result.warnings)

    def test_no_large_csv_warning_under_threshold(self, tmp_path: Path):
        rows = [["s", "text", "", ""] for _ in range(100)]
        csv_path = _write_csv(tmp_path / "ok.csv", rows)
        result = validate_timeline_csv(csv_path)
        assert not any("large csv" in w.lower() for w in result.warnings)
