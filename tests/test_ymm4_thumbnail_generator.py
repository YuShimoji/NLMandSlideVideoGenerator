#!/usr/bin/env python3
"""
テスト: YMM4テンプレートベースのサムネイル生成 (SP-037 Phase 3)
"""

import json
import pytest
import tempfile
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.thumbnails.ymm4_thumbnail_generator import Ymm4ThumbnailGenerator


@pytest.fixture
def sample_template_dir(tmp_path: Path) -> Path:
    """サンプルテンプレートを一時ディレクトリに作成する。"""
    tmpl_dir = tmp_path / "templates"
    tmpl_dir.mkdir()

    template = {
        "FilePath": "",
        "SelectedTimelineIndex": 0,
        "Timelines": [
            {
                "ID": "test-timeline",
                "Name": "テスト",
                "VideoInfo": {"FPS": 30, "Hz": 48000, "Width": 1920, "Height": 1080},
                "Items": [
                    {
                        "$type": "YukkuriMovieMaker.Project.Items.ImageItem, YukkuriMovieMaker",
                        "FilePath": "{{BACKGROUND}}",
                        "Frame": 0,
                        "Layer": 0,
                        "Length": 30,
                    },
                    {
                        "$type": "YukkuriMovieMaker.Project.Items.ImageItem, YukkuriMovieMaker",
                        "FilePath": "{{CHARACTER}}",
                        "Frame": 0,
                        "Layer": 1,
                        "Length": 30,
                    },
                    {
                        "$type": "YukkuriMovieMaker.Project.Items.TextItem, YukkuriMovieMaker",
                        "Text": "{{TITLE}}",
                        "Frame": 0,
                        "Layer": 2,
                        "Length": 30,
                    },
                    {
                        "$type": "YukkuriMovieMaker.Project.Items.TextItem, YukkuriMovieMaker",
                        "Text": "{{SUBTITLE}}",
                        "Frame": 0,
                        "Layer": 3,
                        "Length": 30,
                    },
                ],
            }
        ],
    }

    with open(tmpl_dir / "test_template.y4mmp", "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False)

    return tmpl_dir


@pytest.fixture
def generator(sample_template_dir: Path) -> Ymm4ThumbnailGenerator:
    return Ymm4ThumbnailGenerator(template_dir=sample_template_dir)


class TestYmm4ThumbnailGenerator:
    """基本機能テスト"""

    def test_discover_templates(self, generator: Ymm4ThumbnailGenerator):
        """テンプレート一覧の取得"""
        templates = generator.discover_templates()
        assert "test_template" in templates

    def test_discover_templates_empty_dir(self, tmp_path: Path):
        """空ディレクトリでは空リスト"""
        gen = Ymm4ThumbnailGenerator(template_dir=tmp_path)
        assert gen.discover_templates() == []

    def test_discover_templates_nonexistent_dir(self, tmp_path: Path):
        """存在しないディレクトリでは空リスト"""
        gen = Ymm4ThumbnailGenerator(template_dir=tmp_path / "nonexistent")
        assert gen.discover_templates() == []

    def test_load_template(self, generator: Ymm4ThumbnailGenerator):
        """テンプレートのロード"""
        data = generator.load_template("test_template")
        assert "Timelines" in data
        assert len(data["Timelines"][0]["Items"]) == 4

    def test_load_template_caching(self, generator: Ymm4ThumbnailGenerator):
        """テンプレートがキャッシュされる"""
        data1 = generator.load_template("test_template")
        data2 = generator.load_template("test_template")
        assert data1 is data2

    def test_load_template_not_found(self, generator: Ymm4ThumbnailGenerator):
        """存在しないテンプレートでFileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            generator.load_template("nonexistent")

    def test_list_placeholders(self, generator: Ymm4ThumbnailGenerator):
        """プレースホルダーの検出"""
        placeholders = generator.list_placeholders("test_template")
        assert "TITLE" in placeholders["text"]
        assert "SUBTITLE" in placeholders["text"]
        assert "BACKGROUND" in placeholders["image"]
        assert "CHARACTER" in placeholders["image"]

    def test_generate_basic(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """基本的なサムネイル生成"""
        output_dir = tmp_path / "output"
        result = generator.generate(
            template_name="test_template",
            output_dir=output_dir,
            replacements={
                "TITLE": "AI最新動向2026",
                "SUBTITLE": "機械学習の未来",
                "BACKGROUND": "C:/images/bg.png",
                "CHARACTER": "C:/images/reimu.png",
            },
        )

        assert result.exists()
        assert result.suffix == ".y4mmp"

        with open(result, "r", encoding="utf-8") as f:
            project = json.load(f)

        items = project["Timelines"][0]["Items"]

        # ImageItem のFilePath が差し替えられている
        assert items[0]["FilePath"] == "C:/images/bg.png"
        assert items[1]["FilePath"] == "C:/images/reimu.png"

        # TextItem のText が差し替えられている
        assert items[2]["Text"] == "AI最新動向2026"
        assert items[3]["Text"] == "機械学習の未来"

    def test_generate_partial_replacements(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """一部のプレースホルダーのみ差し替え"""
        output_dir = tmp_path / "output"
        result = generator.generate(
            template_name="test_template",
            output_dir=output_dir,
            replacements={"TITLE": "テストタイトル"},
        )

        with open(result, "r", encoding="utf-8") as f:
            project = json.load(f)

        items = project["Timelines"][0]["Items"]
        # TITLE は差し替え済み
        assert items[2]["Text"] == "テストタイトル"
        # SUBTITLE はプレースホルダーのまま
        assert items[3]["Text"] == "{{SUBTITLE}}"

    def test_generate_does_not_mutate_template(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """生成しても元テンプレートキャッシュは変更されない"""
        generator.load_template("test_template")

        generator.generate(
            template_name="test_template",
            output_dir=tmp_path / "out1",
            replacements={"TITLE": "Test1"},
        )

        # 再ロードして確認
        generator._templates.clear()
        data = generator.load_template("test_template")
        items = data["Timelines"][0]["Items"]
        assert items[2]["Text"] == "{{TITLE}}"

    def test_generate_output_filepath_updated(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """出力ファイルの FilePath が更新されている"""
        output_dir = tmp_path / "output"
        result = generator.generate(
            template_name="test_template",
            output_dir=output_dir,
            replacements={"TITLE": "テスト"},
        )

        with open(result, "r", encoding="utf-8") as f:
            project = json.load(f)

        assert project["FilePath"] == str(result.resolve())

    def test_generate_custom_filename(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """カスタムファイル名で出力"""
        output_dir = tmp_path / "output"
        result = generator.generate(
            template_name="test_template",
            output_dir=output_dir,
            replacements={"TITLE": "テスト"},
            output_filename="custom_thumbnail.y4mmp",
        )
        assert result.name == "custom_thumbnail.y4mmp"
        assert result.exists()


class TestYmm4ThumbnailGeneratorFromScript:
    """generate_from_script テスト"""

    def test_from_script_basic(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """台本データからサムネイル生成"""
        script = {
            "title": "量子コンピュータの衝撃",
            "segments": [
                {"content": "量子ビットの基本原理から応用まで", "duration": 30},
            ],
        }

        result = generator.generate_from_script(
            template_name="test_template",
            script=script,
            output_dir=tmp_path / "output",
            background_image="C:/images/quantum.png",
        )

        with open(result, "r", encoding="utf-8") as f:
            project = json.load(f)

        items = project["Timelines"][0]["Items"]
        assert items[2]["Text"] == "量子コンピュータの衝撃"
        assert "量子ビットの基本原理" in items[3]["Text"]
        assert items[0]["FilePath"] == str(Path("C:/images/quantum.png").resolve())

    def test_from_script_no_segments(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """セグメントなしの台本"""
        script = {"title": "テストタイトル", "segments": []}

        result = generator.generate_from_script(
            template_name="test_template",
            script=script,
            output_dir=tmp_path / "output",
        )

        with open(result, "r", encoding="utf-8") as f:
            project = json.load(f)

        items = project["Timelines"][0]["Items"]
        assert items[2]["Text"] == "テストタイトル"
        assert items[3]["Text"] == ""  # subtitle empty

    def test_from_script_long_subtitle_truncated(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """長いサブタイトルは40文字+...に切り詰め"""
        script = {
            "title": "テスト",
            "segments": [
                {"content": "あ" * 100, "duration": 30},
            ],
        }

        result = generator.generate_from_script(
            template_name="test_template",
            script=script,
            output_dir=tmp_path / "output",
        )

        with open(result, "r", encoding="utf-8") as f:
            project = json.load(f)

        subtitle = project["Timelines"][0]["Items"][3]["Text"]
        assert len(subtitle) == 43  # 40 chars + "..."
        assert subtitle.endswith("...")


class TestYmm4ThumbnailAssetCopy:
    """テンプレート素材コピーテスト"""

    def test_copy_assets(self, sample_template_dir: Path, tmp_path: Path):
        """テンプレート付随素材がコピーされる"""
        # テンプレートと同名のディレクトリに素材を配置
        assets_dir = sample_template_dir / "test_template"
        assets_dir.mkdir()
        (assets_dir / "overlay.png").write_bytes(b"fake png data")
        (assets_dir / "frame.png").write_bytes(b"fake frame data")

        gen = Ymm4ThumbnailGenerator(template_dir=sample_template_dir)
        output_dir = tmp_path / "output"
        gen.generate(
            template_name="test_template",
            output_dir=output_dir,
            replacements={"TITLE": "テスト"},
        )

        assert (output_dir / "overlay.png").exists()
        assert (output_dir / "frame.png").exists()

    def test_no_assets_dir_is_ok(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """素材ディレクトリがなくてもエラーにならない"""
        output_dir = tmp_path / "output"
        result = generator.generate(
            template_name="test_template",
            output_dir=output_dir,
            replacements={"TITLE": "テスト"},
        )
        assert result.exists()


class TestYmm4ThumbnailColorPreset:
    """色彩プリセット適用テスト (SP-037 Phase 4)"""

    def test_apply_color_preset_main_text(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """メインテキストに色彩プリセットが適用される"""
        output_dir = tmp_path / "output"
        result = generator.generate(
            template_name="test_template",
            output_dir=output_dir,
            replacements={"TITLE": "テスト", "SUBTITLE": "サブ"},
            color_preset="dark_red",
        )

        with open(result, "r", encoding="utf-8") as f:
            project = json.load(f)

        items = project["Timelines"][0]["Items"]
        # TITLE = メインテキスト → dark_red プリセットの色
        title_item = items[2]
        assert title_item["FontColor"] == "#FF0000"
        assert title_item["OutlineColor"] == "#FFFFFF"
        assert title_item["OutlineWidth"] == 5

    def test_apply_color_preset_sub_text(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """サブテキストに色彩プリセットが適用される"""
        output_dir = tmp_path / "output"
        result = generator.generate(
            template_name="test_template",
            output_dir=output_dir,
            replacements={"TITLE": "テスト", "SUBTITLE": "サブ"},
            color_preset="dark_red",
        )

        with open(result, "r", encoding="utf-8") as f:
            project = json.load(f)

        items = project["Timelines"][0]["Items"]
        sub_item = items[3]
        assert sub_item["FontColor"] == "#FFFFFF"
        assert sub_item["OutlineColor"] == "#333333"

    def test_all_presets_valid(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """全5プリセットが適用可能"""
        from src.core.thumbnails.ymm4_thumbnail_generator import COLOR_PRESETS
        for preset_name in COLOR_PRESETS:
            output_dir = tmp_path / f"output_{preset_name}"
            result = generator.generate(
                template_name="test_template",
                output_dir=output_dir,
                replacements={"TITLE": "テスト"},
                color_preset=preset_name,
            )
            assert result.exists()

    def test_unknown_preset_ignored(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """不明なプリセット名は警告のみでエラーにならない"""
        output_dir = tmp_path / "output"
        result = generator.generate(
            template_name="test_template",
            output_dir=output_dir,
            replacements={"TITLE": "テスト"},
            color_preset="nonexistent_preset",
        )
        assert result.exists()

    def test_list_color_presets(self):
        """色彩プリセット一覧の取得"""
        presets = Ymm4ThumbnailGenerator.list_color_presets()
        assert len(presets) == 5
        assert "dark_red" in presets
        assert "dark_yellow" in presets
        assert "map_white" in presets
        assert "high_contrast" in presets
        assert "warm_alert" in presets


class TestYmm4ThumbnailVariants:
    """バリエーション生成テスト (SP-037 Phase 4)"""

    def test_text_variants(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """テキストバリエーション生成"""
        output_dir = tmp_path / "output"
        results = generator.generate_variants(
            template_name="test_template",
            output_dir=output_dir,
            base_replacements={"TITLE": "ベース"},
            variant_texts=[
                {"TITLE": "バリエーション1"},
                {"TITLE": "バリエーション2"},
            ],
        )
        assert len(results) == 2
        assert all(p.exists() for p in results)

    def test_color_variants(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """色バリエーション生成"""
        output_dir = tmp_path / "output"
        results = generator.generate_variants(
            template_name="test_template",
            output_dir=output_dir,
            base_replacements={"TITLE": "テスト"},
            color_presets=["dark_red", "dark_yellow", "map_white"],
        )
        assert len(results) == 3

    def test_combined_variants(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """テキスト x 色 の組み合わせバリエーション"""
        output_dir = tmp_path / "output"
        results = generator.generate_variants(
            template_name="test_template",
            output_dir=output_dir,
            base_replacements={"SUBTITLE": "サブ"},
            variant_texts=[{"TITLE": "A"}, {"TITLE": "B"}],
            color_presets=["dark_red", "warm_alert"],
        )
        assert len(results) == 4  # 2 texts x 2 colors

    def test_no_variants_generates_one(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """バリエーション指定なしでも1つ生成"""
        output_dir = tmp_path / "output"
        results = generator.generate_variants(
            template_name="test_template",
            output_dir=output_dir,
            base_replacements={"TITLE": "テスト"},
        )
        assert len(results) == 1


class TestYmm4ThumbnailFromCopy:
    """generate_from_thumbnail_copy テスト (SP-037 Phase 4)"""

    def test_basic_from_copy(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """Gemini文言からサムネイル生成"""
        thumbnail_copy = {
            "main_text": "なぜAIは",
            "sub_text": "衝撃の理由を徹底解説",
            "label": "ゆっくり解説",
            "suggested_pattern": "A",
            "suggested_color": "dark_red",
        }
        # test_template しかないので suggested_pattern は無視されて test_template が使われる
        result = generator.generate_from_thumbnail_copy(
            thumbnail_copy=thumbnail_copy,
            output_dir=tmp_path / "output",
        )
        assert result.exists()

        with open(result, "r", encoding="utf-8") as f:
            project = json.load(f)

        items = project["Timelines"][0]["Items"]
        # TITLE/MAIN_TEXT 両方にセット → TITLE が差し替わる
        assert items[2]["Text"] == "なぜAIは"
        # SUBTITLE/SUB_TEXT 両方にセット → SUBTITLE が差し替わる
        assert items[3]["Text"] == "衝撃の理由を徹底解説"
        # dark_red プリセットが適用される
        assert items[2]["FontColor"] == "#FF0000"

    def test_explicit_template_override(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """テンプレート名を明示指定"""
        thumbnail_copy = {
            "main_text": "テスト",
            "sub_text": "サブ",
            "label": "解説",
            "suggested_pattern": "C",
            "suggested_color": "map_white",
        }
        result = generator.generate_from_thumbnail_copy(
            thumbnail_copy=thumbnail_copy,
            output_dir=tmp_path / "output",
            template_name="test_template",
        )
        assert result.exists()

    def test_with_images(self, generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """背景・キャラ画像指定"""
        thumbnail_copy = {
            "main_text": "テスト",
            "sub_text": "サブ",
            "label": "解説",
            "suggested_pattern": "A",
            "suggested_color": "high_contrast",
        }
        bg = tmp_path / "bg.png"
        bg.write_bytes(b"fake")

        result = generator.generate_from_thumbnail_copy(
            thumbnail_copy=thumbnail_copy,
            output_dir=tmp_path / "output",
            background_image=bg,
        )

        with open(result, "r", encoding="utf-8") as f:
            project = json.load(f)

        items = project["Timelines"][0]["Items"]
        assert str(bg.resolve()) in items[0]["FilePath"]

    def test_no_templates_raises(self, tmp_path: Path):
        """テンプレートが1つもない場合FileNotFoundError"""
        gen = Ymm4ThumbnailGenerator(template_dir=tmp_path / "empty_templates")
        (tmp_path / "empty_templates").mkdir()

        thumbnail_copy = {
            "main_text": "テスト", "sub_text": "サブ",
            "label": "解説", "suggested_pattern": "A",
            "suggested_color": "dark_red",
        }
        with pytest.raises(FileNotFoundError, match="テンプレートが1つも"):
            gen.generate_from_thumbnail_copy(
                thumbnail_copy=thumbnail_copy,
                output_dir=tmp_path / "output",
            )


class TestYmm4ThumbnailWithRealTemplate:
    """config/thumbnail_templates/ の実テンプレートでのテスト"""

    @pytest.fixture
    def real_generator(self) -> Ymm4ThumbnailGenerator:
        tmpl_dir = project_root / "config" / "thumbnail_templates"
        if not tmpl_dir.exists() or not list(tmpl_dir.glob("*.y4mmp")):
            pytest.skip("実テンプレートなし")
        return Ymm4ThumbnailGenerator(template_dir=tmpl_dir)

    def test_real_template_discover(self, real_generator: Ymm4ThumbnailGenerator):
        """実テンプレートが検出される"""
        templates = real_generator.discover_templates()
        assert len(templates) > 0

    def test_real_template_placeholders(self, real_generator: Ymm4ThumbnailGenerator):
        """実テンプレートのプレースホルダーが検出される"""
        templates = real_generator.discover_templates()
        for name in templates:
            placeholders = real_generator.list_placeholders(name)
            # 少なくともTITLEかBACKGROUNDがあるはず
            all_ph = placeholders["text"] + placeholders["image"]
            assert len(all_ph) > 0, f"テンプレート '{name}' にプレースホルダーがない"

    def test_real_template_generate(self, real_generator: Ymm4ThumbnailGenerator, tmp_path: Path):
        """実テンプレートでサムネイル生成"""
        templates = real_generator.discover_templates()
        name = templates[0]

        result = real_generator.generate(
            template_name=name,
            output_dir=tmp_path / "output",
            replacements={
                "TITLE": "テスト動画タイトル",
                "SUBTITLE": "サブタイトルテスト",
                "BACKGROUND": "C:/test/bg.png",
                "CHARACTER": "C:/test/char.png",
            },
        )

        assert result.exists()
        with open(result, "r", encoding="utf-8") as f:
            project = json.load(f)
        assert "Timelines" in project
