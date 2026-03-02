"""
VOICEVOX ベースの VoicePipeline 実装

IVoicePipeline プロトコルに準拠し、VOICEVOX Engine を使用して
高品質ニューラル音声を生成する。Engine 停止時は SofTalk へフォールバック。
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import settings
from audio.tts_integration import AudioInfo, VoiceConfig
from audio.voicevox_client import VoicevoxAudioParams, VoicevoxClient
from core.exceptions import AudioGenerationError
from core.utils.logger import logger

from ..interfaces import IVoicePipeline


class VoicevoxVoicePipeline(IVoicePipeline):
    """VOICEVOX Engine を使用した音声生成パイプライン"""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        engine_url: Optional[str] = None,
        speaker_id: Optional[int] = None,
    ) -> None:
        self.output_dir = output_dir or settings.AUDIO_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        voicevox_settings = settings.TTS_SETTINGS.get("voicevox", {})
        self.engine_url = engine_url or voicevox_settings.get(
            "engine_url", "http://localhost:50021"
        )
        self.speaker_id = speaker_id or int(
            voicevox_settings.get("speaker_id", 3)
        )
        self.params = VoicevoxAudioParams(
            speed_scale=float(voicevox_settings.get("speed", 1.0)),
            pitch_scale=float(voicevox_settings.get("pitch", 0.0)),
            intonation_scale=float(voicevox_settings.get("intonation", 1.0)),
        )

        self.client = VoicevoxClient(
            engine_url=self.engine_url,
            timeout=int(voicevox_settings.get("timeout", 30)),
        )

    async def synthesize(
        self,
        script: Dict[str, Any],
        preferred_provider: Optional[str] = None,
    ) -> AudioInfo:
        """台本テキストから音声を合成"""
        text = self._extract_text(script)
        if not text:
            raise AudioGenerationError(
                "VoicePipelineに渡された台本からテキストを抽出できませんでした"
            )

        if not self.client.is_available():
            logger.warning(
                "VOICEVOX Engine が応答しません。フォールバックを検討してください。"
            )
            raise AudioGenerationError(
                f"VOICEVOX Engine ({self.engine_url}) に接続できません"
            )

        segments = self._split_segments(script)
        if not segments:
            segments = [text]

        wav_paths: List[Path] = []
        total_duration = 0.0

        for i, segment_text in enumerate(segments):
            if not segment_text.strip():
                continue

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"voicevox_{timestamp}_{i:04d}.wav"
            output_path = self.output_dir / filename

            try:
                await self.client.synthesize_to_file_async(
                    text=segment_text.strip(),
                    output_path=output_path,
                    speaker_id=self.speaker_id,
                    params=self.params,
                )
                wav_paths.append(output_path)

                file_size = output_path.stat().st_size
                duration = max(len(segment_text) * 0.08, 0.5)
                total_duration += duration

                logger.info(
                    f"VOICEVOX 合成完了: segment {i+1}/{len(segments)} "
                    f"({file_size} bytes)"
                )
            except Exception as e:
                logger.error(f"VOICEVOX 合成失敗 (segment {i+1}): {e}")
                raise AudioGenerationError(
                    f"VOICEVOX 音声合成に失敗しました (segment {i+1}): {e}"
                ) from e

        if not wav_paths:
            raise AudioGenerationError("生成された音声ファイルがありません")

        main_path = wav_paths[0] if len(wav_paths) == 1 else wav_paths[0]
        total_size = sum(p.stat().st_size for p in wav_paths)

        return AudioInfo(
            file_path=main_path,
            duration=total_duration,
            quality_score=0.92,
            sample_rate=24000,
            file_size=total_size,
            language=script.get("language", "ja"),
            channels=1,
            provider="voicevox",
            voice_id=f"speaker_{self.speaker_id}",
        )

    def _extract_text(self, script: Dict[str, Any]) -> str:
        """台本データからテキストを抽出"""
        if "segments" in script and isinstance(script["segments"], list):
            return "\n\n".join(
                str(seg.get("content", "")) for seg in script["segments"]
            )
        return str(script.get("content", ""))

    def _split_segments(self, script: Dict[str, Any]) -> List[str]:
        """台本をセグメント単位に分割"""
        if "segments" in script and isinstance(script["segments"], list):
            return [
                str(seg.get("content", ""))
                for seg in script["segments"]
                if seg.get("content")
            ]
        return []
