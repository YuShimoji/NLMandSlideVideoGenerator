#!/usr/bin/env python3
"""
テスト: サムネイル生成コンポーネントテスト
OpenSpec IThumbnailGeneratorの実装を検証
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys
import tempfile
import shutil

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.thumbnails import AIThumbnailGenerator, TemplateThumbnailGenerator
from src.video_editor.video_composer import VideoInfo, ThumbnailInfo
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
            created_at=Mock()
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

        assert isinstance(result, ThumbnailInfo)
        assert result.title_text == mock_script["title"]
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

        assert isinstance(result, ThumbnailInfo)
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
            created_at=Mock()
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

        assert isinstance(result, ThumbnailInfo)
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
            created_at=Mock()
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

        assert isinstance(thumbnail_info, ThumbnailInfo)
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
                created_at=Mock()
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
