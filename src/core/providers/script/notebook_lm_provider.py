"""
NotebookLM ベースの Script Provider
OpenSpec IScriptProvider 実装
"""
from typing import Dict, Any, List
from pathlib import Path
import json
from datetime import datetime

from notebook_lm.source_collector import SourceCollector, SourceInfo
from notebook_lm.audio_generator import AudioGenerator, AudioInfo
from notebook_lm.transcript_processor import TranscriptProcessor, TranscriptInfo

from ...interfaces import IScriptProvider


class NotebookLMScriptProvider(IScriptProvider):
    """NotebookLM を利用したスクリプト生成プロバイダ"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.source_collector = SourceCollector()
        self.audio_generator = AudioGenerator()
        self.transcript_processor = TranscriptProcessor()

    async def generate_script(
        self,
        topic: str,
        sources: List[SourceInfo],
        mode: str = "auto",
    ) -> Dict[str, Any]:
        """
        NotebookLM を利用してスクリプトを生成

        Args:
            topic: トピック
            sources: ソース情報リスト
            mode: 生成モード (auto/assist/manual)

        Returns:
            Dict[str, Any]: スクリプトバンドル
        """
        # NotebookLM の音声生成と文字起こしを活用
        # 実際の NotebookLM API を模擬

        # 1. ソース収集 (もし sources が空の場合)
        if not sources:
            sources = await self.source_collector.collect_sources(topic)

        # 2. 音声生成 (NotebookLM 風)
        audio_info = await self.audio_generator.generate_audio(sources)

        # 3. 文字起こしでスクリプト生成
        transcript = await self.transcript_processor.process_audio(audio_info)

        # 4. スクリプト構造の構築
        script_bundle = {
            "title": transcript.title,
            "topic": topic,
            "source_count": len(sources),
            "audio_duration": audio_info.duration,
            "generated_at": datetime.now().isoformat(),
            "segments": []
        }

        # 文字起こし結果からセグメント構築
        for i, segment in enumerate(transcript.segments):
            script_bundle["segments"].append({
                "id": f"seg_{i+1}",
                "start_time": segment.get("start", 0),
                "end_time": segment.get("end", 0),
                "content": segment.get("text", ""),
                "confidence": segment.get("confidence", 1.0)
            })

        # スクリプト保存
        self._save_script(script_bundle)

        return script_bundle

    def _save_script(self, script_bundle: Dict[str, Any]) -> Path:
        """スクリプトをファイルに保存"""
        from config.settings import settings
        settings.SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_path = settings.SCRIPTS_DIR / f"notebooklm_script_{timestamp}.json"

        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script_bundle, f, ensure_ascii=False, indent=2)

        return script_path
