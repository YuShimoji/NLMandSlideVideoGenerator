"""スタイルテンプレートマネージャーテスト (SP-031)"""
import json
from pathlib import Path

import pytest

from core.style_template import (
    StyleTemplate,
    StyleTemplateManager,
    create_template_variant,
    save_template,
)


def _write_template(path: Path, data: dict) -> Path:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _valid_template_data(name: str = "test") -> dict:
    return {
        "version": "1.0.0",
        "metadata": {"name": name, "description": f"{name} template"},
        "subtitle": {"font_size": 48, "bold": True},
        "speaker_colors": ["#FFFFFF", "#FFFF64"],
        "animation": {"ken_burns_zoom_ratio": 1.05},
        "timing": {"crossfade_seconds": 0.5, "default_duration_seconds": 3.0},
        "validation": {"max_total_duration_seconds": 3600},
    }


class TestStyleTemplate:
    def test_speaker_color_cycle(self) -> None:
        t = StyleTemplate(name="test", speaker_colors=["#FFF", "#000"])
        assert t.get_speaker_color(0) == "#FFF"
        assert t.get_speaker_color(1) == "#000"
        assert t.get_speaker_color(2) == "#FFF"  # cycle

    def test_speaker_color_empty(self) -> None:
        t = StyleTemplate(name="test")
        assert t.get_speaker_color(0) == "#FFFFFF"

    def test_to_dict(self) -> None:
        t = StyleTemplate(
            name="test",
            subtitle={"font_size": 48},
            speaker_colors=["#FFF"],
        )
        d = t.to_dict()
        assert d["metadata"]["name"] == "test"
        assert d["subtitle"]["font_size"] == 48
        assert d["speaker_colors"] == ["#FFF"]


class TestStyleTemplateManager:
    def test_load_file(self, tmp_path: Path) -> None:
        data = _valid_template_data("custom")
        path = _write_template(tmp_path / "style_template_custom.json", data)
        mgr = StyleTemplateManager(config_dir=tmp_path)
        template = mgr.load_file(path)
        assert template is not None
        assert template.name == "custom"
        assert template.subtitle["font_size"] == 48

    def test_load_all(self, tmp_path: Path) -> None:
        _write_template(
            tmp_path / "style_template.json", _valid_template_data("default")
        )
        _write_template(
            tmp_path / "style_template_cinematic.json", _valid_template_data("cinematic")
        )
        mgr = StyleTemplateManager(config_dir=tmp_path)
        count = mgr.load_all()
        assert count == 2
        assert "default" in mgr.list_templates()
        assert "cinematic" in mgr.list_templates()

    def test_load_all_ignores_non_matching(self, tmp_path: Path) -> None:
        _write_template(
            tmp_path / "style_template.json", _valid_template_data("default")
        )
        _write_template(
            tmp_path / "other_config.json", {"unrelated": True}
        )
        mgr = StyleTemplateManager(config_dir=tmp_path)
        count = mgr.load_all()
        assert count == 1

    def test_get_default(self, tmp_path: Path) -> None:
        _write_template(
            tmp_path / "style_template.json", _valid_template_data("default")
        )
        mgr = StyleTemplateManager(config_dir=tmp_path)
        mgr.load_all()
        template = mgr.get()
        assert template is not None
        assert template.name == "default"

    def test_get_by_name(self, tmp_path: Path) -> None:
        _write_template(
            tmp_path / "style_template.json", _valid_template_data("default")
        )
        _write_template(
            tmp_path / "style_template_alt.json", _valid_template_data("alt")
        )
        mgr = StyleTemplateManager(config_dir=tmp_path)
        mgr.load_all()
        assert mgr.get("alt") is not None
        assert mgr.get("alt").name == "alt"

    def test_get_nonexistent_returns_none(self, tmp_path: Path) -> None:
        mgr = StyleTemplateManager(config_dir=tmp_path)
        assert mgr.get("nonexistent") is None

    def test_get_or_default_fallback(self, tmp_path: Path) -> None:
        mgr = StyleTemplateManager(config_dir=tmp_path)
        template = mgr.get_or_default("nonexistent")
        assert template.name == "builtin_default"
        assert len(template.speaker_colors) == 6

    def test_set_default(self, tmp_path: Path) -> None:
        _write_template(
            tmp_path / "style_template.json", _valid_template_data("default")
        )
        _write_template(
            tmp_path / "style_template_alt.json", _valid_template_data("alt")
        )
        mgr = StyleTemplateManager(config_dir=tmp_path)
        mgr.load_all()
        assert mgr.set_default("alt")
        assert mgr.get().name == "alt"

    def test_nonexistent_dir(self) -> None:
        mgr = StyleTemplateManager(config_dir=Path("/nonexistent/dir"))
        count = mgr.load_all()
        assert count == 0


class TestSchemaValidation:
    def test_valid_schema(self) -> None:
        data = _valid_template_data()
        errors = StyleTemplateManager.validate_schema(data)
        assert errors == []

    def test_missing_section(self) -> None:
        data = {"subtitle": {}, "speaker_colors": [], "animation": {}}
        errors = StyleTemplateManager.validate_schema(data)
        assert any("timing" in e for e in errors)

    def test_invalid_color_format(self) -> None:
        data = _valid_template_data()
        data["speaker_colors"] = ["not_a_color"]
        errors = StyleTemplateManager.validate_schema(data)
        assert any("カラーコード" in e for e in errors)

    def test_invalid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "style_template_bad.json"
        path.write_text("{invalid json", encoding="utf-8")
        mgr = StyleTemplateManager(config_dir=tmp_path)
        template = mgr.load_file(path)
        assert template is None


class TestTemplateVariant:
    def test_create_variant(self) -> None:
        base = StyleTemplate(
            name="base",
            subtitle={"font_size": 48, "bold": True},
            speaker_colors=["#FFF"],
            animation={"ken_burns_zoom_ratio": 1.05},
            timing={"crossfade_seconds": 0.5},
        )
        variant = create_template_variant(base, "large", {
            "subtitle": {"font_size": 64},
        })
        assert variant.name == "large"
        assert variant.subtitle["font_size"] == 64
        assert variant.subtitle["bold"] is True  # base preserved
        assert variant.animation["ken_burns_zoom_ratio"] == 1.05


class TestSaveTemplate:
    def test_save_and_reload(self, tmp_path: Path) -> None:
        template = StyleTemplate(
            name="saved",
            subtitle={"font_size": 48},
            speaker_colors=["#FFF"],
            animation={"ken_burns_zoom_ratio": 1.05},
            timing={"crossfade_seconds": 0.5},
        )
        out = save_template(template, tmp_path / "style_template_saved.json")
        assert out.exists()

        mgr = StyleTemplateManager(config_dir=tmp_path)
        loaded = mgr.load_file(out)
        assert loaded is not None
        assert loaded.name == "saved"
        assert loaded.subtitle["font_size"] == 48


class TestRealTemplates:
    """実際のconfig/テンプレートファイルの読み込みテスト。"""

    def test_load_project_templates(self) -> None:
        mgr = StyleTemplateManager()  # default: PROJECT_ROOT/config
        count = mgr.load_all()
        assert count >= 1  # at least style_template.json
        default = mgr.get("default")
        assert default is not None
        assert len(default.speaker_colors) >= 4
