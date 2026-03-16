#!/usr/bin/env python3
"""
テスト: サムネイル生成コンポーネントテスト
OpenSpec IThumbnailGeneratorの実装を検証
"""

import pytest
import asyncio
import json
from unittest.mock import Mock
from pathlib import Path
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.thumbnails import AIThumbnailGenerator, TemplateThumbnailGenerator
from src.video_editor.models import VideoInfo  # Changed from video_composer
from datetime import datetime
from src.slides.slide_generator import SlidesPackage

class TestAIThumbnailGenerator:
    """AIThumbnailGeneratorのテスト"""

    @pytest.fixture
    def generator(self):
        """テスト用のジェネレーターインスタンス"""
        return AIThumbnailGenerator()

    @pytest.fixture
    def mock_video_info(self):
        """モック動画情報"""
        return VideoInfo(
            file_path=Path("test_video.mp4"),
            duration=120.0,
            resolution=(1920, 1080),
            fps=30,
            file_size=10000000,
            has_subtitles=True,
            has_effects=True,
            created_at=datetime.now()
        )

    @pytest.fixture
    def mock_script(self):
        """モックスクリプトデータ"""
        return {
            "title": "テスト動画タイトル",
            "content": "これはテストコンテンツです。AI技術の最新動向について説明します。",
            "segments": [
                {
                    "text": "AI技術の進化",
                    "duration": 30,
                    "segment_id": "seg_1"
                },
                {
                    "text": "将来展望",
                    "duration": 45,
                    "segment_id": "seg_2"
                }
            ]
        }

    @pytest.fixture
    def mock_slides(self):
        """モックスライドパッケージ"""
        return SlidesPackage(
            presentation_id="test_presentation",
            slides=[
                Mock(title="タイトルスライド", content="AI技術の最新動向"),
                Mock(title="内容スライド1", content="技術の進化について"),
                Mock(title="内容スライド2", content="将来展望")
            ],
            total_slides=3
        )

    @pytest.mark.asyncio
    async def test_generate_basic(self, generator, mock_video_info, mock_script, mock_slides):
        """基本的なサムネイル生成テスト"""
        result = await generator.generate(
            video=mock_video_info,
            script=mock_script,
            slides=mock_slides,
            style="modern"
        )

        assert hasattr(result, 'file_path')
        assert hasattr(result, 'title_text')
        assert result.style == "modern"
        assert result.resolution == (1280, 720)
        assert result.file_path.exists()

    @pytest.mark.asyncio
    async def test_generate_different_styles(self, generator, mock_video_info, mock_script, mock_slides):
        """異なるスタイルでのサムネイル生成テスト"""
        for style in ["modern", "classic", "gaming", "educational"]:
            result = await generator.generate(
                video=mock_video_info,
                script=mock_script,
                slides=mock_slides,
                style=style
            )

            assert result.style == style
            assert result.file_path.exists()

    @pytest.mark.asyncio
    async def test_generate_empty_script(self, generator, mock_video_info, mock_slides):
        """空のスクリプトでのサムネイル生成テスト"""
        empty_script = {"title": "", "content": "", "segments": []}

        result = await generator.generate(
            video=mock_video_info,
            script=empty_script,
            slides=mock_slides,
            style="modern"
        )

        assert hasattr(result, 'file_path')
        assert result.file_path.exists()

    def test_generator_initialization(self, generator):
        """ジェネレーターの初期化テスト"""
        assert generator is not None
        assert hasattr(generator, 'generate')
        assert hasattr(generator, 'styles')

    @pytest.mark.asyncio
    async def test_content_extraction(self, generator, mock_script, mock_slides):
        """コンテンツ抽出機能のテスト"""
        title, subtitle = await generator._extract_content_info(mock_script, mock_slides)

        assert title == mock_script["title"]
        assert isinstance(subtitle, str)
        assert len(subtitle) > 0

