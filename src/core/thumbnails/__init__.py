"""
サムネイル生成パッケージ

サムネイルはYMM4テンプレートで人間が作成する (DESIGN_FOUNDATIONS準拠)。
PIL による自動生成は廃止済み。
"""

from .ymm4_thumbnail_generator import Ymm4ThumbnailGenerator

__all__ = [
    'Ymm4ThumbnailGenerator',
]
