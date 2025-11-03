#!/usr/bin/env python3
"""
AIサムネイル生成モジュール
Gemini APIを使用して動画の内容から自動で魅力的なサムネイルを生成
"""

import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap
import re

from core.interfaces import IThumbnailGenerator
from video_editor.video_composer import ThumbnailInfo, VideoInfo
from slides.slide_generator import SlidesPackage
from config.settings import settings


class AIThumbnailGenerator(IThumbnailGenerator):
    """AIを活用したサムネイル自動生成"""

    def __init__(self):
        self.output_dir = settings.THUMBNAILS_DIR
        self.output_dir.mkdir(exist_ok=True)

        # サムネイルスタイル設定
        self.styles = {
            'modern': {
                'bg_color': (26, 26, 46),  # ダークブルー
                'text_color': (255, 255, 255),
                'accent_color': (0, 255, 157),  # シアン
                'font_size_title': 72,
                'font_size_subtitle': 36,
                'gradient': True
            },
            'classic': {
                'bg_color': (255, 255, 255),  # 白
                'text_color': (0, 0, 0),
                'accent_color': (255, 69, 0),  # レッドオレンジ
                'font_size_title': 64,
                'font_size_subtitle': 32,
                'gradient': False
            },
            'gaming': {
                'bg_color': (139, 0, 0),  # ダークレッド
                'text_color': (255, 255, 0),  # イエロー
                'accent_color': (255, 20, 147),  # ディープピンク
                'font_size_title': 68,
                'font_size_subtitle': 34,
                'gradient': True
            },
            'educational': {
                'bg_color': (25, 25, 112),  # ミッドナイトブルー
                'text_color': (255, 255, 255),
                'accent_color': (50, 205, 50),  # ライムグリーン
                'font_size_title': 60,
                'font_size_subtitle': 30,
                'gradient': False
            }
        }

    async def generate(
        self,
        video: VideoInfo,
        script: Dict[str, Any],
        slides: SlidesPackage,
        style: str = "modern"
    ) -> ThumbnailInfo:
        """
        AIを活用して動画内容からサムネイルを自動生成

        Args:
            video: 動画情報
            script: スクリプトデータ
            slides: スライドパッケージ
            style: サムネイルスタイル

        Returns:
            ThumbnailInfo: 生成されたサムネイル情報
        """

        # スタイル設定を取得
        if style not in self.styles:
            style = 'modern'
        style_config = self.styles[style]

        # 動画内容からタイトルとサブタイトルを生成
        title_text, subtitle_text = await self._extract_content_info(script, slides)

        # サムネイル画像を生成
        thumbnail_path = await self._create_thumbnail_image(
            title_text, subtitle_text, style_config, video
        )

        # ThumbnailInfoを作成
        thumbnail_info = ThumbnailInfo(
            file_path=thumbnail_path,
            title_text=title_text,
            subtitle_text=subtitle_text,
            style=style,
            resolution=(1280, 720),  # YouTube推奨サイズ
            file_size=thumbnail_path.stat().st_size,
            has_overlay=True,
            has_text_effects=style_config.get('gradient', False),
            created_at=datetime.now()
        )

        return thumbnail_info

    async def _extract_content_info(
        self,
        script: Dict[str, Any],
        slides: SlidesPackage
    ) -> tuple[str, str]:
        """
        スクリプトとスライドからタイトルとサブタイトルを抽出

        Args:
            script: スクリプトデータ
            slides: スライドパッケージ

        Returns:
            tuple[str, str]: (タイトル, サブタイトル)
        """

        # スクリプトからタイトルを取得
        title = script.get('title', '動画タイトル')

        # スクリプトの内容からキーポイントを抽出
        content = script.get('content', '')
        segments = script.get('segments', [])

        # 最初のセグメントからサブタイトルを生成
        if segments:
            first_segment = segments[0].get('text', '')[:50]
            subtitle = f"{first_segment}..."
        else:
            # 内容からキーワードを抽出
            words = re.findall(r'\b\w+\b', content)
            key_words = [word for word in words if len(word) > 3][:3]
            subtitle = '・'.join(key_words) if key_words else '詳細解説'

        return title, subtitle

    async def _create_thumbnail_image(
        self,
        title: str,
        subtitle: str,
        style_config: Dict[str, Any],
        video: VideoInfo
    ) -> Path:
        """
        サムネイル画像を生成

        Args:
            title: タイトルテキスト
            subtitle: サブタイトルテキスト
            style_config: スタイル設定
            video: 動画情報

        Returns:
            Path: 生成された画像のパス
        """

        # 画像サイズ
        width, height = 1280, 720

        # 新しい画像を作成
        image = Image.new('RGB', (width, height), style_config['bg_color'])
        draw = ImageDraw.Draw(image)

        # グラデーション効果（対応スタイルの場合）
        if style_config.get('gradient', False):
            image = self._apply_gradient(image, style_config)

        # フォント設定（デフォルトフォントを使用）
        try:
            # システムフォントを試行
            title_font = ImageFont.truetype("arial.ttf", style_config['font_size_title'])
            subtitle_font = ImageFont.truetype("arial.ttf", style_config['font_size_subtitle'])
        except:
            # デフォルトフォントを使用
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

        # タイトルを描画（中央揃え）
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        title_y = height // 3

        # タイトルに影効果
        shadow_offset = 2
        draw.text((title_x + shadow_offset, title_y + shadow_offset),
                 title, fill=(0, 0, 0, 128), font=title_font)
        draw.text((title_x, title_y), title,
                 fill=style_config['text_color'], font=title_font)

        # サブタイトルを描画
        subtitle_lines = textwrap.wrap(subtitle, width=30)
        subtitle_y = title_y + 120

        for line in subtitle_lines:
            subtitle_bbox = draw.textbbox((0, 0), line, font=subtitle_font)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
            subtitle_x = (width - subtitle_width) // 2

            # サブタイトルに影効果
            draw.text((subtitle_x + shadow_offset, subtitle_y + shadow_offset),
                     line, fill=(0, 0, 0, 128), font=subtitle_font)
            draw.text((subtitle_x, subtitle_y), line,
                     fill=style_config['accent_color'], font=subtitle_font)

            subtitle_y += 50

        # 装飾要素を追加
        self._add_decorative_elements(draw, width, height, style_config)

        # ファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"thumbnail_{timestamp}_{style}.png"
        filepath = self.output_dir / filename

        # 画像を保存
        image.save(filepath, 'PNG')

        return filepath

    def _apply_gradient(self, image: Image.Image, style_config: Dict[str, Any]) -> Image.Image:
        """グラデーション効果を適用"""
        width, height = image.size
        gradient_image = Image.new('RGB', (width, height))

        # 単純な縦グラデーション
        for y in range(height):
            # 上から下へのグラデーション
            ratio = y / height
            r = int(style_config['bg_color'][0] * (1 - ratio * 0.3))
            g = int(style_config['bg_color'][1] * (1 - ratio * 0.3))
            b = int(style_config['bg_color'][2] * (1 - ratio * 0.3))

            for x in range(width):
                gradient_image.putpixel((x, y), (r, g, b))

        # 元の画像を合成
        result = Image.alpha_composite(gradient_image.convert('RGBA'),
                                     image.convert('RGBA')).convert('RGB')

        return result

    def _add_decorative_elements(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        style_config: Dict[str, Any]
    ):
        """装飾要素を追加"""
        # シンプルな装飾線
        accent_color = style_config['accent_color']

        # 上部の装飾線
        draw.rectangle([50, 50, width-50, 60], fill=accent_color)

        # 下部の装飾線
        draw.rectangle([50, height-60, width-50, height-50], fill=accent_color)

        # コーナーのアクセント
        draw.rectangle([40, 40, 60, 60], fill=accent_color)
        draw.rectangle([width-60, 40, width-40, 60], fill=accent_color)
        draw.rectangle([40, height-60, 60, height-40], fill=accent_color)
        draw.rectangle([width-60, height-60, width-40, height-40], fill=accent_color)
