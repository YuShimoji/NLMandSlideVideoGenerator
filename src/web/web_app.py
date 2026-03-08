"""
Web GUI for NLMandSlideVideoGenerator
Streamlit-based dashboard for pipeline management and documentation
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))
sys.path.insert(0, str(PROJECT_ROOT))

from src.web.ui.pages import (  # noqa: E402
    show_home_page,
    show_pipeline_page,
    show_assets_page,
    show_documentation_page,
    show_settings_page,
    show_tests_page,
)

st.set_page_config(
    page_title="NLMandSlide Video Generator",
    page_icon="🎬",
    layout="wide"
)


PAGE_OPTIONS = [
    "🏠 ホーム",
    "🔍 リサーチ・台本照合",
    "🤖 AI生成（API設定後）",
    "📁 生成物一覧",
    "📖 ドキュメント",
    "⚙️ 設定",
    "🧪 テスト",
]

PAGE_ALIASES = {
    "home": "🏠 ホーム",
    "research": "🔍 リサーチ・台本照合",
    "pipeline": "🤖 AI生成（API設定後）",
    "assets": "📁 生成物一覧",
    "docs": "📖 ドキュメント",
    "settings": "⚙️ 設定",
    "tests": "🧪 テスト",
}


def _resolve_initial_page() -> str:
    """クエリまたは環境変数から初期ページを解決する。"""
    page_key = os.getenv("NLM_WEB_DEFAULT_PAGE", "").strip().lower()
    try:
        page_key = st.query_params.get("page", page_key).strip().lower()
    except Exception:
        pass

    return PAGE_ALIASES.get(page_key, PAGE_OPTIONS[0])


def main():
    st.title("🎬 NLMandSlide Video Generator")

    # Sidebar navigation - 整理されたメニュー
    st.sidebar.markdown("### 📍 ナビゲーション")

    # 主要機能
    st.sidebar.markdown("**動画生成**")
    initial_page = _resolve_initial_page()
    page = st.sidebar.selectbox(
        "ページ選択",
        PAGE_OPTIONS,
        index=PAGE_OPTIONS.index(initial_page),
        label_visibility="collapsed"
    )

    # ページ表示
    if page == "🏠 ホーム":
        show_home_page()
    elif page == "🔍 リサーチ・台本照合":
        from src.web.ui.pages import show_research_page
        show_research_page()
    elif page == "🤖 AI生成（API設定後）":
        show_pipeline_page()
    elif page == "📁 生成物一覧":
        show_assets_page()
    elif page == "📖 ドキュメント":
        show_documentation_page()
    elif page == "⚙️ 設定":
        show_settings_page()
    elif page == "🧪 テスト":
        show_tests_page()

    # サイドバーにクイックリンク
    st.sidebar.divider()
    st.sidebar.markdown("### 📚 クイックリンク")
    st.sidebar.markdown("""
    - [CSVフォーマット仕様](docs/spec_csv_input_format.md)
    - [ユーザーガイド](docs/user_guide_manual_workflow.md)
    - [字幕ガイド](docs/subtitle_hardsub_guide.md)
    """)


if __name__ == "__main__":
    main()
