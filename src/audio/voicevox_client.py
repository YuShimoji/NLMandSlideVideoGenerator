"""
VOICEVOX Engine REST API クライアント

VOICEVOX Engine（http://localhost:50021）と通信し、
高品質ニューラルTTS音声を生成する。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from core.utils.logger import logger


@dataclass
class VoicevoxSpeaker:
    """VOICEVOX スピーカー情報"""
    id: int
    name: str
    style_name: str = ""
    style_id: int = 0


@dataclass
class VoicevoxAudioParams:
    """VOICEVOX 音声パラメータ"""
    speed_scale: float = 1.0
    pitch_scale: float = 0.0
    intonation_scale: float = 1.0
    volume_scale: float = 1.0
    pre_phoneme_length: float = 0.1
    post_phoneme_length: float = 0.1


DEFAULT_SPEAKERS: List[VoicevoxSpeaker] = [
    VoicevoxSpeaker(id=3, name="ずんだもん", style_name="ノーマル", style_id=3),
    VoicevoxSpeaker(id=2, name="四国めたん", style_name="ノーマル", style_id=2),
    VoicevoxSpeaker(id=0, name="四国めたん", style_name="あまあま", style_id=0),
    VoicevoxSpeaker(id=1, name="ずんだもん", style_name="あまあま", style_id=1),
    VoicevoxSpeaker(id=8, name="春日部つむぎ", style_name="ノーマル", style_id=8),
]


class VoicevoxClient:
    """VOICEVOX Engine REST API クライアント"""

    def __init__(
        self,
        engine_url: str = "http://localhost:50021",
        timeout: int = 30,
    ) -> None:
        self.engine_url = engine_url.rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        """VOICEVOX Engine が起動しているか確認"""
        try:
            resp = requests.get(
                f"{self.engine_url}/version",
                timeout=3,
            )
            return resp.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False

    def get_speakers(self) -> List[VoicevoxSpeaker]:
        """利用可能なスピーカー一覧を取得"""
        try:
            resp = requests.get(
                f"{self.engine_url}/speakers",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            speakers: List[VoicevoxSpeaker] = []
            for speaker_data in resp.json():
                name = speaker_data.get("name", "")
                for style in speaker_data.get("styles", []):
                    speakers.append(VoicevoxSpeaker(
                        id=style.get("id", 0),
                        name=name,
                        style_name=style.get("name", ""),
                        style_id=style.get("id", 0),
                    ))
            return speakers
        except (requests.RequestException, KeyError, TypeError) as e:
            logger.warning(f"VOICEVOX スピーカー一覧取得失敗: {e}")
            return DEFAULT_SPEAKERS

    def audio_query(
        self,
        text: str,
        speaker_id: int = 3,
        params: Optional[VoicevoxAudioParams] = None,
    ) -> Dict[str, Any]:
        """音声クエリを生成（音声合成の前処理）"""
        resp = requests.post(
            f"{self.engine_url}/audio_query",
            params={"text": text, "speaker": speaker_id},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        query = resp.json()

        if params:
            query["speedScale"] = params.speed_scale
            query["pitchScale"] = params.pitch_scale
            query["intonationScale"] = params.intonation_scale
            query["volumeScale"] = params.volume_scale
            query["prePhonemeLength"] = params.pre_phoneme_length
            query["postPhonemeLength"] = params.post_phoneme_length

        return query

    def synthesis(
        self,
        audio_query: Dict[str, Any],
        speaker_id: int = 3,
    ) -> bytes:
        """音声クエリから WAV 音声データを合成"""
        resp = requests.post(
            f"{self.engine_url}/synthesis",
            params={"speaker": speaker_id},
            json=audio_query,
            timeout=self.timeout * 3,
        )
        resp.raise_for_status()
        return resp.content

    def synthesize_to_file(
        self,
        text: str,
        output_path: Path,
        speaker_id: int = 3,
        params: Optional[VoicevoxAudioParams] = None,
    ) -> Path:
        """テキストから WAV ファイルを直接生成"""
        query = self.audio_query(text, speaker_id, params)
        wav_data = self.synthesis(query, speaker_id)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(wav_data)
        return output_path

    async def synthesize_to_file_async(
        self,
        text: str,
        output_path: Path,
        speaker_id: int = 3,
        params: Optional[VoicevoxAudioParams] = None,
    ) -> Path:
        """非同期版: テキストから WAV ファイルを生成"""
        return await asyncio.to_thread(
            self.synthesize_to_file, text, output_path, speaker_id, params
        )
