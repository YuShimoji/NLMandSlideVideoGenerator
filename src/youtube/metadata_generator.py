"""
メタデータ生成モジュール
YouTube動画用のタイトル、概要、タグを自動生成
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re
from collections import Counter
from datetime import datetime

from core.utils.logger import logger
from config.settings import settings
from notebook_lm.transcript_processor import TranscriptInfo, TranscriptSegment

@dataclass
class VideoMetadata:
    """動画メタデータ"""
    title: str
    description: str
    tags: List[str]
    category_id: str
    thumbnail_suggestions: Optional[List[str]] = None
    language: Optional[str] = None
    privacy_status: Optional[str] = None

class MetadataGenerator:
    """メタデータ生成クラス"""
    
    def __init__(self, template_dir: Optional[Path] = None):
        self.youtube_settings = settings.YOUTUBE_SETTINGS
        self.max_title_length = self.youtube_settings["max_title_length"]
        self.max_description_length = self.youtube_settings["max_description_length"]
        self.max_tags_length = self.youtube_settings["max_tags_length"]
        
        # テンプレートディレクトリ
        self.template_dir = template_dir or settings.TEMPLATES_DIR / "metadata"
        self.template_dir.mkdir(exist_ok=True)
        
        # テンプレート読み込み
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """テンプレートファイルを読み込み"""
        templates = {}
        
        if self.template_dir.exists():
            for template_file in self.template_dir.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                        template_name = template_file.stem
                        templates[template_name] = template_data
                        logger.info(f"メタデータテンプレート読み込み: {template_name}")
                except Exception as e:
                    logger.warning(f"テンプレート読み込みエラー {template_file}: {e}")
        
        # デフォルトテンプレート
        templates.setdefault('default', {
            'title_template': '{topic} - {key_points}',
            'description_template': 'この動画では{topic}について解説します。\n\n{toc}\n\n{hashtags}',
            'tags_template': ['{topic}', '解説', 'チュートリアル'],
            'category_id': self.youtube_settings['category_id'],
            'language': self.youtube_settings['default_language']
        })
        
        return templates
    
    async def generate_metadata(self, transcript: TranscriptInfo, template_name: str = "default") -> Dict[str, Any]:
        """
        台本からYouTube用メタデータを生成
        
        Args:
            transcript: 台本情報
            template_name: 使用するテンプレート名
            
        Returns:
            Dict[str, Any]: 生成されたメタデータ
        """
        logger.info(f"YouTubeメタデータ生成開始 (テンプレート: {template_name})")
        
        # テンプレートの検証
        if template_name not in self.templates:
            logger.warning(f"不明なテンプレート '{template_name}'、default にフォールバック")
            template_name = "default"
        
        template = self.templates[template_name]
        logger.info(f"適用するテンプレート: {template}")
        
        try:
            # Step 1: タイトル生成
            title = self._generate_title_from_template(transcript, template)
            
            # Step 2: 概要欄生成
            description = self._generate_description_from_template(transcript, template)
            
            # Step 3: タグ生成
            tags = self._generate_tags_from_template(transcript, template)
            
            # Step 4: サムネイル提案生成
            thumbnail_suggestions = self._generate_thumbnail_suggestions(transcript)
            
            metadata = {
                "title": title,
                "description": description,
                "tags": tags,
                "category_id": self.youtube_settings["category_id"],
                "thumbnail_suggestions": thumbnail_suggestions
            }
            # 既定の言語とプライバシー設定を付与（後で上書き可能）
            metadata.setdefault("language", self.youtube_settings.get("default_language", "ja"))
            metadata.setdefault("privacy_status", self.youtube_settings.get("privacy_status", "private"))
            
            logger.success("YouTubeメタデータ生成完了")
            return metadata
            
        except Exception as e:
            logger.error(f"メタデータ生成エラー: {str(e)}")
            raise
    
    def _generate_title(self, transcript: TranscriptInfo) -> str:
        """
        動画タイトルを生成
        
        Args:
            transcript: 台本情報
            
        Returns:
            str: 生成されたタイトル
        """
        # 既存のタイトルがある場合はそれをベースに
        base_title = transcript.title
        
        # キーワード抽出
        keywords = self._extract_main_keywords(transcript)
        
        # SEO最適化されたタイトル生成
        if keywords:
            main_keyword = keywords[0]
            
            # パターン別タイトル生成
            title_patterns = [
                f"【解説】{main_keyword}について詳しく説明します",
                f"{main_keyword}の基本から応用まで完全解説",
                f"今さら聞けない{main_keyword}の全て",
                f"{main_keyword}を分かりやすく解説【初心者向け】",
                f"【最新情報】{main_keyword}の動向と今後の展望"
            ]
            
            # 最も適切なパターンを選択
            for pattern in title_patterns:
                if len(pattern) <= self.max_title_length:
                    return pattern
        
        # フォールバック: 元のタイトルを調整
        if len(base_title) <= self.max_title_length:
            return base_title
        else:
            return base_title[:self.max_title_length-3] + "..."
    
    def _generate_description(self, transcript: TranscriptInfo) -> str:
        """
        動画概要欄を生成
        
        Args:
            transcript: 台本情報
            
        Returns:
            str: 生成された概要欄
        """
        description_parts = []
        
        # 1. 動画概要
        summary = self._generate_video_summary(transcript)
        description_parts.append(f"【動画概要】\n{summary}\n")
        
        # 2. タイムスタンプ付き目次
        chapters = self._generate_chapters(transcript)
        if chapters:
            description_parts.append("【目次】")
            description_parts.extend(chapters)
            description_parts.append("")
        
        # 3. 重要ポイント
        key_points = self._extract_key_points_for_description(transcript)
        if key_points:
            description_parts.append("【重要ポイント】")
            description_parts.extend([f"✓ {point}" for point in key_points])
            description_parts.append("")
        
        # 4. 関連情報・ソース
        sources = self._extract_source_information(transcript)
        if sources:
            description_parts.append("【参考情報】")
            description_parts.extend(sources)
            description_parts.append("")
        
        # 5. チャンネル情報・お決まりの文言
        description_parts.extend([
            "【チャンネル情報】",
            "このチャンネルでは、最新の技術動向や解説動画を定期的に配信しています。",
            "チャンネル登録・高評価をお願いします！",
            "",
            "【お問い合わせ】",
            "ご質問やリクエストがありましたら、コメント欄にお書きください。",
            "",
            f"#解説動画 #{self._get_main_hashtag(transcript)}"
        ])
        
        # 文字数制限チェック
        full_description = "\n".join(description_parts)
        if len(full_description) > self.max_description_length:
            # 長すぎる場合は要約版を作成
            return self._create_shortened_description(transcript, summary, chapters[:5])
        
        return full_description
    
    def _generate_video_summary(self, transcript: TranscriptInfo) -> str:
        """
        動画の要約を生成
        
        Args:
            transcript: 台本情報
            
        Returns:
            str: 動画要約
        """
        # 最初と最後のセグメントから要約を作成
        if not transcript.segments:
            return "この動画では重要なトピックについて解説します。"
        
        first_segment = transcript.segments[0]
        
        # 最初のセグメントから主要な内容を抽出
        summary_base = first_segment.text[:200]
        
        # 全体のキーポイントを統合
        all_key_points = []
        for segment in transcript.segments:
            all_key_points.extend(segment.key_points)
        
        # 頻出キーポイントを特定
        point_counts = Counter(all_key_points)
        top_points = [point for point, count in point_counts.most_common(3)]
        
        if top_points:
            summary = f"{summary_base}主に{', '.join(top_points)}について詳しく説明しています。"
        else:
            summary = summary_base
        
        return summary[:300] + "..." if len(summary) > 300 else summary
    
    def _generate_chapters(self, transcript: TranscriptInfo) -> List[str]:
        """
        タイムスタンプ付きチャプターを生成
        
        Args:
            transcript: 台本情報
            
        Returns:
            List[str]: チャプター一覧
        """
        chapters = []
        
        # セグメントをチャプターにグループ化
        chapter_groups = self._group_segments_into_chapters(transcript.segments)
        
        for i, (start_time, title) in enumerate(chapter_groups):
            timestamp = self._seconds_to_timestamp(start_time)
            chapters.append(f"{timestamp} {title}")
        
        return chapters
    
    def _group_segments_into_chapters(self, segments: List[TranscriptSegment]) -> List[tuple]:
        """
        セグメントをチャプターにグループ化
        
        Args:
            segments: セグメント一覧
            
        Returns:
            List[tuple]: (開始時間, チャプタータイトル) のリスト
        """
        if not segments:
            return []
        
        chapters = [(0.0, "イントロダクション")]
        
        # 話者変更やキーポイント変更でチャプター分割
        current_chapter_start = segments[0].start_time
        current_speaker = segments[0].speaker
        current_key_points = set(segments[0].key_points)
        
        for i, segment in enumerate(segments[1:], 1):
            # チャプター分割条件
            should_split = (
                segment.speaker != current_speaker or
                len(set(segment.key_points).intersection(current_key_points)) < 1 or
                segment.start_time - current_chapter_start > 120  # 2分以上
            )
            
            if should_split and i < len(segments) - 1:  # 最後のセグメントは除く
                # チャプタータイトル生成
                title = self._generate_chapter_title(segments[i-3:i+1])
                chapters.append((segment.start_time, title))
                
                current_chapter_start = segment.start_time
                current_speaker = segment.speaker
                current_key_points = set(segment.key_points)
        
        return chapters[:10]  # 最大10チャプター
    
    def _generate_chapter_title(self, segments: List[TranscriptSegment]) -> str:
        """
        チャプタータイトルを生成
        
        Args:
            segments: セグメント一覧
            
        Returns:
            str: チャプタータイトル
        """
        # キーポイントから最頻出のものを選択
        all_points = []
        for seg in segments:
            all_points.extend(seg.key_points)
        
        if all_points:
            point_counts = Counter(all_points)
            most_common = point_counts.most_common(1)[0][0]
            return f"{most_common}について"
        
        # フォールバック: 最初のセグメントから
        if segments:
            first_text = segments[0].text
            return first_text[:20] + "..." if len(first_text) > 20 else first_text
        
        return "詳細解説"
    
    def _extract_key_points_for_description(self, transcript: TranscriptInfo) -> List[str]:
        """
        概要欄用の重要ポイントを抽出
        
        Args:
            transcript: 台本情報
            
        Returns:
            List[str]: 重要ポイント一覧
        """
        all_key_points = []
        for segment in transcript.segments:
            all_key_points.extend(segment.key_points)
        
        # 頻出度でソート
        point_counts = Counter(all_key_points)
        top_points = [point for point, count in point_counts.most_common(5)]
        
        return top_points
    
    def _extract_source_information(self, transcript: TranscriptInfo) -> List[str]:
        """
        ソース情報を抽出
        
        台本テキストからURL、引用、参照情報を抽出
        
        Args:
            transcript: 台本情報
            
        Returns:
            List[str]: ソース情報一覧
        """
        import re
        
        sources = []
        seen_urls = set()
        
        # 全セグメントのテキストを結合
        full_text = " ".join(seg.text for seg in transcript.segments)
        
        # 1. URL抽出
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, full_text)
        for url in urls:
            # URLをクリーンアップ（末尾の句読点除去）
            url = url.rstrip('.,;:!?）」』】')
            if url not in seen_urls:
                seen_urls.add(url)
                sources.append(f"🔗 {url}")
        
        # 2. 引用パターン抽出（「〜によると」「〜の調査」等）
        quote_patterns = [
            r'「([^」]+)」によると',
            r'「([^」]+)」の(調査|報告|発表|研究)',
            r'([A-Za-z0-9]+(?:社|研究所|大学|機関))の',
            r'([\u4e00-\u9fff]+(?:省|庁|委員会))(?:が|の|は)',
        ]
        
        for pattern in quote_patterns:
            matches = re.findall(pattern, full_text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if match and len(match) >= 2 and match not in seen_urls:
                    seen_urls.add(match)
                    sources.append(f"📖 {match}")
        
        # 3. キーポイントから参照情報を抽出
        for segment in transcript.segments:
            for point in segment.key_points:
                # 「〜に基づく」「〜を参照」等のパターン
                if any(kw in point for kw in ["参照", "引用", "出典", "ソース", "データ"]):
                    if point not in seen_urls:
                        seen_urls.add(point)
                        sources.append(f"📊 {point}")
        
        # 4. ソースが見つからない場合のデフォルト
        if not sources:
            sources = [
                "※ 本動画の情報は信頼できるソースに基づいています",
                "※ 最新情報については公式サイトをご確認ください"
            ]
        else:
            # ヘッダー追加
            sources.insert(0, "【参考情報・引用元】")
            sources.append("")
            sources.append("※ 情報は動画作成時点のものです")
        
        return sources[:10]  # 最大10件
    
    def _generate_tags(self, transcript: TranscriptInfo) -> List[str]:
        """
        動画タグを生成
        
        Args:
            transcript: 台本情報
            
        Returns:
            List[str]: タグ一覧
        """
        tags = []
        
        # 1. キーポイントからタグ生成
        all_key_points = []
        for segment in transcript.segments:
            all_key_points.extend(segment.key_points)
        
        point_counts = Counter(all_key_points)
        for point, count in point_counts.most_common(10):
            if len(point) <= 30:  # タグの長さ制限
                tags.append(point)
        
        # 2. 一般的な解説動画タグ
        general_tags = [
            "解説動画",
            "わかりやすい",
            "初心者向け",
            "学習",
            "教育",
            "日本語"
        ]
        tags.extend(general_tags)
        
        # 3. トピック関連タグ
        topic_tags = self._generate_topic_tags(transcript)
        tags.extend(topic_tags)
        
        # 重複除去と文字数制限
        unique_tags = list(dict.fromkeys(tags))  # 順序保持で重複除去
        
        # 文字数制限チェック
        total_length = sum(len(tag) for tag in unique_tags) + len(unique_tags) - 1  # カンマ分
        if total_length > self.max_tags_length:
            # 文字数制限内に収まるよう調整
            adjusted_tags = []
            current_length = 0
            
            for tag in unique_tags:
                if current_length + len(tag) + 1 <= self.max_tags_length:
                    adjusted_tags.append(tag)
                    current_length += len(tag) + 1
                else:
                    break
            
            return adjusted_tags
        
        return unique_tags[:15]  # 最大15タグ
    
    def _generate_topic_tags(self, transcript: TranscriptInfo) -> List[str]:
        """
        トピック関連のタグを生成
        
        Args:
            transcript: 台本情報
            
        Returns:
            List[str]: トピック関連タグ
        """
        topic_tags = []
        
        # テキスト全体から技術用語を抽出
        full_text = " ".join(segment.text for segment in transcript.segments)
        
        # 技術用語パターン
        tech_patterns = [
            r'AI|人工知能|機械学習|深層学習|ディープラーニング',
            r'プログラミング|コーディング|開発',
            r'データ|アルゴリズム|システム',
            r'クラウド|サーバー|ネットワーク',
            r'セキュリティ|暗号化|認証'
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            topic_tags.extend(matches)
        
        # 重複除去
        return list(set(topic_tags))
    
    def _generate_thumbnail_suggestions(self, transcript: TranscriptInfo) -> List[str]:
        """
        サムネイル提案を生成
        
        Args:
            transcript: 台本情報
            
        Returns:
            List[str]: サムネイル提案一覧
        """
        suggestions = []
        
        # 主要キーワードベースの提案
        keywords = self._extract_main_keywords(transcript)
        for keyword in keywords[:3]:
            suggestions.append(f"{keyword}の図解イメージ")
            suggestions.append(f"{keyword}をテーマにしたインフォグラフィック")
        
        # 一般的な解説動画サムネイル提案
        suggestions.extend([
            "疑問符(?)と電球のアイコン",
            "ステップバイステップの図解",
            "ビフォー・アフターの比較画像",
            "重要ポイントを強調したテキスト画像"
        ])
        
        return suggestions
    
    def _extract_main_keywords(self, transcript: TranscriptInfo) -> List[str]:
        """
        主要キーワードを抽出
        
        Args:
            transcript: 台本情報
            
        Returns:
            List[str]: 主要キーワード一覧
        """
        all_key_points = []
        for segment in transcript.segments:
            all_key_points.extend(segment.key_points)
        
        point_counts = Counter(all_key_points)
        return [point for point, count in point_counts.most_common(5)]
    
    def _get_main_hashtag(self, transcript: TranscriptInfo) -> str:
        """
        メインハッシュタグを取得
        
        Args:
            transcript: 台本情報
            
        Returns:
            str: メインハッシュタグ
        """
        keywords = self._extract_main_keywords(transcript)
        if keywords:
            return keywords[0].replace(' ', '')
        return "解説"
    
    def _seconds_to_timestamp(self, seconds: float) -> str:
        """
        秒をタイムスタンプに変換
        
        Args:
            seconds: 秒数
            
        Returns:
            str: タイムスタンプ (MM:SS)
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _create_shortened_description(
        self, 
        transcript: TranscriptInfo, 
        summary: str, 
        chapters: List[str]
    ) -> str:
        """
        短縮版概要欄を作成
        
        Args:
            transcript: 台本情報
            summary: 要約
            chapters: チャプター一覧
            
        Returns:
            str: 短縮版概要欄
        """
        parts = [
            f"【動画概要】\n{summary}\n",
            "【目次】"
        ]
        parts.extend(chapters)
        parts.extend([
            "",
            "チャンネル登録・高評価をお願いします！",
            f"#{self._get_main_hashtag(transcript)} #解説動画"
        ])
        
        return "\n".join(parts)
    
    def optimize_for_seo(self, metadata: Dict[str, Any], target_keywords: List[str]) -> Dict[str, Any]:
        """
        SEO最適化
        
        Args:
            metadata: 元のメタデータ
            target_keywords: ターゲットキーワード
            
        Returns:
            Dict[str, Any]: SEO最適化済みメタデータ
        """
        optimized = metadata.copy()
        
        # タイトルにキーワードを含める
        if target_keywords and target_keywords[0] not in optimized["title"]:
            new_title = f"{target_keywords[0]} - {optimized['title']}"
            if len(new_title) <= self.max_title_length:
                optimized["title"] = new_title
        
        # 概要欄の最初にキーワードを配置
        if target_keywords:
            keyword_line = f"キーワード: {', '.join(target_keywords[:3])}\n\n"
            optimized["description"] = keyword_line + optimized["description"]
        
        return optimized

    def _generate_title_from_template(self, transcript: TranscriptInfo, template: Dict[str, Any]) -> str:
        """
        テンプレートからタイトルを生成
        
        Args:
            transcript: 台本情報
            template: テンプレートデータ
            
        Returns:
            str: 生成されたタイトル
        """
        title_template = template.get('title_template', '{topic} - {key_points}')
        
        # プレースホルダーを解決
        replacements = {
            '{topic}': transcript.title or 'トピックなし',
            '{key_points}': self._get_key_points_string(transcript),
            '{duration}': self._format_duration(transcript),
        }
        
        title = title_template
        for placeholder, value in replacements.items():
            title = title.replace(placeholder, value)
        
        # 長さ制限
        if len(title) > self.max_title_length:
            title = title[:self.max_title_length-3] + "..."
        
        return title

    def _generate_description_from_template(self, transcript: TranscriptInfo, template: Dict[str, Any]) -> str:
        """
        テンプレートから概要欄を生成
        
        Args:
            transcript: 台本情報
            template: テンプレートデータ
            
        Returns:
            str: 生成された概要欄
        """
        desc_template = template.get('description_template', 'この動画では{topic}について解説します。\n\n{toc}\n\n{hashtags}')
        
        # プレースホルダーを解決
        replacements = {
            '{topic}': transcript.title or 'トピックなし',
            '{toc}': self._generate_toc_string(transcript),
            '{hashtags}': self._generate_hashtags_string(transcript),
            '{summary}': self._generate_video_summary(transcript),
        }
        
        description = desc_template
        for placeholder, value in replacements.items():
            description = description.replace(placeholder, value)
        
        # 長さ制限
        if len(description) > self.max_description_length:
            description = description[:self.max_description_length-3] + "..."
        
        return description

    def _generate_tags_from_template(self, transcript: TranscriptInfo, template: Dict[str, Any]) -> List[str]:
        """
        テンプレートからタグを生成
        
        Args:
            transcript: 台本情報
            template: テンプレートデータ
            
        Returns:
            List[str]: 生成されたタグ
        """
        tags_template = template.get('tags_template', ['{topic}', '解説', 'チュートリアル'])
        
        tags = []
        for tag_template in tags_template:
            # プレースホルダーを解決
            tag = tag_template.replace('{topic}', transcript.title or 'トピックなし')
            tags.append(tag)
        
        # 文字数制限
        total_length = sum(len(tag) for tag in tags) + len(tags) - 1
        if total_length > self.max_tags_length:
            # 短くする
            tags = tags[:10]  # 最大10タグ
        
        return tags

    def _get_key_points_string(self, transcript: TranscriptInfo) -> str:
        """キーポイントを文字列化"""
        keywords = self._extract_main_keywords(transcript)
        return ', '.join(keywords[:3])

    def _format_duration(self, transcript: TranscriptInfo) -> str:
        """動画時間をフォーマット"""
        if transcript.segments:
            total_time = max(seg.end_time for seg in transcript.segments)
            minutes = int(total_time // 60)
            return f"{minutes}分"
        return "不明"

    def _generate_toc_string(self, transcript: TranscriptInfo) -> str:
        """目次を文字列化"""
        chapters = self._generate_chapters(transcript)
        return '\n'.join(chapters[:5])  # 最大5チャプター

    def _generate_hashtags_string(self, transcript: TranscriptInfo) -> str:
        """ハッシュタグを文字列化"""
        hashtags = [f"#{tag.replace(' ', '')}" for tag in self._extract_main_keywords(transcript)[:3]]
        return ' '.join(hashtags)

    def create_template_from_metadata(self, metadata: Dict[str, Any], template_name: str) -> None:
        """
        既存メタデータからテンプレートを作成
        
        Args:
            metadata: メタデータ
            template_name: テンプレート名
        """
        template = {
            'title_template': metadata.get('title', '{topic} - {key_points}'),
            'description_template': metadata.get('description', 'この動画では{topic}について解説します。\n\n{toc}\n\n{hashtags}'),
            'tags_template': metadata.get('tags', ['{topic}', '解説']),
            'category_id': metadata.get('category_id', self.youtube_settings['category_id']),
            'language': metadata.get('language', self.youtube_settings['default_language'])
        }
        
        # テンプレートを保存
        template_path = self.template_dir / f"{template_name}.json"
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        
        # キャッシュ更新
        self.templates[template_name] = template
        logger.info(f"テンプレート '{template_name}' を作成しました")

    def edit_template(self, template_name: str, updates: Dict[str, Any]) -> None:
        """
        テンプレートを編集
        
        Args:
            template_name: テンプレート名
            updates: 更新内容
        """
        if template_name not in self.templates:
            raise ValueError(f"テンプレート '{template_name}' が見つかりません")
        
        # 更新適用
        self.templates[template_name].update(updates)
        
        # 保存
        template_path = self.template_dir / f"{template_name}.json"
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(self.templates[template_name], f, ensure_ascii=False, indent=2)
        
        logger.info(f"テンプレート '{template_name}' を更新しました")

    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        利用可能なテンプレート一覧を取得
        
        Returns:
            Dict[str, Dict[str, Any]]: テンプレート一覧
        """
        return self.templates.copy()
