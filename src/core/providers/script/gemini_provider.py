"""
LLMベースのScriptProvider実装 (SP-043 Phase 2-3 移行済み)

ILLMProvider 抽象を通じて任意の LLM プロバイダーで台本生成。
後方互換: GeminiScriptProvider クラス名を維持。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from config.settings import settings
from notebook_lm.gemini_integration import GeminiIntegration
from notebook_lm.research_models import SourceInfo

from ...interfaces import IScriptProvider

if TYPE_CHECKING:
    from core.llm_provider import ILLMProvider


class GeminiScriptProvider(IScriptProvider):
    """LLMを利用した台本生成プロバイダ (旧名維持)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        target_duration: float = 300.0,
        language: Optional[str] = None,
        style: str = "default",
        speaker_mapping: Optional[Dict[str, str]] = None,
        llm_provider: Optional["ILLMProvider"] = None,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.target_duration = target_duration
        self.language = language or settings.YOUTUBE_SETTINGS.get("default_language", "ja")
        self.style = style
        self.speaker_mapping = speaker_mapping
        self._llm_provider = llm_provider

        # APIキーがない環境でもインターフェースチェック用にインスタンス化だけは許可し、
        # 実際の generate_script 呼び出し時にエラーとする（テスト互換のための設計）。
        self.client: Optional[GeminiIntegration] = None
        if self.api_key or self._llm_provider:
            self.client = GeminiIntegration(
                api_key=self.api_key,
                llm_provider=self._llm_provider,
            )

    async def generate_script(
        self,
        topic: str,
        sources: List[SourceInfo],
        mode: str = "auto",
    ) -> Dict[str, Any]:
        if not self.api_key and self._llm_provider is None:
            raise ValueError("LLM APIキーが設定されていません。環境変数 GEMINI_API_KEY / LLM_API_KEY を確認してください。")

        # 遅延初期化（テストや軽量チェック時に無駄な初期化を避ける）
        if self.client is None:
            self.client = GeminiIntegration(
                api_key=self.api_key,
                llm_provider=self._llm_provider,
            )

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
            style=self.style,
            speaker_mapping=self.speaker_mapping,
        )

        try:
            cleaned_content = GeminiIntegration._extract_json_from_response(script_info.content)
            script_bundle = json.loads(cleaned_content)
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

        return script_bundle  # type: ignore[no-any-return]