class TestTemplateThumbnailGenerator:
    """TemplateThumbnailGeneratorのテスト"""

    @pytest.fixture
    def generator(self):
        """テスト用のジェネレーターインスタンス"""
        return TemplateThumbnailGenerator()

    @pytest.fixture
    def mock_video_info(self):
        """モック動画情報"""
        return VideoInfo(
            file_path=Path("test_video.mp4"),
            duration=120.0,
            resolution=(1920, 1080),
            fps=30,
            file_size=10000000,
            has_subtitles=True,
            has_effects=True,
            created_at=datetime.now()
        )

    @pytest.fixture
    def mock_script(self):
        """モックスクリプトデータ"""
        return {
            "title": "テンプレートテスト",
            "content": "テンプレートベースのサムネイル生成テスト",
            "segments": [
                {"text": "テストコンテンツ", "duration": 20, "segment_id": "seg_1"}
            ]
        }

    @pytest.fixture
    def mock_slides(self):
        """モックスライドパッケージ"""
        return SlidesPackage(
            presentation_id="test_presentation",
            slides=[Mock(title="テストスライド", content="テスト内容")],
            total_slides=1
        )

    @pytest.mark.asyncio
    async def test_generate_template(self, generator, mock_video_info, mock_script, mock_slides):
        """テンプレートベースのサムネイル生成テスト"""
        result = await generator.generate(
            video=mock_video_info,
            script=mock_script,
            slides=mock_slides,
            style="modern"
        )

        assert hasattr(result, 'file_path')
        assert result.style == "modern"
        assert result.file_path.exists()

    @pytest.mark.asyncio
    async def test_all_template_styles(self, generator, mock_video_info, mock_script, mock_slides):
        """全テンプレートスタイルのテスト"""
        styles = ["modern", "classic", "gaming", "educational"]

        for style in styles:
            result = await generator.generate(
                video=mock_video_info,
                script=mock_script,
                slides=mock_slides,
                style=style
            )

            assert result.style == style
            assert result.file_path.exists()

    def test_template_initialization(self, generator):
        """テンプレートジェネレーターの初期化テスト"""
        assert generator is not None
        assert hasattr(generator, 'templates')
        assert 'modern' in generator.templates
        assert 'classic' in generator.templates
        assert 'gaming' in generator.templates
        assert 'educational' in generator.templates

