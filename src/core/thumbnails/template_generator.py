#!/usr/bin/env python3
"""
テンプレートベースサムネイル生成モジュール
定義済みテンプレートを使用してサムネイルを生成
"""

import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap

from ...core.interfaces import IThumbnailGenerator
from ...video_editor.video_composer import ThumbnailInfo, VideoInfo
from ...slides.slide_generator import SlidesPackage
from ...config.settings import settings


class TemplateThumbnailGenerator(IThumbnailGenerator):
    """テンプレートベースのサムネイル生成"""

    def __init__(self):
        self.output_dir = settings.THUMBNAILS_DIR
        self.output_dir.mkdir(exist_ok=True)

        # テンプレート設定
        self.templates = {
            'modern': self._modern_template,
            'classic': self._classic_template,
            'gaming': self._gaming_template,
            'educational': self._educational_template
        }

    async def generate(
        self,
        video: VideoInfo,
        script: Dict[str, Any],
        slides: SlidesPackage,
        style: str = "modern"
    ) -> ThumbnailInfo:
        """
        テンプレートを使用してサムネイルを生成

        Args:
            video: 動画情報
            script: スクリプトデータ
            slides: スライドパッケージ
            style: サムネイルスタイル

        Returns:
            ThumbnailInfo: 生成されたサムネイル情報
        """

        # スタイルがサポートされていない場合はデフォルトを使用
        if style not in self.templates:
            style = 'modern'

        # スクリプトからコンテンツを抽出
        title_text, subtitle_text = await self._extract_content_info(script, slides)

        # テンプレートを使用して画像を生成
        template_func = self.templates[style]
        thumbnail_path = await template_func(title_text, subtitle_text, video)

        # ThumbnailInfoを作成
        thumbnail_info = ThumbnailInfo(
            file_path=thumbnail_path,
            title_text=title_text,
            subtitle_text=subtitle_text,
            style=style,
            resolution=(1280, 720),
            file_size=thumbnail_path.stat().st_size,
            has_overlay=True,
            has_text_effects=True,  # テンプレートは効果付き
            created_at=datetime.now()
        )

        return thumbnail_info

    async def _extract_content_info(
        self,
        script: Dict[str, Any],
        slides: SlidesPackage
    ) -> tuple[str, str]:
        """コンテンツ情報抽出（AI生成器と同じロジック）"""
        # AI生成器と同じロジックを使用
        from .ai_generator import AIThumbnailGenerator
        ai_gen = AIThumbnailGenerator()
        return await ai_gen._extract_content_info(script, slides)

    async def _modern_template(
        self,
        title: str,
        subtitle: str,
        video: VideoInfo
    ) -> Path:
        """モダンテンプレート"""
        width, height = 1280, 720

        # グラデーション背景
        image = Image.new('RGB', (width, height), (26, 26, 46))
        image = self._apply_gradient(image, [(26, 26, 46), (0, 255, 157)])

        draw = ImageDraw.Draw(image)

        # タイトル（大きなフォント、中央）
        try:
            title_font = ImageFont.truetype("arial.ttf", 72)
        except:
            title_font = ImageFont.load_default()

        self._draw_centered_text(draw, title, title_font, (255, 255, 255), height // 3)

        # サブタイトル
        try:
            subtitle_font = ImageFont.truetype("arial.ttf", 36)
        except:
            subtitle_font = ImageFont.load_default()

        self._draw_centered_text(draw, subtitle, subtitle_font, (0, 255, 157), height // 3 + 120)

        # 装飾要素
        self._add_modern_decorations(draw, width, height)

        return await self._save_thumbnail(image, "modern")

    async def _classic_template(
        self,
        title: str,
        subtitle: str,
        video: VideoInfo
    ) -> Path:
        """クラシックテンプレート"""
        width, height = 1280, 720

        # 白背景
        image = Image.new('RGB', (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(image)

        # 境界線
        draw.rectangle([20, 20, width-20, height-20], outline=(0, 0, 0), width=4)

        # タイトル
        try:
            title_font = ImageFont.truetype("arial.ttf", 64)
        except:
            title_font = ImageFont.load_default()

        self._draw_centered_text(draw, title, title_font, (0, 0, 0), height // 3)

        # サブタイトル
        try:
            subtitle_font = ImageFont.truetype("arial.ttf", 32)
        except:
            subtitle_font = ImageFont.load_default()

        self._draw_centered_text(draw, subtitle, subtitle_font, (255, 69, 0), height // 3 + 100)

        # クラシックな装飾
        self._add_classic_decorations(draw, width, height)

        return await self._save_thumbnail(image, "classic")

    async def _gaming_template(
        self,
        title: str,
        subtitle: str,
        video: VideoInfo
    ) -> Path:
        """ゲーミングテンプレート"""
        width, height = 1280, 720

        # ダーク背景
        image = Image.new('RGB', (width, height), (139, 0, 0))
        draw = ImageDraw.Draw(image)

        # タイトル（ネオン効果）
        try:
            title_font = ImageFont.truetype("arial.ttf", 68)
        except:
            title_font = ImageFont.load_default()

        self._draw_glowing_text(draw, title, title_font, height // 3)

        # サブタイトル
        try:
            subtitle_font = ImageFont.truetype("arial.ttf", 34)
        except:
            subtitle_font = ImageFont.load_default()

        self._draw_centered_text(draw, subtitle, subtitle_font, (255, 20, 147), height // 3 + 120)

        # ゲーミング装飾
        self._add_gaming_decorations(draw, width, height)

        return await self._save_thumbnail(image, "gaming")

    async def _educational_template(
        self,
        title: str,
        subtitle: str,
        video: VideoInfo
    ) -> Path:
        """教育テンプレート"""
        width, height = 1280, 720

        # 青背景
        image = Image.new('RGB', (width, height), (25, 25, 112))
        draw = ImageDraw.Draw(image)

        # タイトル
        try:
            title_font = ImageFont.truetype("arial.ttf", 60)
        except:
            title_font = ImageFont.load_default()

        self._draw_centered_text(draw, title, title_font, (255, 255, 255), height // 3)

        # サブタイトル
        try:
            subtitle_font = ImageFont.truetype("arial.ttf", 30)
        except:
            subtitle_font = ImageFont.load_default()

        self._draw_centered_text(draw, subtitle, subtitle_font, (50, 205, 50), height // 3 + 100)

        # 教育向け装飾
        self._add_educational_decorations(draw, width, height)

        return await self._save_thumbnail(image, "educational")

    def _apply_gradient(self, image: Image.Image, colors: list) -> Image.Image:
        """グラデーション適用"""
        width, height = image.size
        gradient = Image.new('RGB', (width, height))

        for y in range(height):
            ratio = y / height
            if len(colors) == 2:
                r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * ratio)
                g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * ratio)
                b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * ratio)
            else:
                r, g, b = colors[0]

            for x in range(width):
                gradient.putpixel((x, y), (r, g, b))

        return gradient

    def _draw_centered_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        color: tuple,
        y: int
    ):
        """中央揃えテキスト描画"""
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        x = (1280 - width) // 2  # 固定幅

        # 影効果
        draw.text((x + 2, y + 2), text, fill=(0, 0, 0, 128), font=font)
        draw.text((x, y), text, fill=color, font=font)

    def _draw_glowing_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        y: int
    ):
        """光るテキスト効果"""
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        x = (1280 - width) // 2

        # 多重影で光る効果
        glow_colors = [(255, 255, 0), (255, 255, 100), (255, 255, 150)]
        for i, glow_color in enumerate(glow_colors):
            offset = i + 1
            draw.text((x - offset, y - offset), text, fill=glow_color, font=font)
            draw.text((x + offset, y - offset), text, fill=glow_color, font=font)
            draw.text((x - offset, y + offset), text, fill=glow_color, font=font)
            draw.text((x + offset, y + offset), text, fill=glow_color, font=font)

        # 本体テキスト
        draw.text((x, y), text, fill=(255, 255, 0), font=font)

    def _add_modern_decorations(self, draw: ImageDraw.ImageDraw, width: int, height: int):
        """モダン装飾追加"""
        # 幾何学模様
        draw.rectangle([50, 50, 150, 150], fill=(0, 255, 157), outline=(255, 255, 255))
        draw.ellipse([width-150, height-150, width-50, height-50], fill=(0, 255, 157))

    def _add_classic_decorations(self, draw: ImageDraw.ImageDraw, width: int, height: int):
        """クラシック装飾追加"""
        # 古典的な枠線
        draw.rectangle([40, 40, width-40, height-40], outline=(0, 0, 0), width=2)

    def _add_gaming_decorations(self, draw: ImageDraw.ImageDraw, width: int, height: int):
        """ゲーミング装飾追加"""
        # ネオン効果の線
        draw.line([0, 100, width, 100], fill=(255, 20, 147), width=4)
        draw.line([0, height-100, width, height-100], fill=(255, 20, 147), width=4)

    def _add_educational_decorations(self, draw: ImageDraw.ImageDraw, width: int, height: int):
        """教育装飾追加"""
        # 学術的な要素
        draw.rectangle([100, 100, 200, 150], fill=(50, 205, 50))
        draw.text((120, 115), "✓", fill=(255, 255, 255))

    async def _save_thumbnail(self, image: Image.Image, style: str) -> Path:
        """サムネイルを保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"thumbnail_template_{timestamp}_{style}.png"
        filepath = self.output_dir / filename

        image.save(filepath, 'PNG')
        return filepath
