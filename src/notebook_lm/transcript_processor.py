"""
台本データクラス + テキストパース/保存ユーティリティ

DESIGN NOTE (DESIGN_FOUNDATIONS.md Section 0):
  台本品質は NotebookLM が生成する。Gemini は構造化のみ担当。
  TranscriptInfo / TranscriptSegment はパイプライン全体で使用されるデータクラス。

  音声→テキスト化は:
    - SP-051 AudioTranscriber (Gemini Audio API) で自動化、または
    - NotebookLM Web UI で手動テキスト化
  構造化は:
    - GeminiIntegration.structure_transcript() で実行

  TranscriptProcessor は旧シミュレーションコードを撤去し、
  テキストパース・保存/読込のユーティリティとして維持。
"""
import json
import re
from typing import List
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

from core.utils.logger import logger


@dataclass
class TranscriptSegment:
    """台本セグメント"""
    id: int
    start_time: float
    end_time: float
    speaker: str
    text: str
    key_points: List[str]
    slide_suggestion: str
    confidence_score: float


@dataclass
class TranscriptInfo:
    """台本情報"""
    title: str
    total_duration: float
    segments: List[TranscriptSegment]
    accuracy_score: float
    created_at: datetime
    source_audio_path: str


class TranscriptProcessor:
    """台本テキストのパース・保存/読込ユーティリティ

    旧来の音声アップロード・文字起こしシミュレーションは撤去済み。
    音声→テキスト化は AudioTranscriber (SP-051) または手動で行う。
    """

    def __init__(self, output_dir: Path | None = None):
        if output_dir:
            self.output_dir = output_dir
        else:
            from config.settings import settings
            self.output_dir = settings.TRANSCRIPTS_DIR

    async def process_audio(self, audio_info) -> TranscriptInfo:
        """レガシー互換スタブ: 空の TranscriptInfo を返す。

        旧パイプライン (main.py / pipeline.py) からの呼び出しに対応。
        実際の音声→テキスト化は AudioTranscriber (SP-051) を使用すること。
        """
        logger.warning("process_audio() はレガシースタブです。AudioTranscriber を使用してください。")
        return TranscriptInfo(
            title="(stub)",
            total_duration=getattr(audio_info, "duration", 0.0),
            segments=[],
            accuracy_score=0.0,
            created_at=datetime.now(),
            source_audio_path=str(getattr(audio_info, "file_path", "")),
        )

    def parse_transcript_text(self, raw_transcript: str) -> List[TranscriptSegment]:
        """生の文字起こしテキストからセグメントを解析する

        フォーマット: [MM:SS] Speaker: text

        Args:
            raw_transcript: 生の文字起こしテキスト

        Returns:
            解析されたセグメントリスト
        """
        segments = []
        lines = raw_transcript.strip().split('\n')

        segment_id = 1
        timestamp_pattern = r'\[(\d{2}):(\d{2})\]\s*([^:]+):\s*(.+)'

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = re.match(timestamp_pattern, line)
            if not match:
                continue

            minutes, seconds, speaker, text = match.groups()
            start_time = int(minutes) * 60 + int(seconds)
            end_time = start_time + 15  # 仮の終了時間

            segment = TranscriptSegment(
                id=segment_id,
                start_time=start_time,
                end_time=end_time,
                speaker=speaker.strip(),
                text=text.strip(),
                key_points=[],
                slide_suggestion="",
                confidence_score=0.95,
            )
            segments.append(segment)
            segment_id += 1

        # 終了時間を次のセグメントの開始時間で調整
        for i in range(len(segments) - 1):
            segments[i].end_time = segments[i + 1].start_time

        return segments

    async def save_transcript(self, transcript_info: TranscriptInfo) -> Path:
        """台本をJSON + SRTファイルに保存する

        Args:
            transcript_info: 台本情報

        Returns:
            JSONファイルパス
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = transcript_info.created_at.strftime("%Y%m%d_%H%M%S")
        json_path = self.output_dir / f"transcript_{timestamp}.json"
        srt_path = self.output_dir / f"transcript_{timestamp}.srt"

        # JSON 保存
        transcript_dict = asdict(transcript_info)
        transcript_dict['created_at'] = transcript_info.created_at.isoformat()
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_dict, f, ensure_ascii=False, indent=2)

        # SRT 保存
        self._save_as_srt(transcript_info, srt_path)

        logger.info(f"台本保存完了: {json_path}, {srt_path}")
        return json_path

    def _save_as_srt(self, transcript_info: TranscriptInfo, srt_path: Path) -> None:
        """SRT形式で台本を保存"""
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(transcript_info.segments, 1):
                start = self._seconds_to_srt_time(segment.start_time)
                end = self._seconds_to_srt_time(segment.end_time)
                f.write(f"{i}\n{start} --> {end}\n{segment.text}\n\n")

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """秒をSRT形式タイムスタンプに変換"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    async def load_transcript(self, transcript_path: Path) -> TranscriptInfo:
        """保存された台本を読み込み

        Args:
            transcript_path: 台本JSONファイルパス

        Returns:
            TranscriptInfo
        """
        with open(transcript_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        segments = [TranscriptSegment(**seg) for seg in data['segments']]

        return TranscriptInfo(
            title=data['title'],
            total_duration=data['total_duration'],
            segments=segments,
            accuracy_score=data['accuracy_score'],
            created_at=datetime.fromisoformat(data['created_at']),
            source_audio_path=data['source_audio_path'],
        )
