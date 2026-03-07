#!/usr/bin/env python3
"""
テスト: Voice Pipeline コンポーネントテスト
TTSVoicePipelineのNo-opスタブ検証 + IVoicePipelineインターフェース準拠
"""

import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class TestTTSVoicePipeline:
    """TTSVoicePipeline No-opスタブのテスト"""

    def test_pipeline_initialization(self):
        """パイプラインの初期化テスト"""
        from src.core.voice_pipelines.tts_voice_pipeline import TTSVoicePipeline

        pipeline = TTSVoicePipeline()
        assert pipeline is not None
        assert hasattr(pipeline, "synthesize")

    def test_implements_interface(self):
        """IVoicePipelineインターフェースを満たすことを確認"""
        from src.core.voice_pipelines.tts_voice_pipeline import TTSVoicePipeline
        from src.core.interfaces import IVoicePipeline

        pipeline = TTSVoicePipeline()
        assert isinstance(pipeline, IVoicePipeline)

    @pytest.mark.asyncio
    async def test_synthesize_raises_not_implemented(self):
        """synthesize呼び出しでNotImplementedErrorが発生することを確認"""
        from src.core.voice_pipelines.tts_voice_pipeline import TTSVoicePipeline

        pipeline = TTSVoicePipeline()
        script = {"title": "テスト", "content": "テストコンテンツ"}

        with pytest.raises(NotImplementedError, match="YMM4"):
            await pipeline.synthesize(script)

    def test_tts_integration_stub_types(self):
        """TTSIntegration/TTSProvider/VoiceConfigの型がインポート可能"""
        from audio.tts_integration import TTSIntegration, TTSProvider, VoiceConfig

        tts = TTSIntegration()
        assert tts.get_status()["active_providers"] == []

        config = VoiceConfig()
        assert config.language == "ja"

        assert TTSProvider.ELEVENLABS.value == "elevenlabs"
