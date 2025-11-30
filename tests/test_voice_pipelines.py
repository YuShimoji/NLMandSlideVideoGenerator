#!/usr/bin/env python3
"""
テスト: Voice Pipeline コンポーネントテスト
OpenSpec IVoicePipelineの実装を検証
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class TestTTSVoicePipeline:
    """TTSVoicePipelineのテスト"""

    @pytest.fixture
    def mock_tts_integration(self):
        """TTSIntegrationのモック"""
        mock_tts = MagicMock()
        mock_audio_result = Mock()
        mock_audio_result.file_path = Path("test_audio.mp3")
        mock_audio_result.duration = 25.0
        mock_audio_result.language = "ja"
        mock_audio_result.sample_rate = 44100
        mock_tts.generate_audio = AsyncMock(return_value=mock_audio_result)
        return mock_tts

    @pytest.fixture
    def pipeline(self, mock_tts_integration):
        """テスト用のパイプラインインスタンス（TTSをモック）"""
        with patch('src.core.voice_pipelines.tts_voice_pipeline.TTSIntegration', return_value=mock_tts_integration):
            from src.core.voice_pipelines.tts_voice_pipeline import TTSVoicePipeline
            return TTSVoicePipeline()

    @pytest.fixture
    def mock_script(self):
        """モックスクリプトデータ"""
        return {
            "title": "テストスクリプト",
            "content": "これはテストコンテンツです。",
            "segments": [
                {
                    "content": "最初のセグメント",
                    "duration": 10,
                    "segment_id": "seg_1"
                },
                {
                    "content": "次のセグメント",
                    "duration": 15,
                    "segment_id": "seg_2"
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_synthesize_basic(self, pipeline, mock_script):
        """基本的な音声合成テスト"""
        result = await pipeline.synthesize(mock_script)
        
        assert result is not None
        assert hasattr(result, 'file_path')
        assert result.duration == 25.0

    @pytest.mark.asyncio
    async def test_synthesize_with_provider(self, pipeline, mock_script):
        """プロバイダー指定での音声合成テスト"""
        for provider in ['elevenlabs', 'openai', 'azure']:
            result = await pipeline.synthesize(mock_script, provider)
            assert result is not None

    @pytest.mark.asyncio
    async def test_synthesize_empty_script(self, pipeline):
        """空のスクリプトでの音声合成テスト"""
        empty_script = {
            "title": "空のスクリプト",
            "content": "",
            "segments": []
        }
        
        # 空のスクリプトはValueErrorを発生させるはず
        with pytest.raises(ValueError):
            await pipeline.synthesize(empty_script)

    @pytest.mark.asyncio
    async def test_synthesize_provider_error(self, mock_tts_integration, mock_script):
        """プロバイダーエラー時の処理テスト"""
        mock_tts_integration.generate_audio = AsyncMock(side_effect=Exception("TTS Provider Error"))
        
        with patch('src.core.voice_pipelines.tts_voice_pipeline.TTSIntegration', return_value=mock_tts_integration):
            from src.core.voice_pipelines.tts_voice_pipeline import TTSVoicePipeline
            pipeline = TTSVoicePipeline()
            
            with pytest.raises(Exception):
                await pipeline.synthesize(mock_script)

    def test_pipeline_initialization(self, pipeline):
        """パイプラインの初期化テスト"""
        assert pipeline is not None
        assert hasattr(pipeline, 'synthesize')

    @pytest.mark.asyncio
    async def test_audio_info_structure(self, pipeline, mock_script):
        """生成されるAudioInfoの構造テスト"""
        result = await pipeline.synthesize(mock_script)
        
        assert hasattr(result, 'file_path')
        assert hasattr(result, 'duration')

    @pytest.mark.asyncio
    async def test_multiple_segments_handling(self, pipeline):
        """複数セグメントの処理テスト"""
        multi_segment_script = {
            "title": "複数セグメントテスト",
            "content": "長いコンテンツ",
            "segments": [
                {"content": f"セグメント{i}", "duration": 10, "segment_id": f"seg_{i}"}
                for i in range(1, 6)  # 5セグメント
            ]
        }
        
        result = await pipeline.synthesize(multi_segment_script)
        assert hasattr(result, 'file_path')
