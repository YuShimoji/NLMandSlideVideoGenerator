"""No-op TTS integration stub.

The full external TTS layer (ElevenLabs, OpenAI, Azure, Google Cloud) was removed
during dependency cleanup (2026-03-07). YMM4 built-in voice is the sole
recommended TTS method.

This stub preserves type definitions to prevent ImportError in modules that
reference TTSIntegration, TTSProvider, or VoiceConfig.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class TTSProvider(Enum):
    """TTS provider (stub - no active providers)."""

    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    AZURE = "azure"
    GOOGLE_CLOUD = "google_cloud"


@dataclass
class VoiceConfig:
    """Voice configuration (stub)."""

    voice_id: str = "default"
    language: str = "ja"
    gender: str = "female"
    age_range: str = "adult"
    accent: str = "japanese"
    quality: str = "high"


class TTSIntegration:
    """No-op TTS integration. All calls return safe defaults."""

    def __init__(self, api_keys: Optional[Dict[str, str]] = None) -> None:
        self.api_keys = api_keys or {}

    async def generate_audio(
        self,
        text: str,
        output_path: Any = None,
        voice_config: Optional[VoiceConfig] = None,
        provider: Optional[TTSProvider] = None,
    ) -> Path:
        raise NotImplementedError(
            "External TTS providers have been removed. Use YMM4 built-in voice."
        )

    async def get_available_voices(
        self, provider: TTSProvider
    ) -> List[VoiceConfig]:
        return []

    def get_status(self) -> Dict[str, Any]:
        return {"active_providers": [], "note": "TTS stub - use YMM4"}
