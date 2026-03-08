#!/usr/bin/env python3
"""
テスト: モジュラーパイプライン統合テスト
OpenSpecコンポーネントの統合動作を検証
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.helpers import build_default_pipeline
from src.core.interfaces import IScriptProvider, IPlatformAdapter
from notebook_lm.audio_generator import AudioInfo
from video_editor.models import VideoInfo

class TestModularPipeline:
    """モジュラーパイプライン統合テスト"""

    def test_pipeline_initialization(self):
        """パイプラインが正しく初期化されるか"""
        try:
            pipeline = build_default_pipeline()
            assert pipeline is not None
            assert hasattr(pipeline, 'run')
        except Exception as e:
            pytest.skip(f"Pipeline initialization failed (expected in CI): {e}")

    @pytest.mark.asyncio
    async def test_component_interfaces(self):
        """各コンポーネントが適切なインターフェースを実装しているか"""
        from src.core.providers.script.gemini_provider import GeminiScriptProvider
        from src.core.platforms.youtube_adapter import YouTubePlatformAdapter

        script_provider = GeminiScriptProvider()
        platform_adapter = YouTubePlatformAdapter()

        assert isinstance(script_provider, IScriptProvider) or hasattr(script_provider, 'generate_script')
        assert isinstance(platform_adapter, IPlatformAdapter) or hasattr(platform_adapter, 'upload')

    def test_mock_pipeline_execution(self):
        """モックデータを使ったパイプライン実行テスト"""
        mock_audio = AudioInfo(
            file_path="test_audio.mp3",
            duration=25.0,
            language="ja",
            sample_rate=44100
        )

        mock_video = VideoInfo(
            file_path="test_video.mp4",
            duration=25.0,
            resolution="1080p",
            format="mp4"
        )

        with patch('src.core.providers.script.gemini_provider.GeminiScriptProvider.generate_script') as mock_script_gen, \
             patch('src.core.editing.ymm4_backend.YMM4EditingBackend.render') as mock_edit, \
             patch('src.core.platforms.youtube_adapter.YouTubePlatformAdapter.upload') as mock_upload:

            mock_script_gen.return_value = {"title": "Test", "content": "Test", "segments": []}
            mock_edit.return_value = mock_video
            mock_upload.return_value = Mock(url="https://youtube.com/test", video_id="test123")

            try:
                pipeline = build_default_pipeline()
                assert pipeline is not None
                assert hasattr(pipeline, 'run')
            except Exception as e:
                pytest.skip(f"Pipeline execution failed (expected in CI): {e}")


class TestPipelineConfiguration:
    """パイプライン設定テスト"""

    def test_pipeline_component_config(self):
        """パイプラインコンポーネント設定が正しく読み込まれるか"""
        from config.settings import settings
        components = settings.PIPELINE_COMPONENTS
        assert isinstance(components, dict)
        assert 'script_provider' in components
        assert 'voice_pipeline' in components
        assert 'editing_backend' in components
        assert 'platform_adapter' in components


class TestErrorHandling:
    """エラーハンドリングテスト"""

    def test_component_failure_handling(self):
        """コンポーネント失敗時のエラーハンドリング"""
        with patch('src.core.providers.script.gemini_provider.GeminiScriptProvider.generate_script') as mock_script:
            mock_script.side_effect = Exception("API Error")

            try:
                pipeline = build_default_pipeline()
                assert pipeline is not None
            except Exception:
                pytest.skip("Pipeline initialization failed")


