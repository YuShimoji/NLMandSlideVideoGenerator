"""ドキュメンテーションページモジュール"""
from pathlib import Path

import streamlit as st

from web.ui._utils import load_markdown_file


def show_documentation_page():
    """ドキュメンテーションページ表示"""
    st.header("📖 Documentation")

    # src/web/ui/pages/documentation.py → 5階層上がプロジェクトルート
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

    doc_files = {
        "📘 クイックスタート": PROJECT_ROOT / "docs" / "user_guide_manual_workflow.md",
        "📄 CSV入力仕様": PROJECT_ROOT / "docs" / "spec_csv_input_format.md",
        "🔧 セットアップガイド": PROJECT_ROOT / "README_SETUP.md",
        "📚 README": PROJECT_ROOT / "README.md",
        "💬 字幕ハードサブガイド": PROJECT_ROOT / "docs" / "subtitle_hardsub_guide.md",
    }

    selected_doc = st.selectbox("ドキュメント選択", list(doc_files.keys()))

    if selected_doc:
        filepath = doc_files[selected_doc]
        if filepath.exists():
            content = load_markdown_file(filepath)
            st.markdown(content)
        else:
            st.error(f"ファイルが見つかりません: {filepath}")
