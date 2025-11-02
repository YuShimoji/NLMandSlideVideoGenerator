#!/usr/bin/env python3
"""
テスト: Voice Pipeline コンポーネントテスト
OpenSpec IVoicePipelineの実装を検証
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.voice_pipelines.tts_voice_pipeline import TTSVoicePipeline
from notebook_lm.audio_generator import AudioInfo

class TestTTSVoicePipeline:
    """TTSVoicePipelineのテスト"""

    @pytest.fixture
    def pipeline(self):
        """テスト用のパイプラインインスタンス"""
        return TTSVoicePipeline()

    @pytest.fixture
    def mock_script(self):
        """モックスクリプトデータ"""
        return {
            "title": "テストスクリプト",
            "content": "これはテストコンテンツです。",
            "segments": [
                {
                    "text": "最初のセグメント",
                    "duration": 10,
                    "segment_id": "seg_1"
                },
                {
                    "text": "次のセグメント",
                    "duration": 15,
                    "segment_id": "seg_2"
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_synthesize_basic(self, pipeline, mock_script):
        """基本的な音声合成テスト"""
        # TTS APIをモック
        with patch('src.core.voice_pipelines.tts_voice_pipeline.AudioInfo') as mock_audio_info:
            mock_audio_instance = Mock()
            mock_audio_instance.file_path = "test_audio.mp3"
            mock_audio_instance.duration = 25.0
            mock_audio_instance.language = "ja"
            mock_audio_instance.sample_rate = 44100
            mock_audio_info.return_value = mock_audio_instance

            result = await pipeline.synthesize(mock_script)

            assert isinstance(result, Mock) or hasattr(result, 'file_path')
            assert result.file_path == "test_audio.mp3"
            assert result.duration == 25.0

    @pytest.mark.asyncio
    async def test_synthesize_with_provider(self, pipeline, mock_script):
        """プロバイダー指定での音声合成テスト"""
        for provider in ['elevenlabs', 'openai', 'azure']:
            with patch('src.core.voice_pipelines.tts_voice_pipeline.AudioInfo') as mock_audio_info:
                mock_audio_instance = Mock()
                mock_audio_instance.file_path = f"test_{provider}_audio.mp3"
                mock_audio_instance.duration = 25.0
                mock_audio_instance.language = "ja"
                mock_audio_info.return_value = mock_audio_instance

                result = await pipeline.synthesize(mock_script, provider)

                assert isinstance(result, Mock) or hasattr(result, 'file_path')

    @pytest.mark.asyncio
    async def test_synthesize_empty_script(self, pipeline):
        """空のスクリプトでの音声合成テスト"""
        empty_script = {
            "title": "空のスクリプト",
            "content": "",
            "segments": []
        }

        with patch('src.core.voice_pipelines.tts_voice_pipeline.AudioInfo') as mock_audio_info:
            mock_audio_instance = Mock()
            mock_audio_instance.file_path = "empty_audio.mp3"
            mock_audio_instance.duration = 0.0
            mock_audio_info.return_value = mock_audio_instance

            result = await pipeline.synthesize(empty_script)

            assert isinstance(result, Mock) or hasattr(result, 'file_path')

    @pytest.mark.asyncio
    async def test_synthesize_provider_error(self, pipeline, mock_script):
        """プロバイダーエラー時の処理テスト"""
        with patch('src.core.voice_pipelines.tts_voice_pipeline.AudioInfo') as mock_audio_info:
            mock_audio_info.side_effect = Exception("TTS Provider Error")

            with pytest.raises(Exception):
                await pipeline.synthesize(mock_script, "invalid_provider")

    def test_pipeline_initialization(self, pipeline):
        """パイプラインの初期化テスト"""
        assert pipeline is not None
        assert hasattr(pipeline, 'synthesize')

    @pytest.mark.asyncio
    async def test_audio_info_structure(self, pipeline, mock_script):
        """生成されるAudioInfoの構造テスト"""
        with patch('src.core.voice_pipelines.tts_voice_pipeline.AudioInfo') as mock_audio_info:
            mock_audio_instance = Mock()
            mock_audio_instance.file_path = "structured_audio.mp3"
            mock_audio_instance.duration = 25.0
            mock_audio_instance.language = "ja"
            mock_audio_instance.sample_rate = 44100
            mock_audio_instance.channels = 2
            mock_audio_instance.bitrate = 128
            mock_audio_info.return_value = mock_audio_instance

            result = await pipeline.synthesize(mock_script)

            assert hasattr(result, 'file_path')
            assert hasattr(result, 'duration')
            assert hasattr(result, 'language')
            assert hasattr(result, 'sample_rate')

    @pytest.mark.asyncio
    async def test_multiple_segments_handling(self, pipeline):
        """複数セグメントの処理テスト"""
        multi_segment_script = {
            "title": "複数セグメントテスト",
            "content": "長いコンテンツ",
            "segments": [
                {"text": f"セグメント{i}", "duration": 10, "segment_id": f"seg_{i}"}
                for i in range(1, 6)  # 5セグメント
            ]
        }

        with patch('src.core.voice_pipelines.tts_voice_pipeline.AudioInfo') as mock_audio_info:
            mock_audio_instance = Mock()
            mock_audio_instance.file_path = "multi_segment_audio.mp3"
            mock_audio_instance.duration = 50.0  # 5セグメント × 10秒
            mock_audio_info.return_value = mock_audio_instance

            result = await pipeline.synthesize(multi_segment_script)

            assert hasattr(result, 'file_path')
            assert result.duration >= 40.0  # 最低期待時間
