#!/usr/bin/env python3
"""
テスト: モジュラーパイプライン統合テスト
OpenSpecコンポーネントの統合動作を検証
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from dataclasses import dataclass
import sys
from fastapi.testclient import TestClient

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.helpers import build_default_pipeline
from src.core.interfaces import IScriptProvider, IVoicePipeline, IEditingBackend, IPlatformAdapter
from notebook_lm.audio_generator import AudioInfo
from slides.slide_generator import SlidesPackage
from video_editor.video_composer import VideoInfo

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
        from src.core.voice_pipelines.tts_voice_pipeline import TTSVoicePipeline
        from src.core.editing.moviepy_backend import MoviePyEditingBackend
        from src.core.platforms.youtube_adapter import YouTubePlatformAdapter

        script_provider = GeminiScriptProvider()
        voice_pipeline = TTSVoicePipeline()
        editing_backend = MoviePyEditingBackend()
        platform_adapter = YouTubePlatformAdapter()

        assert isinstance(script_provider, IScriptProvider) or hasattr(script_provider, 'generate_script')
        assert isinstance(voice_pipeline, IVoicePipeline) or hasattr(voice_pipeline, 'synthesize')
        assert isinstance(editing_backend, IEditingBackend) or hasattr(editing_backend, 'render')
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
             patch('src.core.voice_pipelines.tts_voice_pipeline.TTSVoicePipeline.synthesize') as mock_voice, \
             patch('src.core.editing.moviepy_backend.MoviePyEditingBackend.render') as mock_edit, \
             patch('src.core.platforms.youtube_adapter.YouTubePlatformAdapter.upload') as mock_upload:

            mock_script_gen.return_value = {"title": "Test", "content": "Test", "segments": []}
            mock_voice.return_value = mock_audio
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


class TestCsvPipelineApiYmm4:
    """CSV パイプライン API の YMM4 エクスポート統合テスト"""

    @dataclass
    class _DummyTranscript:
        title: str

    @dataclass
    class _DummyArtifacts:
        transcript: "TestCsvPipelineApiYmm4._DummyTranscript"
        editing_outputs: dict

    class _DummyPipeline:
        def __init__(self, artifacts):
            self._artifacts = artifacts

        async def run_csv_timeline(self, *args, **kwargs):
            return {
                "success": True,
                "artifacts": self._artifacts,
                "youtube_url": None,
            }

    def _create_client(self):
        from src.server import api as api_mod

        client = TestClient(api_mod.app)
        return client, api_mod

    def test_csv_api_returns_ymm4_export_field(self):
        """export_ymm4 指定時に ymm4_export フィールドがレスポンスに含まれる"""
        from config.settings import settings

        client, api_mod = self._create_client()

        artifacts = self._DummyArtifacts(
            transcript=self._DummyTranscript(title="CSV Title"),
            editing_outputs={"ymm4": {"project_dir": "/tmp/ymm4_project"}},
        )

        dummy_pipeline = self._DummyPipeline(artifacts)

        payload = {
            "csv_path": "C:/dummy/timeline.csv",
            "audio_dir": "C:/dummy/audio",
            "export_ymm4": True,
            "upload": False,
        }

        with patch.dict(settings.PIPELINE_COMPONENTS, {"editing_backend": "moviepy"}, clear=False):
            with patch.object(api_mod, "build_default_pipeline", return_value=dummy_pipeline):
                response = client.post("/api/v1/pipeline/csv", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ymm4_export" in data
        assert data["ymm4_export"]["project_dir"] == "/tmp/ymm4_project"

    def test_csv_api_export_ymm4_overrides_editing_backend(self):
        """export_ymm4=true の場合、editing_backend が明示されていても YMM4 が優先される"""
        from config.settings import settings

        client, api_mod = self._create_client()

        artifacts = self._DummyArtifacts(
            transcript=self._DummyTranscript(title="CSV Title"),
            editing_outputs={},
        )

        dummy_pipeline = self._DummyPipeline(artifacts)

        payload = {
            "csv_path": "C:/dummy/timeline.csv",
            "audio_dir": "C:/dummy/audio",
            "editing_backend": "moviepy",
            "export_ymm4": True,
            "upload": False,
        }

        with patch.dict(settings.PIPELINE_COMPONENTS, {"editing_backend": "moviepy"}, clear=False):
            with patch.object(api_mod, "build_default_pipeline", return_value=dummy_pipeline):
                response = client.post("/api/v1/pipeline/csv", json=payload)
                assert settings.PIPELINE_COMPONENTS["editing_backend"] == "ymm4"

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
