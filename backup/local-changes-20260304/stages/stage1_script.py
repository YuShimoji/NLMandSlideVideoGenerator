from __future__ import annotations
from typing import List, Optional, Dict, Any, Callable
from ..utils.logger import logger
from ..interfaces import ISourceCollector, IScriptProvider, IVoicePipeline
from notebook_lm.audio_generator import AudioInfo
from ..exceptions import PipelineError
from config.settings import settings

class Stage1ScriptProcessor:
    def __init__(
        self,
        source_collector: ISourceCollector,
        script_provider: Optional[IScriptProvider] = None,
        voice_pipeline: Optional[IVoicePipeline] = None,
    ):
        self.source_collector = source_collector
        self.script_provider = script_provider
        self.voice_pipeline = voice_pipeline

    async def collect_sources(self, topic: str, urls: Optional[List[str]] = None) -> List[Any]:
        """ソース収集フェーズ"""
        try:
            sources = await self.source_collector.collect_sources(topic, urls)
            return sources
        except Exception as e:
            logger.error(f"ソース収集失敗: {e}")
            raise PipelineError(str(e), stage="sources", recoverable=True)

    async def process(
        self,
        topic: str,
        sources: List[Any],
        mode: str = "auto",
        progress_callback: Optional[Callable[[str, float, str], None]] = None
    ) -> tuple[Optional[Dict[str, Any]], AudioInfo]:
        """Script + Voice 生成フェーズ"""
        if self.script_provider and self.voice_pipeline:
            if progress_callback:
                progress_callback("スクリプト生成", 0.2, "AIによるスクリプト生成を開始します...")
            
            raw_script = await self.script_provider.generate_script(topic, sources)
            # 実際には _normalize_script_with_fallback が pipeline.py にあるが、インターフェースに寄せる
            script_bundle = raw_script # TODO: normalization logic

            if progress_callback:
                progress_callback("音声合成", 0.3, "テキスト-to-スピーチで音声を生成します...")
            
            audio_info = await self.voice_pipeline.execute(script_bundle)
            return script_bundle, audio_info
        else:
            # Legacy fallback is handled in the main pipeline for now to keep it simple,
            # or we can move it here if we bring the legacy components.
            raise PipelineError("Stage1 requires script_provider and voice_pipeline")
