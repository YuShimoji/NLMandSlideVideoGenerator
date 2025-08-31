"""
字幕生成モジュール
台本から字幕ファイルを生成
"""
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import re

# 基本的なロガー設定（loguruの代替）
class SimpleLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def success(self, msg): print(f"[SUCCESS] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")
    def debug(self, msg): print(f"[DEBUG] {msg}")

logger = SimpleLogger()

from config.settings import settings
from notebook_lm.transcript_processor import TranscriptInfo, TranscriptSegment

@dataclass
class SubtitleSegment:
    """字幕セグメント"""
    index: int
    start_time: str
    end_time: str
    text: str

class SubtitleGenerator:
    """字幕生成クラス"""
    
    def __init__(self):
        self.subtitle_settings = settings.SUBTITLE_SETTINGS
        self.output_dir = settings.TRANSCRIPTS_DIR
        
    async def generate_subtitles(self, transcript_info: TranscriptInfo) -> Path:
        """
        台本から字幕ファイルを生成
        
        Args:
            transcript_info: 台本情報
            
        Returns:
            Path: 生成された字幕ファイルパス
        """
        logger.info("字幕生成開始")
        
        try:
            # Step 1: 字幕セグメント作成
            subtitle_segments = self._create_subtitle_segments(transcript_info.segments)
            
            # Step 2: 字幕の最適化
            optimized_segments = self._optimize_subtitles(subtitle_segments)
            
            # Step 3: SRTファイル生成
            srt_path = await self._generate_srt_file(optimized_segments, transcript_info.title)
            
            # Step 4: VTTファイル生成（Web用）
            vtt_path = await self._generate_vtt_file(optimized_segments, transcript_info.title)
            
            logger.success(f"字幕生成完了: {srt_path}")
            return srt_path
            
        except Exception as e:
            logger.error(f"字幕生成エラー: {str(e)}")
            raise
    
    def _create_subtitle_segments(self, transcript_segments: List[TranscriptSegment]) -> List[SubtitleSegment]:
        """
        台本セグメントから字幕セグメントを作成
        
        Args:
            transcript_segments: 台本セグメント一覧
            
        Returns:
            List[SubtitleSegment]: 字幕セグメント一覧
        """
        subtitle_segments = []
        
        for i, segment in enumerate(transcript_segments, 1):
            # 時間をSRT形式に変換
            start_time = self._seconds_to_srt_time(segment.start_time)
            end_time = self._seconds_to_srt_time(segment.end_time)
            
            # テキストの前処理
            cleaned_text = self._clean_subtitle_text(segment.text)
            
            subtitle_segment = SubtitleSegment(
                index=i,
                start_time=start_time,
                end_time=end_time,
                text=cleaned_text
            )
            
            subtitle_segments.append(subtitle_segment)
        
        return subtitle_segments
    
    def _clean_subtitle_text(self, text: str) -> str:
        """
        字幕用にテキストをクリーニング
        
        Args:
            text: 元のテキスト
            
        Returns:
            str: クリーニング済みテキスト
        """
        # 不要な記号や文字を除去
        cleaned = re.sub(r'[「」『』【】〈〉《》]', '', text)
        
        # 連続する空白を単一に
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # 行の長さ制限（字幕の可読性向上）
        if len(cleaned) > 50:
            # 句読点で分割を試行
            sentences = re.split(r'[。！？]', cleaned)
            if len(sentences) > 1 and len(sentences[0]) <= 50:
                cleaned = sentences[0] + ('。' if sentences[0] else '')
            else:
                cleaned = cleaned[:47] + "..."
        
        return cleaned.strip()
    
    def _optimize_subtitles(self, subtitle_segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """
        字幕を最適化
        
        Args:
            subtitle_segments: 字幕セグメント一覧
            
        Returns:
            List[SubtitleSegment]: 最適化された字幕セグメント一覧
        """
        optimized = []
        
        for segment in subtitle_segments:
            # 最小表示時間の確保（1秒以上）
            start_seconds = self._srt_time_to_seconds(segment.start_time)
            end_seconds = self._srt_time_to_seconds(segment.end_time)
            
            if end_seconds - start_seconds < 1.0:
                end_seconds = start_seconds + 1.0
                segment.end_time = self._seconds_to_srt_time(end_seconds)
            
            # 読み取り速度の調整（1秒あたり最大15文字）
            text_length = len(segment.text)
            duration = end_seconds - start_seconds
            reading_speed = text_length / duration
            
            if reading_speed > 15:  # 読み取り速度が速すぎる場合
                required_duration = text_length / 15
                segment.end_time = self._seconds_to_srt_time(start_seconds + required_duration)
            
            optimized.append(segment)
        
        # 重複時間の解決
        optimized = self._resolve_time_overlaps(optimized)
        
        return optimized
    
    def _resolve_time_overlaps(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """
        字幕の時間重複を解決
        
        Args:
            segments: 字幕セグメント一覧
            
        Returns:
            List[SubtitleSegment]: 重複解決済みセグメント一覧
        """
        if len(segments) <= 1:
            return segments
        
        resolved = [segments[0]]
        
        for i in range(1, len(segments)):
            current = segments[i]
            previous = resolved[-1]
            
            current_start = self._srt_time_to_seconds(current.start_time)
            previous_end = self._srt_time_to_seconds(previous.end_time)
            
            # 重複がある場合
            if current_start < previous_end:
                # 前のセグメントの終了時間を調整
                gap_time = 0.1  # 100ms のギャップ
                new_previous_end = current_start - gap_time
                
                if new_previous_end > self._srt_time_to_seconds(previous.start_time):
                    previous.end_time = self._seconds_to_srt_time(new_previous_end)
            
            resolved.append(current)
        
        return resolved
    
    async def _generate_srt_file(self, segments: List[SubtitleSegment], title: str) -> Path:
        """
        SRTファイルを生成
        
        Args:
            segments: 字幕セグメント一覧
            title: タイトル
            
        Returns:
            Path: 生成されたSRTファイルパス
        """
        # ファイル名生成
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        srt_path = self.output_dir / f"{safe_title}_subtitles.srt"
        
        # ディレクトリ作成
        srt_path.parent.mkdir(parents=True, exist_ok=True)
        
        # SRTファイル書き込み
        with open(srt_path, 'w', encoding='utf-8') as f:
            for segment in segments:
                f.write(f"{segment.index}\n")
                f.write(f"{segment.start_time} --> {segment.end_time}\n")
                f.write(f"{segment.text}\n\n")
        
        logger.info(f"SRTファイル生成完了: {srt_path}")
        return srt_path
    
    async def _generate_vtt_file(self, segments: List[SubtitleSegment], title: str) -> Path:
        """
        VTTファイルを生成（Web用）
        
        Args:
            segments: 字幕セグメント一覧
            title: タイトル
            
        Returns:
            Path: 生成されたVTTファイルパス
        """
        # ファイル名生成
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        vtt_path = self.output_dir / f"{safe_title}_subtitles.vtt"
        
        # VTTファイル書き込み
        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            
            for segment in segments:
                # VTT形式の時間（ミリ秒表記）
                start_vtt = self._srt_to_vtt_time(segment.start_time)
                end_vtt = self._srt_to_vtt_time(segment.end_time)
                
                f.write(f"{start_vtt} --> {end_vtt}\n")
                f.write(f"{segment.text}\n\n")
        
        logger.info(f"VTTファイル生成完了: {vtt_path}")
        return vtt_path
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """
        秒をSRT形式の時間に変換
        
        Args:
            seconds: 秒数
            
        Returns:
            str: SRT形式の時間
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _srt_time_to_seconds(self, srt_time: str) -> float:
        """
        SRT形式の時間を秒に変換
        
        Args:
            srt_time: SRT形式の時間
            
        Returns:
            float: 秒数
        """
        time_part, millis_part = srt_time.split(',')
        hours, minutes, seconds = map(int, time_part.split(':'))
        millis = int(millis_part)
        
        return hours * 3600 + minutes * 60 + seconds + millis / 1000.0
    
    def _srt_to_vtt_time(self, srt_time: str) -> str:
        """
        SRT時間をVTT時間に変換
        
        Args:
            srt_time: SRT形式の時間
            
        Returns:
            str: VTT形式の時間
        """
        # SRTの「,」をVTTの「.」に変更
        return srt_time.replace(',', '.')
    
    def add_styling_to_subtitles(self, srt_path: Path) -> Path:
        """
        字幕にスタイリングを追加
        
        Args:
            srt_path: SRTファイルパス
            
        Returns:
            Path: スタイル付きSRTファイルパス
        """
        styled_path = srt_path.with_name(f"{srt_path.stem}_styled{srt_path.suffix}")
        
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # スタイルタグを追加
        styled_content = content.replace(
            '\n\n',
            '\n<font color="white" size="24">\n\n'
        )
        
        with open(styled_path, 'w', encoding='utf-8') as f:
            f.write(styled_content)
        
        return styled_path
