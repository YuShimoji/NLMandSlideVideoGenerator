"""
コンテンツ分割モジュール
台本をスライド生成に適した形式に分割
"""
from typing import List, Dict, Any, Optional
import re
from dataclasses import dataclass

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
class SplitContent:
    """分割されたコンテンツ"""
    slide_id: int
    title: str
    text: str
    key_points: List[str]
    duration: float
    source_segments: List[int]  # 元のセグメントID
    image_suggestions: List[str]

class ContentSplitter:
    """コンテンツ分割クラス"""
    
    def __init__(self):
        self.max_chars_per_slide = settings.SLIDES_SETTINGS["max_chars_per_slide"]
        
    async def split_for_slides(
        self, 
        transcript_info: TranscriptInfo, 
        max_slides: int
    ) -> List[Dict[str, Any]]:
        """
        台本をスライド用に分割
        
        Args:
            transcript_info: 台本情報
            max_slides: 最大スライド数
            
        Returns:
            List[Dict[str, Any]]: 分割されたコンテンツ一覧
        """
        logger.info(f"台本分割開始: {len(transcript_info.segments)}セグメント → 最大{max_slides}スライド")
        
        # Step 1: セグメントを論理的にグループ化
        segment_groups = self._group_segments_logically(transcript_info.segments)
        
        # Step 2: 文字数制限に基づく分割
        split_contents = self._split_by_character_limit(segment_groups)
        
        # Step 3: スライド数制限の適用
        if len(split_contents) > max_slides:
            split_contents = self._reduce_to_max_slides(split_contents, max_slides)
        
        # Step 4: 辞書形式に変換
        slide_contents = self._convert_to_slide_format(split_contents)
        
        logger.info(f"台本分割完了: {len(slide_contents)}スライド")
        return slide_contents
    
    def _group_segments_logically(self, segments: List[TranscriptSegment]) -> List[List[TranscriptSegment]]:
        """
        セグメントを論理的にグループ化
        
        Args:
            segments: セグメント一覧
            
        Returns:
            List[List[TranscriptSegment]]: グループ化されたセグメント
        """
        if not segments:
            return []
        
        groups = []
        current_group = [segments[0]]
        
        for i in range(1, len(segments)):
            current_segment = segments[i]
            previous_segment = segments[i-1]
            
            # グループ分割の条件
            should_split = (
                self._is_topic_change(previous_segment, current_segment) or
                self._is_speaker_change_significant(previous_segment, current_segment) or
                self._is_time_gap_significant(previous_segment, current_segment)
            )
            
            if should_split:
                groups.append(current_group)
                current_group = [current_segment]
            else:
                current_group.append(current_segment)
        
        # 最後のグループを追加
        if current_group:
            groups.append(current_group)
        
        logger.debug(f"論理的グループ化完了: {len(groups)}グループ")
        return groups
    
    def _is_topic_change(self, prev_segment: TranscriptSegment, curr_segment: TranscriptSegment) -> bool:
        """
        トピック変更を検出
        
        Args:
            prev_segment: 前のセグメント
            curr_segment: 現在のセグメント
            
        Returns:
            bool: トピック変更があるかどうか
        """
        # キーポイントの重複度をチェック
        prev_points = set(prev_segment.key_points)
        curr_points = set(curr_segment.key_points)
        
        if not prev_points or not curr_points:
            return False
        
        # 共通キーポイントの割合
        common_points = prev_points.intersection(curr_points)
        overlap_ratio = len(common_points) / len(prev_points.union(curr_points))
        
        # 重複が少ない場合はトピック変更とみなす
        return overlap_ratio < 0.3
    
    def _is_speaker_change_significant(self, prev_segment: TranscriptSegment, curr_segment: TranscriptSegment) -> bool:
        """
        話者変更が重要かどうかを判定
        
        Args:
            prev_segment: 前のセグメント
            curr_segment: 現在のセグメント
            
        Returns:
            bool: 重要な話者変更かどうか
        """
        # 話者が変わり、かつ前のセグメントが長い場合
        return (prev_segment.speaker != curr_segment.speaker and 
                (curr_segment.start_time - prev_segment.start_time) > 30)
    
    def _is_time_gap_significant(self, prev_segment: TranscriptSegment, curr_segment: TranscriptSegment) -> bool:
        """
        時間的な間隔が重要かどうかを判定
        
        Args:
            prev_segment: 前のセグメント
            curr_segment: 現在のセグメント
            
        Returns:
            bool: 重要な時間間隔かどうか
        """
        # 5秒以上の間隔がある場合
        time_gap = curr_segment.start_time - prev_segment.end_time
        return time_gap > 5.0
    
    def _split_by_character_limit(self, segment_groups: List[List[TranscriptSegment]]) -> List[SplitContent]:
        """
        文字数制限に基づいて分割
        
        Args:
            segment_groups: セグメントグループ
            
        Returns:
            List[SplitContent]: 分割されたコンテンツ
        """
        split_contents = []
        slide_id = 1
        
        for group in segment_groups:
            # グループ全体のテキスト長を確認
            total_text = " ".join(seg.text for seg in group)
            
            if len(total_text) <= self.max_chars_per_slide:
                # そのまま1スライドとして使用
                content = self._create_split_content(group, slide_id)
                split_contents.append(content)
                slide_id += 1
            else:
                # さらに細分化が必要
                sub_contents = self._split_group_further(group, slide_id)
                split_contents.extend(sub_contents)
                slide_id += len(sub_contents)
        
        return split_contents
    
    def _split_group_further(self, group: List[TranscriptSegment], start_slide_id: int) -> List[SplitContent]:
        """
        グループをさらに細分化
        
        Args:
            group: セグメントグループ
            start_slide_id: 開始スライドID
            
        Returns:
            List[SplitContent]: 細分化されたコンテンツ
        """
        sub_contents = []
        current_segments = []
        current_length = 0
        slide_id = start_slide_id
        
        for segment in group:
            segment_length = len(segment.text)
            
            # 現在のセグメントを追加すると制限を超える場合
            if current_length + segment_length > self.max_chars_per_slide and current_segments:
                # 現在のセグメント群でスライド作成
                content = self._create_split_content(current_segments, slide_id)
                sub_contents.append(content)
                slide_id += 1
                
                # 新しいグループを開始
                current_segments = [segment]
                current_length = segment_length
            else:
                current_segments.append(segment)
                current_length += segment_length
        
        # 残りのセグメントでスライド作成
        if current_segments:
            content = self._create_split_content(current_segments, slide_id)
            sub_contents.append(content)
        
        return sub_contents
    
    def _create_split_content(self, segments: List[TranscriptSegment], slide_id: int) -> SplitContent:
        """
        セグメント群からSplitContentを作成
        
        Args:
            segments: セグメント一覧
            slide_id: スライドID
            
        Returns:
            SplitContent: 作成されたコンテンツ
        """
        # テキスト結合
        text = " ".join(seg.text for seg in segments)
        
        # キーポイント収集（重複除去）
        all_key_points = []
        for seg in segments:
            all_key_points.extend(seg.key_points)
        key_points = list(dict.fromkeys(all_key_points))  # 順序を保持して重複除去
        
        # タイトル生成
        title = self._generate_slide_title(segments, key_points)
        
        # 時間計算
        duration = segments[-1].end_time - segments[0].start_time
        
        # ソースセグメントID
        source_segments = [seg.id for seg in segments]
        
        # 画像提案生成
        image_suggestions = self._generate_image_suggestions(key_points, text)
        
        return SplitContent(
            slide_id=slide_id,
            title=title,
            text=text,
            key_points=key_points,
            duration=duration,
            source_segments=source_segments,
            image_suggestions=image_suggestions
        )
    
    def _generate_slide_title(self, segments: List[TranscriptSegment], key_points: List[str]) -> str:
        """
        スライドタイトルを生成
        
        Args:
            segments: セグメント一覧
            key_points: キーポイント
            
        Returns:
            str: 生成されたタイトル
        """
        if key_points:
            # 最も重要なキーポイントをタイトルに
            return key_points[0]
        
        # キーポイントがない場合、最初のセグメントから抽出
        first_text = segments[0].text
        
        # 最初の文または50文字でタイトル生成
        sentences = re.split(r'[。！？]', first_text)
        if sentences and len(sentences[0]) <= 50:
            return sentences[0].strip()
        
        return first_text[:30] + "..." if len(first_text) > 30 else first_text
    
    def _generate_image_suggestions(self, key_points: List[str], text: str) -> List[str]:
        """
        画像提案を生成
        
        Args:
            key_points: キーポイント
            text: テキスト
            
        Returns:
            List[str]: 画像提案一覧
        """
        suggestions = []
        
        # キーポイントベースの画像提案
        for point in key_points[:2]:  # 上位2つのキーポイント
            suggestions.append(f"{point}の図解")
            suggestions.append(f"{point}のイメージ画像")
        
        # テキストから具体的な概念を抽出
        concrete_terms = self._extract_concrete_terms(text)
        for term in concrete_terms[:2]:
            suggestions.append(f"{term}の写真")
        
        return suggestions[:4]  # 最大4つの提案
    
    def _extract_concrete_terms(self, text: str) -> List[str]:
        """
        テキストから具体的な用語を抽出
        
        Args:
            text: 対象テキスト
            
        Returns:
            List[str]: 抽出された用語
        """
        # 技術用語、固有名詞などを抽出
        patterns = [
            r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',  # 英語の固有名詞
            r'[ァ-ヴー]+',  # カタカナ語
            r'[一-龯]{2,}(?:技術|システム|プラットフォーム|ツール|サービス)',  # 技術関連用語
        ]
        
        terms = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            terms.extend(matches)
        
        # 重複除去と長さフィルタ
        unique_terms = list(set(term for term in terms if 2 <= len(term) <= 20))
        return unique_terms
    
    def _reduce_to_max_slides(self, split_contents: List[SplitContent], max_slides: int) -> List[SplitContent]:
        """
        スライド数を最大数に削減
        
        Args:
            split_contents: 分割コンテンツ一覧
            max_slides: 最大スライド数
            
        Returns:
            List[SplitContent]: 削減されたコンテンツ一覧
        """
        if len(split_contents) <= max_slides:
            return split_contents
        
        logger.info(f"スライド数削減: {len(split_contents)} → {max_slides}")
        
        # 重要度に基づいてスライドを選択
        scored_contents = []
        for content in split_contents:
            score = self._calculate_content_importance(content)
            scored_contents.append((score, content))
        
        # スコア順にソート
        scored_contents.sort(key=lambda x: x[0], reverse=True)
        
        # 上位max_slides個を選択
        selected_contents = [content for _, content in scored_contents[:max_slides]]
        
        # スライドIDを再振り
        for i, content in enumerate(selected_contents, 1):
            content.slide_id = i
        
        return selected_contents
    
    def _calculate_content_importance(self, content: SplitContent) -> float:
        """
        コンテンツの重要度を計算
        
        Args:
            content: 分割コンテンツ
            
        Returns:
            float: 重要度スコア
        """
        score = 0.0
        
        # キーポイント数による重み
        score += len(content.key_points) * 0.3
        
        # テキスト長による重み（適度な長さを好む）
        text_length = len(content.text)
        if 50 <= text_length <= 150:
            score += 0.4
        elif text_length > 150:
            score += 0.2
        
        # 時間長による重み
        if 10 <= content.duration <= 30:
            score += 0.3
        
        return score
    
    def _convert_to_slide_format(self, split_contents: List[SplitContent]) -> List[Dict[str, Any]]:
        """
        SplitContentを辞書形式に変換
        
        Args:
            split_contents: 分割コンテンツ一覧
            
        Returns:
            List[Dict[str, Any]]: 辞書形式のスライドコンテンツ
        """
        slide_contents = []
        
        for content in split_contents:
            slide_dict = {
                "slide_id": content.slide_id,
                "title": content.title,
                "text": content.text,
                "key_points": content.key_points,
                "duration": content.duration,
                "source_segments": content.source_segments,
                "image_suggestions": content.image_suggestions
            }
            slide_contents.append(slide_dict)
        
        return slide_contents
    
    def extract_key_points_only(self, split_contents: List[SplitContent]) -> List[SplitContent]:
        """
        要点のみを抽出してコンテンツを簡略化
        
        Args:
            split_contents: 分割コンテンツ一覧
            
        Returns:
            List[SplitContent]: 簡略化されたコンテンツ一覧
        """
        logger.info("要点抽出による簡略化実行")
        
        simplified_contents = []
        
        for content in split_contents:
            if len(content.key_points) > 0:
                # キーポイントのみでテキストを再構成
                simplified_text = "\n".join(f"• {point}" for point in content.key_points[:3])
                
                simplified_content = SplitContent(
                    slide_id=content.slide_id,
                    title=content.title,
                    text=simplified_text,
                    key_points=content.key_points[:3],
                    duration=min(content.duration, 20.0),  # 時間も短縮
                    source_segments=content.source_segments,
                    image_suggestions=content.image_suggestions
                )
                
                simplified_contents.append(simplified_content)
            else:
                # キーポイントがない場合は元のテキストを短縮
                short_text = content.text[:100] + "..." if len(content.text) > 100 else content.text
                content.text = short_text
                simplified_contents.append(content)
        
        return simplified_contents
