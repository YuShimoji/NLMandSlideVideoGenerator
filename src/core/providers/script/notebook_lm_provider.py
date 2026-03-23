"""
NotebookLM ベースの Script Provider — レガシースタブ

DESIGN NOTE (DESIGN_FOUNDATIONS.md):
  実際の台本生成は NotebookLM (Audio Overview → テキスト化) が行う。
  Python側の台本構造化は GeminiScriptProvider.structure_transcript() が担う。
  このプロバイダは後方互換のためのスタブ。
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from datetime import datetime

from notebook_lm.research_models import SourceInfo
from notebook_lm.audio_generator import AudioGenerator, AudioInfo
from notebook_lm.transcript_processor import TranscriptProcessor, TranscriptInfo, TranscriptSegment

from ...interfaces import IScriptProvider


class NotebookLMScriptProvider(IScriptProvider):
    """NotebookLM を利用したスクリプト生成プロバイダ (レガシースタブ)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.audio_generator = AudioGenerator()
        self.transcript_processor = TranscriptProcessor()

    async def generate_script(
        self,
        topic: str,
        sources: List[SourceInfo],
        mode: str = "auto",
        transcript_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """スタブ: プレースホルダー音声 → 空セグメントのバンドルを返す。

        実際の台本生成は GeminiScriptProvider を使用すること。
        """
        audio_info = await self.audio_generator.generate_audio(sources)

        script_bundle = {
            "title": f"{topic} (stub)",
            "topic": topic,
            "source_count": len(sources),
            "audio_duration": audio_info.duration,
            "generated_at": datetime.now().isoformat(),
            "segments": [],
        }

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
