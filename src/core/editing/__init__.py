"""
編集バックエンド

利用可能なバックエンド:
- MoviePyEditingBackend: MoviePy/FFmpegベース（確実な動作）
- YMM4EditingBackend: ゆっくりMovieMaker4連携（高品質）
- ExportFallbackManager: 複数バックエンドのフォールバック管理
"""

from .moviepy_backend import MoviePyEditingBackend
from .ymm4_backend import YMM4EditingBackend
from .export_fallback_manager import (
    ExportFallbackManager,
    BackendType,
    BackendConfig,
    FallbackResult,
)

__all__ = [
    "MoviePyEditingBackend",
    "YMM4EditingBackend",
    "ExportFallbackManager",
    "BackendType",
    "BackendConfig",
    "FallbackResult",
]
