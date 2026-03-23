"""
スライド生成関連モジュール
Google Slidesを使用したスライドの自動生成

三段フォールバック:
  1. テンプレート複製方式 (SLIDES_TEMPLATE_PRESENTATION_ID 設定時)
  2. プログラマティック方式 (API認証済み、テンプレートID未設定)
  3. python-pptx モック (API未認証時)
"""

from .slide_generator import SlideGenerator
from .content_splitter import ContentSplitter
from .slide_templates import LayoutType, SlideContent, SlideTemplateConfig

__all__ = [
    "SlideGenerator",
    "ContentSplitter",
    "LayoutType",
    "SlideContent",
    "SlideTemplateConfig",
]
