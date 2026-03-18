"""TextSlideGenerator テスト (SP-033 Phase 3 + SP-041)"""
import pytest
from pathlib import Path
from unittest.mock import patch

from core.visual.text_slide_generator import (
    TextSlideGenerator,
    LAYOUT_STANDARD,
    LAYOUT_EMPHASIS,
    LAYOUT_TWOCOLUMN,
    LAYOUT_STATS,
    EMPHASIS_CONTENT_MAX_LEN,
    TWOCOLUMN_MIN_KEYPOINTS,
    _PRESET_THEME_MAP,
    _PRESET_LAYOUT_PRIORITY,
)


DARK_THEME = {
    "background": (20, 20, 25),
    "gradient_top": (25, 25, 35),
    "gradient_bottom": (12, 12, 18),
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


class TestSelectLayout:
    """SP-041: レイアウト自動選択テスト。"""

    def test_short_content_no_keypoints_returns_emphasis(self) -> None:
        result = TextSlideGenerator._select_layout("短いテキスト", [])
        assert result == LAYOUT_EMPHASIS

    def test_empty_content_no_keypoints_returns_emphasis(self) -> None:
        result = TextSlideGenerator._select_layout("", [])
        assert result == LAYOUT_EMPHASIS

    def test_long_content_no_keypoints_returns_standard(self) -> None:
        long_text = "A" * EMPHASIS_CONTENT_MAX_LEN
        result = TextSlideGenerator._select_layout(long_text, [])
        assert result == LAYOUT_STANDARD

    def test_with_keypoints_returns_standard(self) -> None:
        result = TextSlideGenerator._select_layout("短い", ["point1", "point2"])
        assert result == LAYOUT_STANDARD

    def test_short_content_with_keypoints_returns_standard(self) -> None:
        result = TextSlideGenerator._select_layout("短い", ["point1"])
        assert result == LAYOUT_STANDARD


class TestGradientBackground:
    """SP-041: グラデーション背景テスト。"""

    def test_gradient_applied(self, gen: TextSlideGenerator) -> None:
        from PIL import Image
        seg = {"section": "テスト", "content": "短い引用"}
        path = gen.generate(seg, index=100)
        img = Image.open(path)
        # 上端と下端のピクセル色が異なる (グラデーション)
        top_pixel = img.getpixel((self.width // 2, 0))
        bottom_pixel = img.getpixel((self.width // 2, self.height - 1))
        assert top_pixel != bottom_pixel

    @property
    def width(self) -> int:
        return 1920

    @property
    def height(self) -> int:
        return 1080

    def test_gradient_without_theme_keys(self, tmp_path: Path) -> None:
        """gradient_top/bottom がないテーマでもエラーにならない。"""
        no_gradient_theme = {
            "background": (50, 50, 50),
            "title_color": (255, 255, 255),
            "body_color": (200, 200, 200),
            "label_color": (100, 100, 100),
            "accent_color": (0, 255, 0),
        }
        gen = TextSlideGenerator(output_dir=tmp_path, theme=no_gradient_theme)
        seg = {"section": "No gradient", "content": "test"}
        path = gen.generate(seg, index=0)
        assert path.exists()
        from PIL import Image
        img = Image.open(path)
        # 単色背景のまま (上下同色)
        top_pixel = img.getpixel((960, 0))
        bottom_pixel = img.getpixel((960, 1079))
        assert top_pixel == bottom_pixel == (50, 50, 50)


class TestEmphasisLayout:
    """SP-041: Emphasis レイアウト描画テスト。"""

    def test_emphasis_generates_png(self, gen: TextSlideGenerator) -> None:
        seg = {"section": "結論", "content": "AIは未来を変える", "speaker": "れいむ"}
        path = gen.generate(seg, index=200)
        assert path.exists()
        assert path.stat().st_size > 1000

    def test_emphasis_dimensions(self, gen: TextSlideGenerator) -> None:
        from PIL import Image
        seg = {"section": "引用", "content": "短い引用文"}
        path = gen.generate(seg, index=201)
        img = Image.open(path)
        assert img.size == (1920, 1080)

    def test_emphasis_without_content(self, gen: TextSlideGenerator) -> None:
        """content なしでも section だけで描画される。"""
        seg = {"section": "まとめ"}
        path = gen.generate(seg, index=202)
        assert path.exists()

    def test_emphasis_with_speaker(self, gen: TextSlideGenerator) -> None:
        seg = {"section": "", "content": "名言です", "speaker": "まりさ"}
        path = gen.generate(seg, index=203)
        assert path.exists()

    def test_standard_for_long_content(self, gen: TextSlideGenerator) -> None:
        """長い content は Standard レイアウトになる。"""
        long = "これは非常に長いテキストであり" * 5
        seg = {"section": "詳細", "content": long}
        path = gen.generate(seg, index=204)
        assert path.exists()

    def test_standard_for_keypoints(self, gen: TextSlideGenerator) -> None:
        """key_points がある場合は Standard レイアウトになる。"""
        seg = {
            "section": "概要",
            "content": "短い",
            "key_points": ["ポイント1", "ポイント2"],
        }
        path = gen.generate(seg, index=205)
        assert path.exists()


class TestSelectLayoutExtended:
    """SP-041 Phase 2: TwoColumn / Stats レイアウト選択テスト。"""

    def test_many_keypoints_returns_twocolumn(self) -> None:
        kps = [f"point{i}" for i in range(TWOCOLUMN_MIN_KEYPOINTS)]
        result = TextSlideGenerator._select_layout("content", kps)
        assert result == LAYOUT_TWOCOLUMN

    def test_three_keypoints_returns_standard(self) -> None:
        kps = ["a", "b", "c"]
        result = TextSlideGenerator._select_layout("content", kps)
        assert result == LAYOUT_STANDARD

    def test_percentage_returns_stats(self) -> None:
        result = TextSlideGenerator._select_layout("成長率は150%に達した", [])
        assert result == LAYOUT_STATS

    def test_yen_amount_returns_stats(self) -> None:
        result = TextSlideGenerator._select_layout("売上は$500に到達", [])
        assert result == LAYOUT_STATS

    def test_japanese_unit_returns_stats(self) -> None:
        result = TextSlideGenerator._select_layout("利用者が500万人を突破", [])
        assert result == LAYOUT_STATS

    def test_comma_number_returns_stats(self) -> None:
        result = TextSlideGenerator._select_layout("参加者は1,200,000人", [])
        assert result == LAYOUT_STATS

    def test_no_number_short_returns_emphasis(self) -> None:
        result = TextSlideGenerator._select_layout("重要な結論", [])
        assert result == LAYOUT_EMPHASIS

    def test_stats_priority_over_emphasis(self) -> None:
        """数値を含む短い文は Stats が Emphasis より優先される。"""
        result = TextSlideGenerator._select_layout("成長率50%", [])
        assert result == LAYOUT_STATS

    def test_twocolumn_priority_over_stats(self) -> None:
        """key_points >= 4 なら数値があっても TwoColumn。"""
        kps = [f"p{i}" for i in range(5)]
        result = TextSlideGenerator._select_layout("成長率50%", kps)
        assert result == LAYOUT_TWOCOLUMN


class TestTwoColumnLayout:
    """SP-041 Phase 2: TwoColumn レイアウト描画テスト。"""

    def test_twocolumn_generates_png(self, gen: TextSlideGenerator) -> None:
        seg = {
            "section": "主要ポイント",
            "key_points": ["ポイント1", "ポイント2", "ポイント3", "ポイント4"],
            "speaker": "れいむ",
        }
        path = gen.generate(seg, index=300)
        assert path.exists()
        assert path.stat().st_size > 1000

    def test_twocolumn_dimensions(self, gen: TextSlideGenerator) -> None:
        from PIL import Image
        seg = {
            "section": "分析",
            "key_points": ["A", "B", "C", "D", "E"],
        }
        path = gen.generate(seg, index=301)
        img = Image.open(path)
        assert img.size == (1920, 1080)

    def test_twocolumn_with_content(self, gen: TextSlideGenerator) -> None:
        seg = {
            "section": "詳細分析",
            "content": "補足テキスト",
            "key_points": ["1", "2", "3", "4"],
        }
        path = gen.generate(seg, index=302)
        assert path.exists()

    def test_twocolumn_many_keypoints(self, gen: TextSlideGenerator) -> None:
        """大量の key_points でもクラッシュしない。"""
        seg = {
            "section": "大量ポイント",
            "key_points": [f"ポイント{i}" for i in range(20)],
        }
        path = gen.generate(seg, index=303)
        assert path.exists()


class TestStatsLayout:
    """SP-041 Phase 2: Stats レイアウト描画テスト。"""

    def test_stats_generates_png(self, gen: TextSlideGenerator) -> None:
        seg = {"section": "成長", "content": "前年比150%の成長を達成"}
        path = gen.generate(seg, index=400)
        assert path.exists()
        assert path.stat().st_size > 1000

    def test_stats_dimensions(self, gen: TextSlideGenerator) -> None:
        from PIL import Image
        seg = {"section": "売上", "content": "売上は$500に到達した"}
        path = gen.generate(seg, index=401)
        img = Image.open(path)
        assert img.size == (1920, 1080)

    def test_stats_japanese_unit(self, gen: TextSlideGenerator) -> None:
        seg = {"section": "ユーザー数", "content": "利用者が500万人を突破しました"}
        path = gen.generate(seg, index=402)
        assert path.exists()

    def test_stats_with_speaker(self, gen: TextSlideGenerator) -> None:
        seg = {
            "section": "データ",
            "content": "処理速度は3倍に向上",
            "speaker": "まりさ",
        }
        path = gen.generate(seg, index=403)
        assert path.exists()

    def test_stats_comma_number(self, gen: TextSlideGenerator) -> None:
        seg = {"section": "参加者", "content": "累計1,200,000人が参加"}
        path = gen.generate(seg, index=404)
        assert path.exists()


class TestStylePresetIntegration:
    """SP-041 Phase 3: スタイルプリセット連携テスト。"""

    def test_news_preset_favors_stats_layout(self) -> None:
        content = "市場は前年比30%増、売上1,000億円を突破"
        layout = TextSlideGenerator._select_layout(content, [], style_preset="news")
        assert layout == LAYOUT_STATS

    def test_educational_preset_favors_twocolumn(self) -> None:
        kps = ["ポイント1", "ポイント2", "ポイント3", "ポイント4"]
        layout = TextSlideGenerator._select_layout("内容", kps, style_preset="educational")
        assert layout == LAYOUT_TWOCOLUMN

    def test_summary_preset_favors_emphasis(self) -> None:
        content = "短いまとめ"
        layout = TextSlideGenerator._select_layout(content, [], style_preset="summary")
        assert layout == LAYOUT_EMPHASIS

    def test_news_preset_falls_back_to_standard(self) -> None:
        content = "普通の長さのニュース記事で数値なし。" * 3
        layout = TextSlideGenerator._select_layout(content, [], style_preset="news")
        assert layout == LAYOUT_STANDARD

    def test_no_preset_uses_default_priority(self) -> None:
        content = "市場は前年比30%増"
        layout = TextSlideGenerator._select_layout(content, [], style_preset=None)
        assert layout == LAYOUT_STATS

    def test_unknown_preset_uses_default_priority(self) -> None:
        content = "短い"
        layout = TextSlideGenerator._select_layout(content, [], style_preset="unknown_preset")
        assert layout == LAYOUT_EMPHASIS

    def test_preset_theme_map_has_expected_entries(self) -> None:
        assert "news" in _PRESET_THEME_MAP
        assert "educational" in _PRESET_THEME_MAP
        assert "summary" in _PRESET_THEME_MAP
        assert _PRESET_THEME_MAP["news"] == "blue"
        assert _PRESET_THEME_MAP["educational"] == "green"
        assert _PRESET_THEME_MAP["summary"] == "warm"

    def test_constructor_accepts_style_preset(self, tmp_path: Path) -> None:
        gen = TextSlideGenerator(output_dir=tmp_path, style_preset="news")
        assert gen.style_preset == "news"

    def test_preset_generates_png(self, tmp_path: Path) -> None:
        gen = TextSlideGenerator(output_dir=tmp_path, style_preset="educational")
        seg = {"section": "学習", "content": "これは教育用スライド", "key_points": ["a", "b"]}
        path = gen.generate(seg, index=500)
        assert path.exists()
        assert path.suffix == ".png"
