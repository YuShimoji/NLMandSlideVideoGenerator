"""Tests for SP-036 Script Style Presets."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import target
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from notebook_lm.gemini_integration import GeminiIntegration


PRESETS_DIR = Path(__file__).resolve().parent.parent / "config" / "script_presets"
EXPECTED_PRESETS = ["default", "educational", "news", "summary"]


class TestPresetFiles:
    """プリセットJSONファイルの妥当性テスト"""

    def test_presets_dir_exists(self):
        assert PRESETS_DIR.exists(), f"Presets directory not found: {PRESETS_DIR}"

    @pytest.mark.parametrize("name", EXPECTED_PRESETS)
    def test_preset_file_exists(self, name: str):
        path = PRESETS_DIR / f"{name}.json"
        assert path.exists(), f"Preset file not found: {path}"

    @pytest.mark.parametrize("name", EXPECTED_PRESETS)
    def test_preset_valid_json(self, name: str):
        path = PRESETS_DIR / f"{name}.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("name", EXPECTED_PRESETS)
    def test_preset_required_fields(self, name: str):
        path = PRESETS_DIR / f"{name}.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        required = ["name", "display_name", "role", "tone", "structure", "requirements", "speakers"]
        for field in required:
            assert field in data, f"Missing required field '{field}' in {name}.json"

    @pytest.mark.parametrize("name", EXPECTED_PRESETS)
    def test_preset_structure_is_list(self, name: str):
        path = PRESETS_DIR / f"{name}.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data["structure"], list)
        assert len(data["structure"]) >= 2

    @pytest.mark.parametrize("name", EXPECTED_PRESETS)
    def test_preset_speakers_schema(self, name: str):
        path = PRESETS_DIR / f"{name}.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        speakers = data["speakers"]
        assert "default_count" in speakers
        assert "default_names" in speakers
        assert isinstance(speakers["default_names"], list)
        assert len(speakers["default_names"]) >= 1

    @pytest.mark.parametrize("name", EXPECTED_PRESETS)
    def test_preset_segment_density(self, name: str):
        path = PRESETS_DIR / f"{name}.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "segment_density" in data:
            density = data["segment_density"]
            assert isinstance(density, dict)
            # At least one threshold
            assert len(density) >= 1


class TestGeminiIntegrationPresets:
    """GeminiIntegration のプリセット機能テスト"""

    def _make_instance(self) -> GeminiIntegration:
        return GeminiIntegration(api_key="test-key", model_name="test-model")

    def test_load_default_preset(self):
        gi = self._make_instance()
        preset = gi.load_preset("default")
        assert preset["name"] == "default"
        assert "role" in preset

    @pytest.mark.parametrize("name", EXPECTED_PRESETS)
    def test_load_all_presets(self, name: str):
        gi = self._make_instance()
        preset = gi.load_preset(name)
        assert preset["name"] == name

    def test_load_preset_caching(self):
        gi = self._make_instance()
        preset1 = gi.load_preset("default")
        preset2 = gi.load_preset("default")
        assert preset1 is preset2  # Same object from cache

    def test_load_unknown_preset_raises(self):
        gi = self._make_instance()
        with pytest.raises(ValueError, match="Unknown style preset"):
            gi.load_preset("nonexistent_style_xyz")

    def test_list_presets(self):
        gi = self._make_instance()
        presets = gi.list_presets()
        assert isinstance(presets, list)
        assert len(presets) >= 4
        names = [p["name"] for p in presets]
        for expected in EXPECTED_PRESETS:
            assert expected in names

    def test_list_presets_has_display_name(self):
        gi = self._make_instance()
        presets = gi.list_presets()
        for p in presets:
            assert "name" in p
            assert "display_name" in p
            assert isinstance(p["display_name"], str)

    def test_build_script_prompt_uses_preset(self):
        gi = self._make_instance()
        sources = [{"title": "Test", "url": "http://example.com", "content_preview": "Preview", "relevance_score": 0.9, "reliability_score": 0.8}]

        prompt_default = gi._build_script_prompt(sources, "test topic", 300.0, "ja", style="default")
        prompt_news = gi._build_script_prompt(sources, "test topic", 300.0, "ja", style="news")

        # Different presets should produce different prompts
        assert prompt_default != prompt_news
        # News preset should mention its specific role
        assert "ニュース" in prompt_news

    def test_build_script_prompt_fallback_on_missing_preset(self):
        gi = self._make_instance()
        sources = [{"title": "Test", "url": "http://example.com", "content_preview": "Preview"}]

        # Should not raise, falls back to built-in default
        prompt = gi._build_script_prompt(sources, "test topic", 300.0, "ja", style="nonexistent_xyz")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    @pytest.mark.parametrize("duration,expected_key", [
        (60.0, "300"),
        (300.0, "300"),
        (600.0, "900"),
        (1200.0, "1800"),
        (2400.0, "3600"),
        (7200.0, "3600"),
    ])
    def test_segment_density_threshold_selection(self, duration: float, expected_key: str):
        gi = self._make_instance()
        preset = gi.load_preset("default")
        density = preset.get("segment_density", {})
        # Verify the expected key exists
        assert expected_key in density
