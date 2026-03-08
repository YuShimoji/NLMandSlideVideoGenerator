"""
編集バックエンド

利用可能なバックエンド:
- YMM4EditingBackend: ゆっくりMovieMaker4連携
"""

from .ymm4_backend import YMM4EditingBackend

__all__ = [
    "YMM4EditingBackend",
]
