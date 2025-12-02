"""
Web GUI for NLMandSlideVideoGenerator
Streamlit-based dashboard for pipeline management and documentation
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))
sys.path.insert(0, str(PROJECT_ROOT))

from src.web.ui.pages import (
    show_home_page,
    show_pipeline_page,
    show_csv_pipeline_page,
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


def main():
    st.title("🎬 NLMandSlide Video Generator")

    # Sidebar navigation - 整理されたメニュー
    st.sidebar.markdown("### 📍 ナビゲーション")
    
    # 主要機能
    st.sidebar.markdown("**動画生成**")
    page = st.sidebar.selectbox(
        "ページ選択",
        [
            "🏠 ホーム",
            "📹 動画を作る（CSV）",
            "🤖 AI生成（API設定後）",
            "📁 生成物一覧",
            "📖 ドキュメント",
            "⚙️ 設定",
            "🧪 テスト",
        ],
        label_visibility="collapsed"
    )
    
    # ページ表示
    if page == "🏠 ホーム":
        show_home_page()
    elif page == "📹 動画を作る（CSV）":
        show_csv_pipeline_page()
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
