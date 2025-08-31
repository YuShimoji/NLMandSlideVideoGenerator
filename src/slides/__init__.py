"""
スライド生成関連モジュール
Google Slidesを使用したスライドの自動生成
"""

from .slide_generator import SlideGenerator
from .content_splitter import ContentSplitter

__all__ = [
    "SlideGenerator",
    "ContentSplitter"
]
