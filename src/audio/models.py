"""音声関連データモデル."""

from dataclasses import dataclass


@dataclass
class VoiceConfig:
    """Voice configuration."""

    voice_id: str = "default"
    language: str = "ja"
    gender: str = "female"
    age_range: str = "adult"
    accent: str = "japanese"
    quality: str = "high"
