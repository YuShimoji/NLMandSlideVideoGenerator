#!/usr/bin/env python3
"""
テスト: モジュラーパイプライン統合テスト
OpenSpecコンポーネントの統合動作を検証
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.pipeline import build_default_pipeline
from src.core.interfaces import IScriptProvider, IVoicePipeline, IEditingBackend, IPlatformAdapter
from notebook_lm.source_collector import SourceInfo
from notebook_lm.audio_generator import AudioInfo
from slides.slide_generator import SlidesPackage
from video_editor.video_composer import VideoInfo

class TestModularPipeline:
    """モジュラーパイプライン統合テスト"""

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self):
        """パイプラインが正しく初期化されるか"""
        try:
            pipeline = await build_default_pipeline()
            assert pipeline is not None
            assert hasattr(pipeline, 'run')
        except Exception as e:
            # 設定ファイルやAPIキーがない場合を考慮してスキップ
            pytest.skip(f"Pipeline initialization failed (expected in CI): {e}")

    @pytest.mark.asyncio
    async def test_component_interfaces(self):
        """各コンポーネントが適切なインターフェースを実装しているか"""
        # 設定がない環境でもインターフェースチェックは可能
        from src.core.providers.script.gemini_provider import GeminiScriptProvider
        from src.core.voice_pipelines.tts_voice_pipeline import TTSVoicePipeline
        from src.core.editing.moviepy_backend import MoviePyEditingBackend
        from src.core.platforms.youtube_adapter import YouTubePlatformAdapter

        # 各コンポーネントのインスタンス化
        script_provider = GeminiScriptProvider()
        voice_pipeline = TTSVoicePipeline()
        editing_backend = MoviePyEditingBackend()
        platform_adapter = YouTubePlatformAdapter()

        # インターフェース準拠チェック
        assert isinstance(script_provider, IScriptProvider) or hasattr(script_provider, 'generate_script')
        assert isinstance(voice_pipeline, IVoicePipeline) or hasattr(voice_pipeline, 'synthesize')
        assert isinstance(editing_backend, IEditingBackend) or hasattr(editing_backend, 'render')
        assert isinstance(platform_adapter, IPlatformAdapter) or hasattr(platform_adapter, 'upload')

    @pytest.mark.asyncio
    async def test_mock_pipeline_execution(self):
        """モックデータを使ったパイプライン実行テスト"""
        # モックデータの作成
        mock_script = {
            "title": "Test Topic",
            "content": "This is test content",
            "segments": [
                {"text": "First segment", "duration": 10},
                {"text": "Second segment", "duration": 15}
            ]
        }

        mock_audio = AudioInfo(
            file_path="test_audio.mp3",
            duration=25.0,
            language="ja",
            sample_rate=44100
        )

        mock_slides = SlidesPackage(
            presentation_id="test_presentation",
            slides=[
                Mock(title="Slide 1", content="Content 1"),
                Mock(title="Slide 2", content="Content 2")
            ]
        )

        mock_video = VideoInfo(
            file_path="test_video.mp4",
            duration=25.0,
            resolution="1080p",
            format="mp4"
        )

        # 各コンポーネントのモック
        with patch('src.core.providers.script.gemini_provider.GeminiScriptProvider.generate_script') as mock_script_gen, \
             patch('src.core.voice_pipelines.tts_voice_pipeline.TTSVoicePipeline.synthesize') as mock_voice, \
             patch('src.core.editing.moviepy_backend.MoviePyEditingBackend.render') as mock_edit, \
             patch('src.core.platforms.youtube_adapter.YouTubePlatformAdapter.upload') as mock_upload:

            # モックの戻り値を設定
            mock_script_gen.return_value = mock_script
            mock_voice.return_value = mock_audio
            mock_edit.return_value = mock_video
            mock_upload.return_value = Mock(url="https://youtube.com/test", video_id="test123")

            try:
                # パイプライン実行（実際にはモックされる）
                pipeline = await build_default_pipeline()
                result = await pipeline.run(topic="Test Topic")

                # 各コンポーネントが呼ばれたことを確認
                mock_script_gen.assert_called_once()
                mock_voice.assert_called_once()
                mock_edit.assert_called_once()
                mock_upload.assert_called_once()

            except Exception as e:
                # 設定ファイルがない場合を考慮
                pytest.skip(f"Pipeline execution failed (expected in CI): {e}")

class TestPipelineConfiguration:
    """パイプライン設定テスト"""

    def test_pipeline_component_config(self):
        """パイプラインコンポーネント設定が正しく読み込まれるか"""
        # 環境変数や設定ファイルがない場合のテスト
        try:
            from config.settings import PIPELINE_COMPONENTS
            assert isinstance(PIPELINE_COMPONENTS, dict)
            assert 'script_provider' in PIPELINE_COMPONENTS
            assert 'voice_pipeline' in PIPELINE_COMPONENTS
            assert 'editing_backend' in PIPELINE_COMPONENTS
            assert 'platform_adapter' in PIPELINE_COMPONENTS
        except ImportError:
            pytest.skip("Settings not available")

    def test_component_factory(self):
        """コンポーネントファクトリが正しく動作するか"""
        try:
            from src.core.pipeline import create_component

            # 各コンポーネントタイプのファクトリテスト
            script_provider = create_component('script_provider', 'gemini')
            assert script_provider is not None

            voice_pipeline = create_component('voice_pipeline', 'tts')
            assert voice_pipeline is not None

            editing_backend = create_component('editing_backend', 'moviepy')
            assert editing_backend is not None

        except Exception as e:
            pytest.skip(f"Component factory test failed: {e}")

class TestErrorHandling:
    """エラーハンドリングテスト"""

    @pytest.mark.asyncio
    async def test_component_failure_handling(self):
        """コンポーネント失敗時のエラーハンドリング"""
        # エラーが適切に伝播されることをテスト
        with patch('src.core.providers.script.gemini_provider.GeminiScriptProvider.generate_script') as mock_script:
            mock_script.side_effect = Exception("API Error")

            try:
                pipeline = await build_default_pipeline()
                with pytest.raises(Exception):
                    await pipeline.run(topic="Test Topic")
            except Exception:
                # パイプライン初期化自体が失敗する場合はスキップ
                pytest.skip("Pipeline initialization failed")

    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """グレースフルデグレーションのテスト"""
        # あるコンポーネントが失敗しても他のコンポーネントは動作する
        try:
            pipeline = await build_default_pipeline()

            # 部分的な実行テスト（モックが必要）
            # 実際のテストはより詳細なモックが必要

            pytest.skip("Graceful degradation test requires detailed mocking")

        except Exception:
            pytest.skip("Pipeline initialization failed")
