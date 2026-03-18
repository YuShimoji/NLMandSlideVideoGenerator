"""
サムネイル生成パッケージ
動画の内容から自動で魅力的なサムネイルを生成
"""

from .ai_generator import AIThumbnailGenerator
from .template_generator import TemplateThumbnailGenerator

# Script preset (SP-036) → thumbnail style マッピング
# script_presets/ の name フィールドを thumbnail スタイル名に変換する。
# 未知のプリセットは "modern" にフォールバックする。
PRESET_TO_THUMBNAIL_STYLE: dict[str, str] = {
    "default": "modern",
    "news": "classic",
    "educational": "educational",
    "summary": "gaming",
}

_DEFAULT_THUMBNAIL_STYLE = "modern"


def resolve_thumbnail_style(script_preset: str) -> str:
    """Script preset 名からサムネイルスタイル名を解決する。

    Args:
        script_preset: SP-036 で定義されたプリセット名
            (default / news / educational / summary)。

    Returns:
        対応する thumbnail スタイル名 (modern / classic / educational / gaming)。
        未知のプリセットの場合は "modern" を返す。
    """
    return PRESET_TO_THUMBNAIL_STYLE.get(script_preset, _DEFAULT_THUMBNAIL_STYLE)


__all__ = [
    'AIThumbnailGenerator',
    'TemplateThumbnailGenerator',
    'PRESET_TO_THUMBNAIL_STYLE',
    'resolve_thumbnail_style',
]
