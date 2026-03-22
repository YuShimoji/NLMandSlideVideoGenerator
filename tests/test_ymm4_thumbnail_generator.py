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
