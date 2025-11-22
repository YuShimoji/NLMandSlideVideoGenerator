"""
CSV台本ローダー

A列: 話者名, B列: テキスト のシンプルなCSVから
TranscriptSegment / TranscriptInfo を生成するユーティリティ。

P10 (CSVタイムラインモード) で、行ごとに音声が分割されているケースを主対象とし、
対応する AudioInfo リストが与えられた場合は、その duration に基づいて
start_time / end_time を割り当てる。

AudioInfo が1本だけ、または与えられない場合は、テキスト文字数ベースの
ヒューリスティックで時間を自動配分する。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

from core.utils.logger import logger
from config.settings import settings
from .audio_generator import AudioInfo
from .transcript_processor import TranscriptInfo, TranscriptSegment


@dataclass
class CsvTimelineRow:
    """CSV 1行分の情報"""

    index: int
    speaker: str
    text: str


class CsvTranscriptLoader:
    """CSV から TranscriptInfo を生成するローダー"""

    def __init__(self) -> None:
        # 文字数ベース推定時の読み上げ速度 (chars/sec のイメージ)
        self.chars_per_second: float = 6.0
        self.min_segment_duration: float = 1.0
        self.max_segment_duration: float = 15.0

    async def load_from_csv(
        self,
        csv_path: Path,
        audio_segments: Optional[Sequence[AudioInfo]] = None,
        total_audio: Optional[AudioInfo] = None,
        title: Optional[str] = None,
    ) -> TranscriptInfo:
        """CSV から TranscriptInfo を生成する

        Args:
            csv_path: CSVファイルパス (A列: 話者, B列: テキスト)
            audio_segments: 行ごとの音声情報 (1行=1 AudioInfo を想定)
            total_audio: 全体音声情報（長尺1本など）
            title: 台本タイトル（省略時はCSVファイル名）
        """

        logger.info(f"CSV台本読み込み開始: {csv_path}")

        rows = self._read_csv_rows(csv_path)
        if not rows:
            logger.warning("CSVが空、または有効な行がありません")
            return TranscriptInfo(
                title=title or csv_path.stem,
                total_duration=0.0,
                segments=[],
                accuracy_score=1.0,
                created_at=datetime.now(),
                source_audio_path=str(total_audio.file_path) if total_audio else "",
            )

        # TranscriptSegment の骨格を作成（時間情報は後で付与）
        segments: List[TranscriptSegment] = []
        for row in rows:
            segment = TranscriptSegment(
                id=row.index,
                start_time=0.0,
                end_time=0.0,
                speaker=row.speaker or "Speaker",
                text=row.text,
                key_points=[],
                slide_suggestion=row.text[:50],
                confidence_score=1.0,
            )
            segments.append(segment)

        # 時間情報を付与
        self._assign_timings(segments, audio_segments=audio_segments, total_audio=total_audio)

        total_duration = segments[-1].end_time if segments else 0.0
        transcript_info = TranscriptInfo(
            title=title or csv_path.stem,
            total_duration=total_duration,
            segments=segments,
            accuracy_score=1.0,
            created_at=datetime.now(),
            source_audio_path=str(total_audio.file_path) if total_audio else "",
        )

        logger.info(
            f"CSV台本読み込み完了: {len(segments)}セグメント, total_duration={total_duration:.2f}s"
        )
        return transcript_info

    def _read_csv_rows(self, csv_path: Path) -> List[CsvTimelineRow]:
        """CSV を読み込んで CsvTimelineRow のリストに変換

        - 空行は無視
        - 列数が2未満の行は無視
        """
        rows: List[CsvTimelineRow] = []

        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            index = 1
            for raw_row in reader:
                # 空行スキップ
                if not raw_row or not any(col.strip() for col in raw_row):
                    continue

                if len(raw_row) < 2:
                    logger.debug(f"列数不足の行をスキップ: {raw_row}")
                    continue

                speaker = raw_row[0].strip()
                text = raw_row[1].strip()

                if not text:
                    # テキストが空の行はスキップ
                    logger.debug(f"テキストが空の行をスキップ: {raw_row}")
                    continue

                rows.append(CsvTimelineRow(index=index, speaker=speaker, text=text))
                index += 1

        return rows

    def _assign_timings(
        self,
        segments: List[TranscriptSegment],
        audio_segments: Optional[Sequence[AudioInfo]] = None,
        total_audio: Optional[AudioInfo] = None,
    ) -> None:
        """セグメントに start_time / end_time を割り当てる

        優先順位:
        1. audio_segments があり、長さがセグメント数と一致する場合:
           各 AudioInfo.duration をそのまま使用
        2. それ以外: total_audio.duration またはテキスト長から
           ヒューリスティックに時間を配分
        """
        if not segments:
            return

        # ケース1: 行ごとの AudioInfo がある場合
        if audio_segments and len(audio_segments) == len(segments):
            logger.debug("audio_segments に基づいてタイミングを割り当て")
            current = 0.0
            for seg, audio in zip(segments, audio_segments):
                duration = float(getattr(audio, "duration", 0.0) or 0.0)
                if duration <= 0:
                    # duration が無効な場合はテキスト長から推定
                    duration = max(
                        self.min_segment_duration,
                        len(seg.text) / self.chars_per_second,
                    )
                seg.start_time = current
                current += duration
                seg.end_time = current
            return

        # ケース2: ヒューリスティックに基づく自動配分
        # 全体時間の決定
        if total_audio and getattr(total_audio, "duration", 0.0) and total_audio.duration > 0:
            total_duration = float(total_audio.duration)
        else:
            # テキスト長からざっくり推定
            total_chars = sum(len(seg.text) for seg in segments)
            if total_chars > 0:
                total_duration = total_chars / self.chars_per_second
            else:
                total_duration = len(segments) * self.min_segment_duration

        logger.debug(
            f"ヒューリスティックでタイミング割り当て: total_duration≈{total_duration:.2f}s"
        )

        # 各セグメントの重み (文字数比率)
        total_chars = sum(max(len(seg.text), 1) for seg in segments)
        current = 0.0
        for seg in segments:
            weight = max(len(seg.text), 1) / total_chars
            duration = total_duration * weight
            # 最小/最大表示時間をクリップ
            duration = max(self.min_segment_duration, min(duration, self.max_segment_duration))

            seg.start_time = current
            current += duration
            seg.end_time = current
