"""
GeminiベースのScriptProvider実装
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from config.settings import settings
from notebook_lm.gemini_integration import GeminiIntegration
from notebook_lm.source_collector import SourceInfo

from ...interfaces import IScriptProvider


class GeminiScriptProvider(IScriptProvider):
    """NotebookLM/Geminiを利用した台本生成プロバイダ"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        target_duration: float = 300.0,
        language: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.target_duration = target_duration
        self.language = language or settings.YOUTUBE_SETTINGS.get("default_language", "ja")

        if not self.api_key:
            raise ValueError("Gemini APIキーが設定されていません。環境変数 GEMINI_API_KEY を確認してください。")

        self.client = GeminiIntegration(api_key=self.api_key)

    async def generate_script(
        self,
        topic: str,
        sources: List[SourceInfo],
        mode: str = "auto",
    ) -> Dict[str, Any]:
        sources_payload: List[Dict[str, Any]] = [
            {
                "url": getattr(src, "url", ""),
                "title": getattr(src, "title", ""),
                "content_preview": getattr(src, "content_preview", ""),
                "relevance_score": getattr(src, "relevance_score", 0.0),
                "reliability_score": getattr(src, "reliability_score", 0.0),
            }
            for src in sources
        ]

        script_info = await self.client.generate_script_from_sources(
            sources=sources_payload,
            topic=topic,
            target_duration=self.target_duration,
            language=self.language,
        )

        try:
            script_bundle = json.loads(script_info.content)
        except json.JSONDecodeError:
            script_bundle = {
                "title": script_info.title,
                "segments": [],
                "content": script_info.content,
                "total_duration_estimate": script_info.total_duration_estimate,
                "language": script_info.language,
                "quality_score": script_info.quality_score,
                "created_at": script_info.created_at.isoformat(),
            }

        if "title" not in script_bundle:
            script_bundle["title"] = script_info.title

        return script_bundle
