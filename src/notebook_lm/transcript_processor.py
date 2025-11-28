"""
文字起こし処理モジュール
NotebookLMを使用した音声の文字起こしと台本構造化
"""
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import json
import re
from datetime import datetime

# 基本的なロガー設定（loguruの代替）
from core.utils.logger import logger

from config.settings import settings
from .audio_generator import AudioInfo

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
    """文字起こし処理クラス"""
    
    def __init__(self):
        self.accuracy_threshold = settings.NOTEBOOK_LM_SETTINGS["transcript_accuracy_threshold"]
        self.output_dir = settings.TRANSCRIPTS_DIR
        
    async def process_audio(self, audio_info: AudioInfo) -> TranscriptInfo:
        """
        音声ファイルを処理して台本を生成
        
        Args:
            audio_info: 音声情報
            
        Returns:
            TranscriptInfo: 生成された台本情報
        """
        logger.info(f"文字起こし処理開始: {audio_info.file_path}")
        
        try:
            # Step 1: NotebookLMに音声をアップロード
            upload_session = await self._upload_audio_to_notebook(audio_info.file_path)
            
            # Step 2: 文字起こし実行
            raw_transcript = await self._execute_transcription(upload_session)
            
            # Step 3: 台本構造化
            structured_transcript = await self._structure_transcript(raw_transcript, audio_info)
            
            # Step 4: 内容検証・修正
            verified_transcript = await self._verify_and_correct_transcript(structured_transcript)
            
            # Step 5: 台本保存
            await self._save_transcript(verified_transcript)
            
            logger.success(f"文字起こし処理完了: 精度={verified_transcript.accuracy_score:.2f}")
            return verified_transcript
            
        except Exception as e:
            logger.error(f"文字起こし処理エラー: {str(e)}")
            raise

    async def process_transcript(self, audio_info: AudioInfo) -> TranscriptInfo:
        return await self.process_audio(audio_info)
    
    async def _upload_audio_to_notebook(self, audio_path: Path) -> str:
        """
        音声ファイルをNotebookLMにアップロード
        
        Args:
            audio_path: 音声ファイルパス
            
        Returns:
            str: アップロードセッションID
        """
        logger.debug("NotebookLMに音声アップロード中...")
        
        # TODO: 実際のNotebookLM音声アップロード実装
        # Seleniumまたは専用APIを使用
        
        session_id = f"transcript_session_{int(datetime.now().timestamp())}"
        logger.debug(f"音声アップロード完了: {session_id}")
        
        return session_id
    
    async def _execute_transcription(self, session_id: str) -> str:
        """
        文字起こしを実行
        
        Args:
            session_id: アップロードセッションID
            
        Returns:
            str: 生の文字起こしテキスト
        """
        logger.info("文字起こし実行中...")
        
        # TODO: 実際の文字起こし実装
        # NotebookLMの文字起こし機能を使用
        
        # プレースホルダー実装
        await asyncio.sleep(2)
        
        # サンプル文字起こしテキスト
        sample_transcript = """
        [00:00] ナレーター1: こんにちは、今日はAI技術の最新動向について解説します。
        [00:15] ナレーター2: まず、機械学習の基本概念から始めましょう。
        [00:30] ナレーター1: 機械学習とは、データから自動的にパターンを学習する技術です。
        [01:00] ナレーター2: 特に深層学習は、近年大きな注目を集めています。
        """
        
        logger.info("文字起こし完了")
        return sample_transcript
    
    async def _structure_transcript(self, raw_transcript: str, audio_info: AudioInfo) -> TranscriptInfo:
        """
        生の文字起こしを構造化
        
        Args:
            raw_transcript: 生の文字起こしテキスト
            audio_info: 音声情報
            
        Returns:
            TranscriptInfo: 構造化された台本情報
        """
        logger.debug("台本構造化中...")
        
        # タイムスタンプとテキストを解析
        segments = self._parse_transcript_segments(raw_transcript)
        
        # タイトル生成
        title = self._generate_title_from_content(segments)
        
        # 台本情報作成
        if segments:
            last_end_time = segments[-1].end_time
            total_duration = min(audio_info.duration, last_end_time) if audio_info.duration else last_end_time
        else:
            total_duration = audio_info.duration

        transcript_info = TranscriptInfo(
            title=title,
            total_duration=total_duration,
            segments=segments,
            accuracy_score=0.95,  # 初期値
            created_at=datetime.now(),
            source_audio_path=str(audio_info.file_path)
        )
        
        logger.debug(f"台本構造化完了: {len(segments)}セグメント")
        return transcript_info
    
    def _parse_transcript_segments(self, raw_transcript: str) -> List[TranscriptSegment]:
        """
        生の文字起こしからセグメントを解析
        
        Args:
            raw_transcript: 生の文字起こしテキスト
            
        Returns:
            List[TranscriptSegment]: 解析されたセグメント一覧
        """
        segments = []
        lines = raw_transcript.strip().split('\n')
        
        segment_id = 1
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # タイムスタンプパターンマッチング
            timestamp_pattern = r'\[(\d{2}):(\d{2})\]\s*([^:]+):\s*(.+)'
            match = re.match(timestamp_pattern, line)
            
            if match:
                minutes, seconds, speaker, text = match.groups()
                start_time = int(minutes) * 60 + int(seconds)
                
                # 次のセグメントの開始時間を推定（仮に15秒後とする）
                end_time = start_time + 15
                
                # キーポイント抽出
                key_points = self._extract_key_points(text)
                
                # スライド提案生成
                slide_suggestion = self._generate_slide_suggestion(text, key_points)
                
                segment = TranscriptSegment(
                    id=segment_id,
                    start_time=start_time,
                    end_time=end_time,
                    speaker=speaker.strip(),
                    text=text.strip(),
                    key_points=key_points,
                    slide_suggestion=slide_suggestion,
                    confidence_score=0.95
                )
                
                segments.append(segment)
                segment_id += 1
        
        # 終了時間の調整
        for i in range(len(segments) - 1):
            segments[i].end_time = segments[i + 1].start_time
        
        return segments
    
    def _extract_key_points(self, text: str) -> List[str]:
        """
        テキストからキーポイントを抽出
        
        Args:
            text: 対象テキスト
            
        Returns:
            List[str]: 抽出されたキーポイント
        """
        # 簡単な実装：重要そうなキーワードを抽出
        important_words = []
        
        # 技術用語パターン
        tech_patterns = [
            r'AI|人工知能|機械学習|深層学習|ディープラーニング',
            r'データ|アルゴリズム|モデル|学習',
            r'技術|システム|プラットフォーム|ツール'
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            important_words.extend(matches)
        
        # 重複除去と上位3つを返す
        unique_words = list(set(important_words))
        return unique_words[:3]
    
    def _generate_slide_suggestion(self, text: str, key_points: List[str]) -> str:
        """
        スライド内容の提案を生成
        
        Args:
            text: セグメントテキスト
            key_points: キーポイント
            
        Returns:
            str: スライド提案
        """
        if not key_points:
            return text[:100] + "..." if len(text) > 100 else text
        
        # キーポイントを中心としたスライド提案
        suggestion = f"【{', '.join(key_points)}】\n"
        
        # テキストの要約（最初の50文字）
        summary = text[:50] + "..." if len(text) > 50 else text
        suggestion += summary
        
        return suggestion
    
    def _generate_title_from_content(self, segments: List[TranscriptSegment]) -> str:
        """
        セグメント内容からタイトルを生成
        
        Args:
            segments: セグメント一覧
            
        Returns:
            str: 生成されたタイトル
        """
        if not segments:
            return "解説動画"
        
        # 最初のセグメントから主要なキーワードを抽出
        first_segment_text = segments[0].text
        
        # 全セグメントのキーポイントを収集
        all_key_points = []
        for segment in segments:
            all_key_points.extend(segment.key_points)
        
        # 最頻出キーワードを特定
        from collections import Counter
        keyword_counts = Counter(all_key_points)
        
        if keyword_counts:
            top_keyword = keyword_counts.most_common(1)[0][0]
            return f"{top_keyword}について解説"
        
        return "解説動画"
    
    async def _verify_and_correct_transcript(self, transcript_info: TranscriptInfo) -> TranscriptInfo:
        """
        台本内容の検証・修正
        
        Args:
            transcript_info: 台本情報
            
        Returns:
            TranscriptInfo: 検証済み台本情報
        """
        logger.debug("台本内容検証中...")
        
        # 精度スコア計算
        accuracy_score = self._calculate_transcript_accuracy(transcript_info)
        transcript_info.accuracy_score = accuracy_score
        
        # 低精度の場合の修正処理
        if accuracy_score < self.accuracy_threshold:
            logger.warning(f"台本精度が低いです: {accuracy_score:.2f}")
            transcript_info = await self._correct_low_accuracy_transcript(transcript_info)
        
        # セグメント間の整合性チェック
        transcript_info = self._fix_segment_consistency(transcript_info)
        
        logger.debug(f"台本検証完了: 精度={transcript_info.accuracy_score:.2f}")
        return transcript_info
    
    def _calculate_transcript_accuracy(self, transcript_info: TranscriptInfo) -> float:
        """
        台本精度を計算
        
        Args:
            transcript_info: 台本情報
            
        Returns:
            float: 精度スコア (0.0-1.0)
        """
        if not transcript_info.segments:
            return 0.0
        
        # セグメント信頼度の平均
        confidence_scores = [seg.confidence_score for seg in transcript_info.segments]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        # 時間軸の整合性チェック
        time_consistency = self._check_time_consistency(transcript_info.segments)
        
        # 総合精度スコア
        accuracy = (avg_confidence + time_consistency) / 2
        return accuracy
    
    def _check_time_consistency(self, segments: List[TranscriptSegment]) -> float:
        """
        時間軸の整合性をチェック
        
        Args:
            segments: セグメント一覧
            
        Returns:
            float: 整合性スコア (0.0-1.0)
        """
        if len(segments) < 2:
            return 1.0
        
        consistent_count = 0
        total_checks = len(segments) - 1
        
        for i in range(total_checks):
            current_seg = segments[i]
            next_seg = segments[i + 1]
            
            # 現在のセグメントの終了時間が次のセグメントの開始時間と一致するか
            if abs(current_seg.end_time - next_seg.start_time) <= 1.0:  # 1秒の誤差許容
                consistent_count += 1
        
        return consistent_count / total_checks if total_checks > 0 else 1.0
    
    async def _correct_low_accuracy_transcript(self, transcript_info: TranscriptInfo) -> TranscriptInfo:
        """
        低精度台本の修正
        
        Args:
            transcript_info: 台本情報
            
        Returns:
            TranscriptInfo: 修正済み台本情報
        """
        logger.info("低精度台本の修正実行中...")
        
        # TODO: 実際の修正処理実装
        # - 音声の再解析
        # - 手動修正インターフェースの提供
        # - AI による自動修正
        
        # プレースホルダー: 信頼度スコアを調整
        for segment in transcript_info.segments:
            if segment.confidence_score < 0.8:
                segment.confidence_score = 0.8
        
        # 精度スコア再計算
        transcript_info.accuracy_score = self._calculate_transcript_accuracy(transcript_info)
        
        return transcript_info
    
    def _fix_segment_consistency(self, transcript_info: TranscriptInfo) -> TranscriptInfo:
        """
        セグメント間の整合性を修正
        
        Args:
            transcript_info: 台本情報
            
        Returns:
            TranscriptInfo: 修正済み台本情報
        """
        segments = transcript_info.segments
        
        # 時間軸の修正
        for i in range(len(segments) - 1):
            current_seg = segments[i]
            next_seg = segments[i + 1]
            
            # 重複や逆転の修正
            if current_seg.end_time > next_seg.start_time:
                # 中間点で分割
                mid_time = (current_seg.start_time + next_seg.end_time) / 2
                current_seg.end_time = mid_time
                next_seg.start_time = mid_time
        
        return transcript_info
    
    async def _save_transcript(self, transcript_info: TranscriptInfo):
        """
        台本をファイルに保存
        
        Args:
            transcript_info: 台本情報
        """
        # JSONファイルとして保存
        timestamp = transcript_info.created_at.strftime("%Y%m%d_%H%M%S")
        json_filename = f"transcript_{timestamp}.json"
        json_path = self.output_dir / json_filename
        
        # ディレクトリ作成
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        # JSON保存
        transcript_dict = asdict(transcript_info)
        transcript_dict['created_at'] = transcript_info.created_at.isoformat()
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_dict, f, ensure_ascii=False, indent=2)
        
        # SRTファイルとしても保存（字幕用）
        srt_filename = f"transcript_{timestamp}.srt"
        srt_path = self.output_dir / srt_filename
        
        await self._save_as_srt(transcript_info, srt_path)
        
        logger.info(f"台本保存完了: {json_path}, {srt_path}")
    
    async def _save_as_srt(self, transcript_info: TranscriptInfo, srt_path: Path):
        """
        SRT形式で台本を保存
        
        Args:
            transcript_info: 台本情報
            srt_path: SRTファイルパス
        """
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(transcript_info.segments, 1):
                # SRT形式のタイムスタンプ
                start_time = self._seconds_to_srt_time(segment.start_time)
                end_time = self._seconds_to_srt_time(segment.end_time)
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment.text}\n\n")
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """
        秒をSRT形式のタイムスタンプに変換
        
        Args:
            seconds: 秒数
            
        Returns:
            str: SRT形式タイムスタンプ
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    async def load_transcript(self, transcript_path: Path) -> TranscriptInfo:
        """
        保存された台本を読み込み
        
        Args:
            transcript_path: 台本ファイルパス
            
        Returns:
            TranscriptInfo: 読み込まれた台本情報
        """
        with open(transcript_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # TranscriptSegmentオブジェクトに変換
        segments = [
            TranscriptSegment(**seg_data) 
            for seg_data in data['segments']
        ]
        
        # TranscriptInfoオブジェクトに変換
        transcript_info = TranscriptInfo(
            title=data['title'],
            total_duration=data['total_duration'],
            segments=segments,
            accuracy_score=data['accuracy_score'],
            created_at=datetime.fromisoformat(data['created_at']),
            source_audio_path=data['source_audio_path']
        )
        
        return transcript_info
