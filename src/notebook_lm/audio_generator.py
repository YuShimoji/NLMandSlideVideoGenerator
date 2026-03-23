"""
音声情報データクラス + AudioGenerator レガシースタブ

DESIGN NOTE (DESIGN_FOUNDATIONS.md Section 3):
  音声合成は YMM4 の責務。Python は音声を生成しない。
  AudioInfo は CSV/YMM4 パイプラインのデータ受け渡しに使用される。
  AudioGenerator はレガシー互換スタブ (プレースホルダー WAV のみ生成)。
"""
import time
import wave
from pathlib import Path
from dataclasses import dataclass
from typing import List

from core.utils.logger import logger
from config.settings import settings
from .research_models import SourceInfo


@dataclass
class AudioInfo:
    """音声情報

    CSV/YMM4 パイプラインでの音声メタデータ受け渡しに使用。
    互換性のため、品質スコアやファイルサイズなどは省略可能な引数として扱う。
    """
    file_path: Path
    duration: float
    quality_score: float = 1.0
    sample_rate: int = 44100
    file_size: int = 0
    language: str = "ja"
    channels: int = 2


class AudioGenerator:
    """音声生成レガシースタブ

    音声合成は YMM4 の責務。このクラスはプレースホルダー WAV のみ生成する。
    既存コードの import 互換性のために維持。
    """

    def __init__(self):
        self.audio_quality_threshold = settings.NOTEBOOK_LM_SETTINGS["audio_quality_threshold"]
        self.max_duration = settings.NOTEBOOK_LM_SETTINGS["max_audio_duration"]
        self.output_dir = settings.AUDIO_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_audio(self, sources: List[SourceInfo]) -> AudioInfo:
        """プレースホルダー WAV を生成する (音声合成は YMM4 の責務)。"""
        logger.warning("音声合成はYMM4で実施。プレースホルダーを生成します。")
        output_path = self.output_dir / f"placeholder_audio_{int(time.time())}.wav"

        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(2)
            wav_file.setframerate(44100)
            wav_file.writeframes(b'\x00\x00' * 44100 * 2)

        return AudioInfo(
            file_path=output_path,
            duration=1.0,
            quality_score=0.5,
            sample_rate=44100,
            file_size=output_path.stat().st_size,
            language="ja",
            channels=2,
        )

    async def regenerate_audio_if_needed(
        self, audio_info: AudioInfo, sources: List[SourceInfo]
    ) -> AudioInfo:
        """互換スタブ: 常に既存の audio_info をそのまま返す。"""
        return audio_info
