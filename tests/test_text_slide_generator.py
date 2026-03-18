"""TextSlideGenerator テスト (SP-033 Phase 3)"""
import pytest
from pathlib import Path
from unittest.mock import patch

from core.visual.text_slide_generator import TextSlideGenerator


DARK_THEME = {
    "background": (20, 20, 25),
    "title_color": (235, 235, 235),
    "speaker_color": (180, 200, 255),
    "body_color": (200, 200, 200),
    "label_color": (120, 120, 130),
    "accent_color": (100, 150, 255),
}


@pytest.fixture
def gen(tmp_path: Path) -> TextSlideGenerator:
    return TextSlideGenerator(output_dir=tmp_path / "slides", theme=DARK_THEME)


class TestGenerate:
    def test_creates_png_file(self, gen: TextSlideGenerator) -> None:
        seg = {"section": "導入", "content": "AIの最新動向について解説します。"}
        path = gen.generate(seg, index=0)
        assert path.exists()
        assert path.suffix == ".png"

    def test_png_dimensions(self, gen: TextSlideGenerator) -> None:
        from PIL import Image
        seg = {"section": "テスト", "key_points": ["ポイント1", "ポイント2"]}
        path = gen.generate(seg, index=1)
        img = Image.open(path)
        assert img.size == (1920, 1080)

    def test_cache_hit(self, gen: TextSlideGenerator) -> None:
        seg = {"section": "キャッシュテスト", "content": "同一内容"}
        path1 = gen.generate(seg, index=5)
        path2 = gen.generate(seg, index=5)
        assert path1 == path2

    def test_different_content_different_files(self, gen: TextSlideGenerator) -> None:
        seg1 = {"section": "A", "content": "内容A"}
        seg2 = {"section": "B", "content": "内容B"}
        path1 = gen.generate(seg1, index=0)
        path2 = gen.generate(seg2, index=1)
        assert path1 != path2

    def test_empty_segment(self, gen: TextSlideGenerator) -> None:
        seg: dict = {}
        path = gen.generate(seg, index=0)
        assert path.exists()

    def test_key_points_rendered(self, gen: TextSlideGenerator) -> None:
        seg = {
            "section": "量子コンピュータ",
            "key_points": ["超電導量子ビット", "エラー訂正", "実用化ロードマップ"],
        }
        path = gen.generate(seg, index=2)
        assert path.exists()
        # PNG should be non-trivial size (not just a tiny blank)
        assert path.stat().st_size > 1000

    def test_speaker_label(self, gen: TextSlideGenerator) -> None:
        seg = {
            "section": "議論",
            "speaker": "れいむ",
            "content": "これについてどう思いますか？",
        }
        path = gen.generate(seg, index=3)
        assert path.exists()


class TestGenerateBatch:
    def test_batch_returns_correct_count(self, gen: TextSlideGenerator) -> None:
        segments = [
            {"section": f"Section {i}", "content": f"Content {i}"}
            for i in range(5)
        ]
        paths = gen.generate_batch(segments)
        assert len(paths) == 5
        assert all(p.exists() for p in paths)

    def test_batch_with_indices(self, gen: TextSlideGenerator) -> None:
        segments = [
            {"section": "A", "content": "aaa"},
            {"section": "B", "content": "bbb"},
        ]
        paths = gen.generate_batch(segments, indices=[10, 20])
        assert len(paths) == 2
        assert "010" in paths[0].name
        assert "020" in paths[1].name


class TestTextWrapping:
    def test_split_for_wrap_japanese(self) -> None:
        result = TextSlideGenerator._split_for_wrap("日本語テスト")
        assert result == ["日", "本", "語", "テ", "ス", "ト"]

    def test_split_for_wrap_english(self) -> None:
        result = TextSlideGenerator._split_for_wrap("hello world")
        assert "hello" in result
        assert " " in result
        assert "world" in result

    def test_split_for_wrap_mixed(self) -> None:
        result = TextSlideGenerator._split_for_wrap("AI技術")
        assert "AI" in result
        assert "技" in result
        assert "術" in result


class TestCacheKey:
    def test_deterministic(self) -> None:
        key1 = TextSlideGenerator._cache_key("s", "c", ["a"])
        key2 = TextSlideGenerator._cache_key("s", "c", ["a"])
        assert key1 == key2

    def test_different_inputs(self) -> None:
        key1 = TextSlideGenerator._cache_key("s1", "c", [])
        key2 = TextSlideGenerator._cache_key("s2", "c", [])
        assert key1 != key2

    def test_length(self) -> None:
        key = TextSlideGenerator._cache_key("section", "content", ["kp1", "kp2"])
        assert len(key) == 8


class TestThemeFallback:
    def test_custom_theme(self, tmp_path: Path) -> None:
        custom = {
            "background": (255, 0, 0),
            "title_color": (255, 255, 255),
            "body_color": (200, 200, 200),
            "label_color": (100, 100, 100),
            "accent_color": (0, 255, 0),
        }
        gen = TextSlideGenerator(output_dir=tmp_path, theme=custom)
        seg = {"section": "Red BG", "content": "test"}
        path = gen.generate(seg, index=0)
        assert path.exists()

        from PIL import Image
        img = Image.open(path)
        # Top-left corner should be red background
        pixel = img.getpixel((0, 0))
        assert pixel == (255, 0, 0)


class TestSpeakerMappingCache:
    """speaker_mapping適用後のキャッシュが話者名変更を反映することを検証。"""

    def test_different_speaker_produces_different_slide(self, gen: TextSlideGenerator) -> None:
        """同一content/sectionでもspeakerが異なれば別スライドを生成する。"""
        seg_host1 = {"section": "テスト", "content": "内容", "speaker": "Host1"}
        seg_reimu = {"section": "テスト", "content": "内容", "speaker": "れいむ"}
        path1 = gen.generate(seg_host1, index=0)
        path2 = gen.generate(seg_reimu, index=0)
        # 異なるspeakerなので異なるファイルが生成される
        assert path1 != path2
        assert path1.exists()
        assert path2.exists()

    def test_cache_key_includes_speaker(self) -> None:
        """_cache_keyがspeakerを含むことを確認。"""
        key1 = TextSlideGenerator._cache_key("s", "c", [], "Host1")
        key2 = TextSlideGenerator._cache_key("s", "c", [], "れいむ")
        assert key1 != key2

    def test_cache_key_backward_compat(self) -> None:
        """speaker省略時も動作する (後方互換)。"""
        key1 = TextSlideGenerator._cache_key("s", "c", [])
        key2 = TextSlideGenerator._cache_key("s", "c", [], "")
        assert key1 == key2
