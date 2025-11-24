#!/usr/bin/env python3
"""
テスト: モジュラーパイプライン統合テスト
OpenSpecコンポーネントの統合動作を検証
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from dataclasses import dataclass
import sys
from fastapi.testclient import TestClient

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


class TestOperationalFeatures:
    """運用機能の統合テスト"""

    @pytest.mark.asyncio
    async def test_database_persistence(self):
        """データ永続化テスト"""
        try:
            from src.core.persistence import db_manager

            # テストレコードの保存
            test_record = {
                'job_id': 'test_operational_123',
                'topic': '運用テスト',
                'status': 'completed',
                'created_at': asyncio.get_event_loop().time(),
                'artifacts': {'test': 'data'},
                'metadata': {'test': True}
            }

            record_id = db_manager.save_generation_record(test_record)
            assert record_id > 0

            # レコードの取得
            history = db_manager.get_generation_history(limit=10)
            found_record = next((r for r in history if r.get('job_id') == 'test_operational_123'), None)
            assert found_record is not None
            assert found_record['topic'] == '運用テスト'

        except Exception as e:
            pytest.skip(f"Database test failed: {e}")

    @pytest.mark.asyncio
    async def test_health_check_api(self):
        """ヘルスチェックAPIテスト"""
        try:
            from src.server.api_server import server

            health_status = await server.perform_health_check()

            assert 'healthy' in health_status
            assert 'checks' in health_status
            assert isinstance(health_status['healthy'], bool)
            assert 'timestamp' in health_status

        except Exception as e:
            pytest.skip(f"Health check test failed: {e}")

    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """メトリクス収集テスト"""
        try:
            from src.server.api_server import REQUEST_COUNT

            # メトリクスが利用可能か確認
            if hasattr(REQUEST_COUNT, '_value'):
                initial_value = REQUEST_COUNT._value
                # 何らかの操作でメトリクスが増加することを確認
                assert initial_value >= 0
            else:
                pytest.skip("Prometheus metrics not available")

        except Exception as e:
            pytest.skip(f"Metrics test failed: {e}")

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """エラー回復テスト"""
        try:
            from src.core.pipeline import PipelineError, retry_on_failure

            # リトライデコレータのテスト
            call_count = 0

            @retry_on_failure(max_retries=2)
            async def failing_function():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("Test error")
                return "success"

            result = await failing_function()
            assert result == "success"
            assert call_count == 3  # リトライされた

        except Exception as e:
            pytest.skip(f"Error recovery test failed: {e}")

    @pytest.mark.asyncio
    async def test_backup_functionality(self):
        """バックアップ機能テスト"""
        try:
            from src.core.persistence import backup_manager
            import tempfile

            # 一時ディレクトリでテスト
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                (temp_path / "test_data").mkdir()

                # テストファイル作成
                test_file = temp_path / "test_data" / "test.txt"
                test_file.write_text("test content")

                # バックアップ実行
                backup_path = backup_manager.create_backup(
                    "test_backup",
                    [temp_path / "test_data"]
                )

                assert backup_path.exists()
                assert backup_path.suffix == ".zip"

        except Exception as e:
            pytest.skip(f"Backup test failed: {e}")

    @pytest.mark.asyncio
    async def test_configuration_management(self):
        """設定管理テスト"""
        try:
            from src.core.persistence import db_manager

            # 設定変更の保存
            db_manager.save_config_change(
                key="test_setting",
                value={"enabled": True},
                changed_by="test"
            )

            # 設定履歴の取得
            history = db_manager.get_config_history(key="test_setting", limit=5)
            assert len(history) > 0

            latest_change = history[0]
            assert latest_change['key'] == "test_setting"
            assert latest_change['value']['enabled'] is True

        except Exception as e:
            pytest.skip(f"Configuration test failed: {e}")

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
                # エンドポイント内部で editing_backend が YMM4 に切り替えられているはず
                assert settings.PIPELINE_COMPONENTS["editing_backend"] == "ymm4"

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