class TestTemplateThumbnailGeneratorExtended:
    """TemplateThumbnailGenerator の未カバーパスのテスト"""

    @pytest.fixture
    def mock_video_info(self):
        return VideoInfo(
            file_path=Path("test_video.mp4"),
            duration=120.0,
            resolution=(1920, 1080),
            fps=30,
            file_size=10000000,
            has_subtitles=True,
            has_effects=True,
            created_at=datetime.now()
        )

    @pytest.fixture
    def mock_script(self):
        return {
            "title": "テンプレートテスト",
            "content": "テンプレートベースのサムネイル生成テスト",
            "segments": [
                {"text": "テストコンテンツ", "duration": 20, "segment_id": "seg_1"}
            ]
        }

    @pytest.fixture
    def mock_slides(self):
        return SlidesPackage(
            presentation_id="test_presentation",
            slides=[Mock(title="テストスライド", content="テスト内容")],
            total_slides=1
        )

    def test_load_json_templates_valid(self, tmp_path):
        """有効なJSONテンプレートの読み込み"""
        tmpl_dir = tmp_path / "thumbnails"
        tmpl_dir.mkdir()
        (tmpl_dir / "custom_style.json").write_text(
            json.dumps({"width": 1920, "height": 1080, "background_color": "#ff0000", "text_elements": []}),
            encoding="utf-8"
        )
        gen = TemplateThumbnailGenerator(template_dir=tmpl_dir)
        assert "custom_style" in gen.json_templates
        assert gen.json_templates["custom_style"]["width"] == 1920

    def test_load_json_templates_corrupt(self, tmp_path):
        """破損JSONテンプレートはスキップされる"""
        tmpl_dir = tmp_path / "thumbnails"
        tmpl_dir.mkdir()
        (tmpl_dir / "broken.json").write_text("{invalid json", encoding="utf-8")
        gen = TemplateThumbnailGenerator(template_dir=tmpl_dir)
        assert "broken" not in gen.json_templates

    def test_load_json_templates_empty_dir(self, tmp_path):
        """空ディレクトリではテンプレートなし"""
        tmpl_dir = tmp_path / "thumbnails"
        tmpl_dir.mkdir()
        gen = TemplateThumbnailGenerator(template_dir=tmpl_dir)
        assert gen.json_templates == {}

    def test_load_json_templates_multiple(self, tmp_path):
        """複数JSONテンプレートの読み込み"""
        tmpl_dir = tmp_path / "thumbnails"
        tmpl_dir.mkdir()
        for name in ["style_a", "style_b", "style_c"]:
            (tmpl_dir / f"{name}.json").write_text(
                json.dumps({"width": 1280, "text_elements": []}),
                encoding="utf-8"
            )
        gen = TemplateThumbnailGenerator(template_dir=tmpl_dir)
        assert len(gen.json_templates) == 3

    @pytest.mark.asyncio
    async def test_generate_unknown_style_fallback(self, mock_video_info, mock_script, mock_slides):
        """不明なスタイルはmodernにフォールバック"""
        gen = TemplateThumbnailGenerator()
        result = await gen.generate(
            video=mock_video_info,
            script=mock_script,
            slides=mock_slides,
            style="nonexistent_style"
        )
        # modern テンプレートで生成される
        assert result.file_path.exists()
        assert result.resolution == (1280, 720)

    @pytest.mark.asyncio
    async def test_generate_json_template_with_text_placeholders(self, tmp_path, mock_video_info, mock_script, mock_slides):
        """JSONテンプレートのtext_elements内プレースホルダーが正しく解決される"""
        tmpl_dir = tmp_path / "thumbnails"
        tmpl_dir.mkdir()
        (tmpl_dir / "json_style.json").write_text(
            json.dumps({
                "width": 1280, "height": 720,
                "background_color": "#000000",
                "text_elements": [{"text": "{title}", "position": [50, 50], "font_size": 36, "color": "#ffffff"}],
                "image_elements": []
            }),
            encoding="utf-8"
        )
        gen = TemplateThumbnailGenerator(template_dir=tmpl_dir)
        result = await gen.generate(
            video=mock_video_info,
            script=mock_script,
            slides=mock_slides,
            style="json_style"
        )
        assert result.file_path.exists()
        assert result.style == "json_style"

    @pytest.mark.asyncio
    async def test_generate_json_template_no_text_elements(self, tmp_path, mock_video_info, mock_script, mock_slides):
        """text_elementsが空のJSONテンプレートは正常に生成される"""
        tmpl_dir = tmp_path / "thumbnails"
        tmpl_dir.mkdir()
        (tmpl_dir / "minimal.json").write_text(
            json.dumps({
                "width": 800, "height": 600,
                "background_color": "#336699",
                "text_elements": [],
                "image_elements": []
            }),
            encoding="utf-8"
        )
        gen = TemplateThumbnailGenerator(template_dir=tmpl_dir)
        result = await gen.generate(
            video=mock_video_info,
            script=mock_script,
            slides=mock_slides,
            style="minimal"
        )
        assert result.file_path.exists()
        assert result.resolution == (800, 600)
        assert result.style == "minimal"
        assert result.has_text_effects is True

    def test_apply_gradient_two_colors(self):
        """2色グラデーション"""
        gen = TemplateThumbnailGenerator()
        img = Image.new('RGB', (10, 10), (0, 0, 0))
        result = gen._apply_gradient(img, [(0, 0, 0), (255, 255, 255)])
        assert result.size == (10, 10)
        # 上端は暗い、下端は明るい
        top_pixel = result.getpixel((0, 0))
        bottom_pixel = result.getpixel((0, 9))
        assert top_pixel[0] < bottom_pixel[0]

    def test_apply_gradient_single_color(self):
        """1色（フォールバック）グラデーション"""
        gen = TemplateThumbnailGenerator()
        img = Image.new('RGB', (10, 10), (0, 0, 0))
        result = gen._apply_gradient(img, [(128, 64, 32)])
        # 全ピクセルが同じ色
        assert result.getpixel((0, 0)) == (128, 64, 32)
        assert result.getpixel((5, 5)) == (128, 64, 32)

    def test_draw_centered_text(self):
        """中央揃えテキスト描画が例外なく動作"""
        gen = TemplateThumbnailGenerator()
        img = Image.new('RGB', (1280, 720), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        # 例外なく完了すること
        gen._draw_centered_text(draw, "テスト", font, (255, 255, 255), 100)

    def test_draw_glowing_text(self):
        """光るテキスト描画が例外なく動作"""
        gen = TemplateThumbnailGenerator()
        img = Image.new('RGB', (1280, 720), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        gen._draw_glowing_text(draw, "Glow", font, 100)

    def test_decoration_methods(self):
        """各装飾メソッドが例外なく動作"""
        gen = TemplateThumbnailGenerator()
        img = Image.new('RGB', (1280, 720), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        gen._add_modern_decorations(draw, 1280, 720)
        gen._add_classic_decorations(draw, 1280, 720)
        gen._add_gaming_decorations(draw, 1280, 720)
        gen._add_educational_decorations(draw, 1280, 720)

    @pytest.mark.asyncio
    async def test_save_thumbnail(self):
        """サムネイル保存"""
        gen = TemplateThumbnailGenerator()
        img = Image.new('RGB', (100, 100), (255, 0, 0))
        path = await gen._save_thumbnail(img, "test_style")
        assert path.exists()
        assert path.suffix == ".png"
        assert path.stat().st_size > 0
        path.unlink()  # cleanup


class TestThumbnailIntegration:
    """サムネイル生成の統合テスト"""

    @pytest.mark.asyncio
    async def test_pipeline_thumbnail_generation(self):
        """パイプラインでのサムネイル生成統合テスト"""
        from src.core.pipeline import build_default_pipeline

        # パイプライン構築
        pipeline = build_default_pipeline()

        # サムネイルジェネレーターが設定されていることを確認
        assert pipeline.thumbnail_generator is not None

        # モックデータでテスト
        mock_video = VideoInfo(
            file_path=Path("test_video.mp4"),
            duration=60.0,
            resolution=(1920, 1080),
            fps=30,
            file_size=5000000,
            has_subtitles=True,
            has_effects=False,
            created_at=datetime.now()
        )

        mock_script = {"title": "統合テスト", "content": "パイプライン統合テスト"}
        mock_slides = SlidesPackage(
            presentation_id="test",
            slides=[Mock(title="テスト", content="内容")],
            total_slides=1
        )

        # サムネイル生成テスト
        thumbnail_info = await pipeline.thumbnail_generator.generate(
            video=mock_video,
            script=mock_script,
            slides=mock_slides,
            style="modern"
        )

        assert hasattr(thumbnail_info, 'file_path')
        assert thumbnail_info.file_path.exists()

    def test_thumbnail_file_output(self):
        """サムネイルファイルの出力テスト"""
        # 一時ディレクトリでのテスト
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # AIジェネレーターでテスト
            generator = AIThumbnailGenerator()
            generator.output_dir = temp_path

            # モックデータ
            mock_video = VideoInfo(
                file_path=Path("test.mp4"),
                duration=60.0,
                resolution=(1920, 1080),
                fps=30,
                file_size=1000000,
                has_subtitles=False,
                has_effects=False,
                created_at=datetime.now()
            )

            mock_script = {"title": "ファイルテスト", "content": "ファイル出力テスト"}
            mock_slides = SlidesPackage(
                presentation_id="test",
                slides=[Mock(title="テスト", content="内容")],
                total_slides=1
            )

            async def test_generation():
                result = await generator.generate(
                    video=mock_video,
                    script=mock_script,
                    slides=mock_slides,
                    style="modern"
                )

                # ファイルが作成されたことを確認
                assert result.file_path.exists()
                assert result.file_path.parent == temp_path
                assert result.file_path.suffix == ".png"

                # ファイルサイズが妥当か確認（空ファイルでない）
                assert result.file_path.stat().st_size > 1000

            asyncio.run(test_generation())
