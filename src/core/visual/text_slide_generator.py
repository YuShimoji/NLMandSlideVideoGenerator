"""テキストスライド自動生成 (SP-033 Phase 3)

スライドPNGが存在しないセグメントに対して、
セグメント内容（section, key_points, content）からシンプルなテキストスライドPNGを生成する。

PLACEHOLDER_THEMES (config/settings.py) のカラースキームを使用。
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

from core.utils.logger import logger


# デフォルト解像度 (Full HD)
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080

# フォントサイズ
TITLE_FONT_SIZE = 56
BODY_FONT_SIZE = 40
LABEL_FONT_SIZE = 28

# レイアウト定数
PADDING_X = 120
PADDING_TOP = 160
TITLE_Y = PADDING_TOP
BODY_Y_START = PADDING_TOP + 120
LINE_SPACING = 1.5
MAX_BODY_LINES = 12
ACCENT_BAR_HEIGHT = 6
ACCENT_BAR_Y = PADDING_TOP - 40

# 日本語フォント候補 (Windows → Linux → macOS)
_JP_FONT_CANDIDATES = [
    "C:/Windows/Fonts/meiryo.ttc",       # Windows: メイリオ
    "C:/Windows/Fonts/msgothic.ttc",      # Windows: MS ゴシック
    "C:/Windows/Fonts/YuGothM.ttc",       # Windows: 游ゴシック
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",       # Linux alt
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",           # macOS
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",     # macOS
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """日本語対応フォントをロードする。見つからない場合はデフォルトにフォールバック。"""
    for path in _JP_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, TypeError, ValueError):
            continue
    # 英語フォントフォールバック
    try:
        return ImageFont.truetype("arial.ttf", size)
    except (OSError, TypeError, ValueError):
        return ImageFont.load_default()


class TextSlideGenerator:
    """セグメント内容からテキストスライドPNGを生成する。

    生成されたスライドは work_dir/generated_slides/ に保存され、
    同一内容のセグメントにはキャッシュを返す（ハッシュベース）。
    """

    def __init__(
        self,
        output_dir: Path,
        theme: Optional[Dict[str, Any]] = None,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
    ) -> None:
        """
        Args:
            output_dir: 生成スライドの保存先ディレクトリ。
            theme: PLACEHOLDER_THEMES のカラースキーム辞書。
                None の場合は settings から取得。
            width: スライド幅 (px)。
            height: スライド高さ (px)。
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = width
        self.height = height

        if theme is None:
            theme = self._load_default_theme()
        self.theme = theme

        # フォントキャッシュ
        self._title_font = _load_font(TITLE_FONT_SIZE)
        self._body_font = _load_font(BODY_FONT_SIZE)
        self._label_font = _load_font(LABEL_FONT_SIZE)

    @staticmethod
    def _load_default_theme() -> Dict[str, Any]:
        """settings.py から現在のテーマを読み込む。"""
        try:
            from config.settings import settings
            theme_name = settings.PLACEHOLDER_THEME
            themes = settings.PLACEHOLDER_THEMES
            return themes.get(theme_name, themes.get("dark", {}))  # type: ignore[no-any-return]
        except ImportError:
            # settings不在時のフォールバック
            return {
                "background": (20, 20, 25),
                "title_color": (235, 235, 235),
                "speaker_color": (180, 200, 255),
                "body_color": (200, 200, 200),
                "label_color": (120, 120, 130),
                "accent_color": (100, 150, 255),
            }

    def generate(self, segment: Dict[str, Any], index: int = 0) -> Path:
        """1セグメントからテキストスライドPNGを生成する。

        Args:
            segment: 台本セグメント辞書。
                期待キー: section, content/text, key_points, speaker
            index: セグメントインデックス（ファイル名に使用）。

        Returns:
            生成されたPNGファイルのパス。キャッシュヒット時はそのまま返す。
        """
        # コンテンツ抽出
        section = segment.get("section", "")
        content = segment.get("content", "") or segment.get("text", "")
        key_points = segment.get("key_points", [])
        speaker = segment.get("speaker", "")

        # キャッシュキー生成
        cache_key = self._cache_key(section, content, key_points, speaker)
        cached_path = self.output_dir / f"slide_{index:03d}_{cache_key}.png"
        if cached_path.exists():
            logger.debug(f"テキストスライドキャッシュヒット: {cached_path.name}")
            return cached_path

        # 画像生成
        image = self._render(section, content, key_points, speaker)
        image.save(str(cached_path), "PNG")
        logger.debug(f"テキストスライド生成: {cached_path.name}")
        return cached_path

    def generate_batch(
        self,
        segments: List[Dict[str, Any]],
        indices: Optional[List[int]] = None,
    ) -> List[Path]:
        """複数セグメントのテキストスライドを一括生成する。

        Args:
            segments: セグメント辞書群。
            indices: 各セグメントのインデックス。Noneなら連番。

        Returns:
            生成されたPNGパス群。
        """
        if indices is None:
            indices = list(range(len(segments)))

        paths = []
        for seg, idx in zip(segments, indices):
            paths.append(self.generate(seg, idx))
        return paths

    def _render(
        self,
        section: str,
        content: str,
        key_points: List[str],
        speaker: str,
    ) -> Image.Image:
        """テキストスライド画像を描画する。"""
        bg_color = tuple(self.theme.get("background", (20, 20, 25)))
        image = Image.new("RGB", (self.width, self.height), bg_color)
        draw = ImageDraw.Draw(image)

        # アクセントバー (上部装飾)
        accent_color = tuple(self.theme.get("accent_color", (100, 150, 255)))
        draw.rectangle(
            [PADDING_X, ACCENT_BAR_Y, self.width - PADDING_X, ACCENT_BAR_Y + ACCENT_BAR_HEIGHT],
            fill=accent_color,
        )

        y = TITLE_Y

        # セクションタイトル描画
        if section:
            title_color = tuple(self.theme.get("title_color", (235, 235, 235)))
            wrapped_title = self._wrap_text(section, self._title_font, self.width - PADDING_X * 2)
            for line in wrapped_title[:2]:  # タイトルは最大2行
                draw.text((PADDING_X, y), line, fill=title_color, font=self._title_font)
                y += int(TITLE_FONT_SIZE * LINE_SPACING)
            y += 20  # タイトル後スペース

        # 話者ラベル描画
        if speaker:
            speaker_color = tuple(self.theme.get("speaker_color", (180, 200, 255)))
            draw.text((PADDING_X, y), f"— {speaker}", fill=speaker_color, font=self._label_font)
            y += int(LABEL_FONT_SIZE * LINE_SPACING) + 10

        # key_points をバレットリストとして描画
        body_color = tuple(self.theme.get("body_color", (200, 200, 200)))
        label_color = tuple(self.theme.get("label_color", (120, 120, 130)))
        remaining_lines = MAX_BODY_LINES

        if key_points:
            for kp in key_points:
                if remaining_lines <= 0:
                    break
                bullet = f"•  {kp}"
                wrapped = self._wrap_text(bullet, self._body_font, self.width - PADDING_X * 2 - 20)
                for line in wrapped:
                    if remaining_lines <= 0:
                        break
                    draw.text((PADDING_X + 20, y), line, fill=body_color, font=self._body_font)
                    y += int(BODY_FONT_SIZE * LINE_SPACING)
                    remaining_lines -= 1

        # key_points が無い場合、content をテキストとして描画
        elif content:
            wrapped = self._wrap_text(content, self._body_font, self.width - PADDING_X * 2)
            for line in wrapped:
                if remaining_lines <= 0:
                    break
                draw.text((PADDING_X, y), line, fill=body_color, font=self._body_font)
                y += int(BODY_FONT_SIZE * LINE_SPACING)
                remaining_lines -= 1

        # フッター: セグメント番号等（なくてもよいが視覚的区切り）
        footer_y = self.height - 60
        draw.rectangle(
            [PADDING_X, footer_y, self.width - PADDING_X, footer_y + 1],
            fill=label_color,
        )

        return image

    def _wrap_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> List[str]:
        """テキストを指定幅に収まるよう折り返す。"""
        if not text:
            return []

        # 改行で分割してから各行を処理
        raw_lines = text.replace("\r\n", "\n").split("\n")
        result: List[str] = []

        for raw_line in raw_lines:
            if not raw_line.strip():
                result.append("")
                continue

            # テキスト幅を測定して折り返し
            words_or_chars = self._split_for_wrap(raw_line)
            current_line = ""

            for chunk in words_or_chars:
                test_line = current_line + chunk if current_line else chunk
                bbox = font.getbbox(test_line)
                text_width = bbox[2] - bbox[0] if bbox else 0

                if text_width <= max_width or not current_line:
                    current_line = test_line
                else:
                    result.append(current_line)
                    current_line = chunk

            if current_line:
                result.append(current_line)

        return result

    @staticmethod
    def _split_for_wrap(text: str) -> List[str]:
        """テキストを折り返し用に分割する。

        日本語: 1文字ずつ
        英語: 単語単位（スペースで分割）
        """
        chunks: List[str] = []
        current_ascii = ""

        for ch in text:
            if ord(ch) < 128:
                current_ascii += ch
            else:
                if current_ascii:
                    # ASCII部分をスペースで分割
                    parts = current_ascii.split(" ")
                    for i, part in enumerate(parts):
                        if i > 0:
                            chunks.append(" ")
                        if part:
                            chunks.append(part)
                    current_ascii = ""
                chunks.append(ch)

        if current_ascii:
            parts = current_ascii.split(" ")
            for i, part in enumerate(parts):
                if i > 0:
                    chunks.append(" ")
                if part:
                    chunks.append(part)

        return chunks

    @staticmethod
    def _cache_key(section: str, content: str, key_points: List[str], speaker: str = "") -> str:
        """コンテンツからキャッシュキー（短いハッシュ）を生成する。"""
        raw = f"{section}|{content}|{'|'.join(key_points)}|{speaker}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]
