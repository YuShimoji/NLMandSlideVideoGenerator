"""
TTSベースのVoicePipeline実装
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from config.settings import settings
from audio.tts_integration import TTSIntegration, VoiceConfig, TTSProvider

from ..interfaces import IVoicePipeline


class TTSVoicePipeline(IVoicePipeline):
    """複数TTSプロバイダを横断して音声生成を行うパイプライン"""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
    ) -> None:
        self.output_dir = output_dir or settings.AUDIO_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        api_keys = {
            "elevenlabs": settings.TTS_SETTINGS.get("elevenlabs", {}).get("api_key", ""),
            "openai": settings.OPENAI_API_KEY,
            "azure_speech": settings.TTS_SETTINGS.get("azure", {}).get("key", ""),
            "azure_region": settings.TTS_SETTINGS.get("azure", {}).get("region", ""),
            "google_cloud": settings.TTS_SETTINGS.get("google_cloud", {}).get("api_key", ""),
        }

        self.tts = TTSIntegration(api_keys)

    async def synthesize(
        self,
        script: Dict[str, Any],
        preferred_provider: Optional[str] = None,
    ):
        text = self._extract_text(script)
        if not text:
            raise ValueError("VoicePipelineに渡された台本からテキストを抽出できませんでした")

        selected_provider_key = self._resolve_provider_key(preferred_provider)
        provider_voice = settings.TTS_SETTINGS.get(selected_provider_key, {}).get("voice_id")
        language = script.get("language") or settings.YOUTUBE_SETTINGS.get("default_language", "ja")

        voice_config = VoiceConfig(
            voice_id=provider_voice or "default",
            language=language,
            gender="female",
            age_range="adult",
            accent="japanese" if language == "ja" else "",
            quality="high",
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pipeline_tts_{timestamp}".replace(" ", "_")
        output_path = self.output_dir / f"{filename}.mp3"

        provider_enum = self._to_provider_enum(selected_provider_key)

        return await self.tts.generate_audio(
            text=text,
            output_path=output_path,
            provider=provider_enum,
            voice_config=voice_config,
        )

    def _extract_text(self, script: Dict[str, Any]) -> str:
        if "segments" in script and isinstance(script["segments"], list):
            return "\n\n".join(str(seg.get("content", "")) for seg in script["segments"])
        return str(script.get("content", ""))

    def _resolve_provider_key(self, preferred_provider: Optional[str]) -> str:
        if preferred_provider and preferred_provider in settings.TTS_SETTINGS:
            return preferred_provider
        configured = settings.TTS_SETTINGS.get("provider", "none")
        if configured != "none" and configured in settings.TTS_SETTINGS:
            return configured
        return "elevenlabs"

    def _to_provider_enum(self, provider_key: str) -> Optional[TTSProvider]:
        try:
            return TTSProvider(provider_key)
        except ValueError:
            return None
