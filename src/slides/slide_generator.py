"""
スライド生成モジュール
Google Slidesを使用したスライドの自動生成
"""
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import time
import json

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
from .content_splitter import ContentSplitter

@dataclass
class SlideInfo:
    """スライド情報"""
    slide_id: int
    title: str
    content: str
    layout: str
    duration: float
    image_suggestions: List[str] = None

@dataclass
class SlidesPackage:
    """スライドパッケージ情報"""
    file_path: Path
    slides: List[SlideInfo]
    total_slides: int
    theme: str
    created_at: str = None

class SlideGenerator:
    """スライド生成クラス"""
    
    def __init__(self):
        self.max_chars_per_slide = settings.SLIDES_SETTINGS["max_chars_per_slide"]
        self.max_slides_per_batch = settings.SLIDES_SETTINGS["max_slides_per_batch"]
        self.theme = settings.SLIDES_SETTINGS["theme"]
        self.output_dir = settings.SLIDES_DIR
        self.content_splitter = ContentSplitter()
        
    async def generate_slides(
        self,
        transcript: TranscriptInfo,
        max_slides: int = 20
    ) -> SlidesPackage:
        """
        台本からスライドを生成
        
        Args:
            transcript_info: 台本情報
            max_slides: 最大スライド数
            
        Returns:
            SlidesPackage: 生成されたスライドパッケージ
        """
        logger.info(f"スライド生成開始: {transcript.title}")
        
        try:
            # Step 1: 台本をスライド用に分割
            slide_contents = await self.content_splitter.split_for_slides(
                transcript, max_slides
            )
            
            # Step 2: Google Slidesでスライド生成
            slides_package = await self._generate_slides_with_google(
                slide_contents, transcript.title
            )
            
            # Step 3: スライドファイルのダウンロード
            await self._download_slides_file(slides_package)
            
            # Step 4: スライド情報の保存
            await self._save_slides_metadata(slides_package)
            
            logger.success(f"スライド生成完了: {slides_package.total_slides}枚")
            return slides_package
            
        except Exception as e:
            logger.error(f"スライド生成エラー: {str(e)}")
            raise
    
    async def _generate_slides_with_google(
        self, 
        slide_contents: List[Dict[str, Any]], 
        presentation_title: str
    ) -> SlidesPackage:
        """
        Google Slidesでスライドを生成
        
        Args:
            slide_contents: スライド内容一覧
            presentation_title: プレゼンテーションタイトル
            
        Returns:
            SlidesPackage: 生成されたスライドパッケージ
        """
        logger.info("Google Slidesでスライド生成中...")
        
        # Step 1: Google Slidesセッション開始
        session_id = await self._start_google_slides_session()
        
        # Step 2: 新しいプレゼンテーション作成
        presentation_id = await self._create_new_presentation(session_id, presentation_title)
        
        # Step 3: バッチ処理でスライド生成
        slides = []
        batch_size = min(self.max_slides_per_batch, len(slide_contents))
        
        for i in range(0, len(slide_contents), batch_size):
            batch = slide_contents[i:i + batch_size]
            batch_slides = await self._generate_slides_batch(session_id, batch, i + 1)
            slides.extend(batch_slides)
            
            # レート制限対応
            if i + batch_size < len(slide_contents):
                await asyncio.sleep(2)
        
        # スライドパッケージ作成
        slides_package = SlidesPackage(
            file_path=self.output_dir / f"{presentation_id}.pptx",
            slides=slides,
            total_slides=len(slides),
            theme=self.theme,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        logger.info(f"Google Slidesでの生成完了: {len(slides)}枚")
        return slides_package
    
    async def _start_google_slides_session(self) -> str:
        """
        Google Slidesセッションを開始
        
        Returns:
            str: セッションID
        """
        logger.debug("Google Slidesセッション開始中...")
        
        # TODO: 実際のGoogle Slides自動化実装
        # Seleniumを使用したWebブラウザ自動化
        # または Google Slides API の使用
        
        session_id = f"slides_session_{int(time.time())}"
        logger.debug(f"セッション開始完了: {session_id}")
        
        return session_id
    
    async def _create_new_presentation(self, session_id: str, title: str) -> str:
        """
        新しいプレゼンテーションを作成
        
        Args:
            session_id: セッションID
            title: プレゼンテーションタイトル
            
        Returns:
            str: プレゼンテーションID
        """
        logger.debug(f"新しいプレゼンテーション作成: {title}")
        
        # TODO: 実際のプレゼンテーション作成実装
        
        presentation_id = f"presentation_{int(time.time())}"
        logger.debug(f"プレゼンテーション作成完了: {presentation_id}")
        
        return presentation_id
    
    async def _generate_slides_batch(
        self, 
        session_id: str, 
        batch_contents: List[Dict[str, Any]], 
        start_index: int
    ) -> List[SlideInfo]:
        """
        スライドをバッチ生成
        
        Args:
            session_id: セッションID
            batch_contents: バッチ内容
            start_index: 開始インデックス
            
        Returns:
            List[SlideInfo]: 生成されたスライド情報
        """
        logger.debug(f"バッチ生成開始: {len(batch_contents)}枚 (開始: {start_index})")
        
        slides = []
        
        for i, content in enumerate(batch_contents):
            slide_id = start_index + i
            
            # スライド作成サポートにプロンプト送信
            slide_info = await self._create_single_slide(
                session_id, content, slide_id
            )
            
            slides.append(slide_info)
            
            # 個別スライド間の待機
            await asyncio.sleep(1)
        
        logger.debug(f"バッチ生成完了: {len(slides)}枚")
        return slides
    
    async def _create_single_slide(
        self, 
        session_id: str, 
        content: Dict[str, Any], 
        slide_id: int
    ) -> SlideInfo:
        """
        単一スライドを作成
        
        Args:
            session_id: セッションID
            content: スライド内容
            slide_id: スライドID
            
        Returns:
            SlideInfo: 作成されたスライド情報
        """
        logger.debug(f"スライド作成中: {slide_id}")
        
        # スライド作成サポートへのプロンプト構築
        prompt = self._build_slide_prompt(content)
        
        # TODO: 実際のスライド作成実装
        # Google Slidesの「スライド作成サポート」機能を使用
        
        # プレースホルダー実装
        slide_info = SlideInfo(
            slide_id=slide_id,
            title=content.get("title", f"スライド {slide_id}"),
            content=content.get("text", ""),
            image_suggestions=content.get("image_suggestions", []),
            layout_type="title_and_content",
            estimated_duration=content.get("duration", 15.0)
        )
        
        logger.debug(f"スライド作成完了: {slide_id}")
        return slide_info
    
    def _build_slide_prompt(self, content: Dict[str, Any]) -> str:
        """
        スライド作成用プロンプトを構築
        
        Args:
            content: スライド内容
            
        Returns:
            str: 構築されたプロンプト
        """
        title = content.get("title", "")
        text = content.get("text", "")
        key_points = content.get("key_points", [])
        
        prompt = f"""以下の内容でスライドを作成してください：

タイトル: {title}

内容:
{text}

重要なポイント:
{chr(10).join(f"• {point}" for point in key_points)}

スライドは視覚的に分かりやすく、フォントサイズは24pt以上で作成してください。
関連する画像があれば追加してください。"""
        
        return prompt
    
    async def _download_slides_file(self, slides_package: SlidesPackage):
        """
        スライドファイルをダウンロード
        
        Args:
            slides_package: スライドパッケージ
        """
        logger.info("スライドファイルダウンロード中...")
        
        # ディレクトリ作成
        slides_package.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # TODO: 実際のダウンロード実装
        # Google SlidesからPowerPoint形式でダウンロード
        
        # プレースホルダー: 空のファイル作成
        with open(slides_package.file_path, 'wb') as f:
            f.write(b'')  # 実際にはPowerPointファイルの内容
        
        logger.info(f"スライドダウンロード完了: {slides_package.file_path}")
    
    async def _save_slides_metadata(self, slides_package: SlidesPackage):
        """
        スライドメタデータを保存
        
        Args:
            slides_package: スライドパッケージ
        """
        metadata_path = self.output_dir / f"{slides_package.presentation_id}_metadata.json"
        
        metadata = {
            "presentation_id": slides_package.presentation_id,
            "title": slides_package.title,
            "total_slides": slides_package.total_slides,
            "created_at": slides_package.created_at,
            "file_path": str(slides_package.file_path),
            "slides": [
                {
                    "slide_id": slide.slide_id,
                    "title": slide.title,
                    "content": slide.content,
                    "image_suggestions": slide.image_suggestions,
                    "layout_type": slide.layout_type,
                    "estimated_duration": slide.estimated_duration
                }
                for slide in slides_package.slides
            ]
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"スライドメタデータ保存完了: {metadata_path}")
    
    async def handle_generation_failure(
        self, 
        failed_content: Dict[str, Any], 
        session_id: str
    ) -> Optional[SlideInfo]:
        """
        スライド生成失敗時の処理
        
        Args:
            failed_content: 失敗したコンテンツ
            session_id: セッションID
            
        Returns:
            Optional[SlideInfo]: 再生成されたスライド情報
        """
        logger.warning("スライド生成失敗、再試行中...")
        
        # 文字数制限による失敗の場合、要点抽出を実行
        if len(failed_content.get("text", "")) > self.max_chars_per_slide:
            logger.info("文字数制限により要点抽出実行")
            
            # 要点のみでスライド再生成
            key_points = failed_content.get("key_points", [])
            simplified_content = {
                "title": failed_content.get("title", ""),
                "text": "\n".join(f"• {point}" for point in key_points[:3]),
                "key_points": key_points[:3],
                "duration": failed_content.get("duration", 15.0)
            }
            
            return await self._create_single_slide(
                session_id, simplified_content, failed_content.get("slide_id", 1)
            )
        
        return None
    
    def optimize_slides_for_video(self, slides_package: SlidesPackage) -> SlidesPackage:
        """
        動画用にスライドを最適化
        
        Args:
            slides_package: スライドパッケージ
            
        Returns:
            SlidesPackage: 最適化されたスライドパッケージ
        """
        logger.info("動画用スライド最適化中...")
        
        # 各スライドの表示時間を調整
        for slide in slides_package.slides:
            # テキスト量に基づく表示時間計算
            text_length = len(slide.content)
            base_duration = 10.0  # 基本10秒
            additional_duration = text_length / 100 * 2  # 100文字あたり2秒追加
            
            slide.estimated_duration = min(base_duration + additional_duration, 30.0)
        
        logger.info("スライド最適化完了")
        return slides_package
