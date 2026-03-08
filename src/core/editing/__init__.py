"""
編集バックエンド

利用可能なバックエンド:
- YMM4EditingBackend: ゆっくりMovieMaker4連携
- ExportFallbackManager: 複数バックエンドのフォールバック管理
"""

from .ymm4_backend import YMM4EditingBackend
from .export_fallback_manager import (
    ExportFallbackManager,
    BackendType,
    BackendConfig,
    FallbackResult,
)

__all__ = [
    "YMM4EditingBackend",
    "ExportFallbackManager",
    "BackendType",
    "BackendConfig",
    "FallbackResult",
]
