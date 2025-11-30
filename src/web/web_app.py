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

    # Sidebar navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Home", "Pipeline Execution", "CSV Pipeline", "Assets", "Documentation", "Settings", "Tests"]
    )

    if page == "Home":
        show_home_page()
    elif page == "Pipeline Execution":
        show_pipeline_page()
    elif page == "CSV Pipeline":
        show_csv_pipeline_page()
    elif page == "Assets":
        show_assets_page()
    elif page == "Documentation":
        show_documentation_page()
    elif page == "Settings":
        show_settings_page()
    elif page == "Tests":
        show_tests_page()


if __name__ == "__main__":
    main()
