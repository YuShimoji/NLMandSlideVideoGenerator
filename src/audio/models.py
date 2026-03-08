"""音声関連データモデル."""

from dataclasses import dataclass
from enum import Enum


class TTSProvider(Enum):
    """TTS provider enum (legacy, no active providers)."""

    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    AZURE = "azure"
    GOOGLE_CLOUD = "google_cloud"


@dataclass
class VoiceConfig:
    """Voice configuration."""

    voice_id: str = "default"
    language: str = "ja"
    gender: str = "female"
    age_range: str = "adult"
    accent: str = "japanese"
    quality: str = "high"
