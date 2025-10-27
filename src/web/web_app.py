"""
Web GUI for NLMandSlideVideoGenerator
Streamlit-based dashboard for pipeline management and documentation
"""

import streamlit as st
import sys
import os
from pathlib import Path
import asyncio
import subprocess
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from src.core.pipeline import build_default_pipeline

st.set_page_config(
    page_title="NLMandSlide Video Generator",
    page_icon="🎬",
    layout="wide"
)

def load_markdown_file(filepath):
    """Load markdown content from file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error loading file: {str(e)}"

def main():
    st.title("🎬 NLMandSlide Video Generator")

    # Sidebar navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Home", "Pipeline Execution", "Documentation", "Settings", "Tests"]
    )

    if page == "Home":
        show_home_page()
    elif page == "Pipeline Execution":
        show_pipeline_page()
    elif page == "Documentation":
        show_documentation_page()
    elif page == "Settings":
        show_settings_page()
    elif page == "Tests":
        show_tests_page()

def show_home_page():
    st.header("Welcome to NLMandSlide Video Generator")

    st.markdown("""
    This application generates videos from topics using AI-powered script generation,
    text-to-speech, and video editing.

    **Current Implementation Status:**
    - ✅ Stage 1: Script & Voice Orchestration (Gemini, TTS)
    - ✅ Stage 2: Editing & Rendering (MoviePy, YMM4)
    - ✅ Stage 3: Publishing (YouTube Adapter)
    - ✅ Unit Tests (18 tests passing)
    - ✅ Integration Tests available
    """)

    # Current pipeline components
    st.subheader("Current Pipeline Configuration")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Components:**")
        st.code(f"""
Script Provider: {settings.PIPELINE_COMPONENTS['script_provider']}
Voice Pipeline: {settings.PIPELINE_COMPONENTS['voice_pipeline']}
Editing Backend: {settings.PIPELINE_COMPONENTS['editing_backend']}
Platform Adapter: {settings.PIPELINE_COMPONENTS['platform_adapter']}
        """)

    with col2:
        st.markdown("**Stage Modes:**")
        st.code(f"""
Stage 1: {settings.PIPELINE_STAGE_MODES['stage1']}
Stage 2: {settings.PIPELINE_STAGE_MODES['stage2']}
Stage 3: {settings.PIPELINE_STAGE_MODES['stage3']}
        """)

def show_pipeline_page():
    st.header("Pipeline Execution")

    # Session state for progress tracking
    if 'pipeline_running' not in st.session_state:
        st.session_state.pipeline_running = False
    if 'pipeline_result' not in st.session_state:
        st.session_state.pipeline_result = None
    if 'progress_stage' not in st.session_state:
        st.session_state.progress_stage = ""
    if 'progress_value' not in st.session_state:
        st.session_state.progress_value = 0.0
    if 'progress_message' not in st.session_state:
        st.session_state.progress_message = ""

    # Input form (only show when not running)
    if not st.session_state.pipeline_running:
        with st.form("pipeline_form"):
            topic = st.text_input("Topic", placeholder="Enter the topic for video generation")
            urls = st.text_area("Source URLs (optional)", placeholder="One URL per line", height=100)
            editing_backend = st.selectbox("Editing Backend", ["moviepy", "ymm4"], index=0)

            submitted = st.form_submit_button("Generate Video")

            if submitted and topic:
                # Save form data to session state
                st.session_state.topic = topic
                st.session_state.urls = [url.strip() for url in urls.split('\n') if url.strip()]
                st.session_state.editing_backend = editing_backend

                # Start pipeline execution
                st.session_state.pipeline_running = True
                st.session_state.pipeline_result = None
                st.session_state.progress_stage = "初期化"
                st.session_state.progress_value = 0.0
                st.session_state.progress_message = "パイプラインを開始します..."
                st.rerun()

    # Progress display (show when running or completed)
    if st.session_state.pipeline_running or st.session_state.pipeline_result:
        st.subheader("実行状況")

        # Progress bar
        progress_bar = st.progress(st.session_state.progress_value)

        # Current stage and message
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric("現在のステージ", st.session_state.progress_stage)
        with col2:
            st.text(st.session_state.progress_message)

        # Execute pipeline if running
        if st.session_state.pipeline_running:
            try:
                # Build pipeline
                pipeline = build_default_pipeline()

                # Prepare sources
                topic = st.session_state.get('topic', '')
                urls = st.session_state.get('urls', [])
                editing_backend = st.session_state.get('editing_backend', 'moviepy')

                # Override settings for this run
                original_backend = settings.PIPELINE_COMPONENTS['editing_backend']
                settings.PIPELINE_COMPONENTS['editing_backend'] = editing_backend

                # Progress callback function
                def progress_callback(stage, value, message):
                    st.session_state.progress_stage = stage
                    st.session_state.progress_value = value
                    st.session_state.progress_message = message

                # Execute pipeline
                result = asyncio.run(pipeline.run(
                    topic=topic,
                    urls=urls,
                    progress_callback=progress_callback
                ))

                # Restore settings
                settings.PIPELINE_COMPONENTS['editing_backend'] = original_backend

                # Mark as completed
                st.session_state.pipeline_running = False
                st.session_state.pipeline_result = result

                st.success("Pipeline completed!")
                st.rerun()

            except Exception as e:
                st.session_state.pipeline_running = False
                st.error(f"Pipeline failed: {str(e)}")

        # Show result if completed
        if st.session_state.pipeline_result:
            st.subheader("実行結果")
            st.json(st.session_state.pipeline_result)

            # Reset button
            if st.button("新しい実行を開始"):
                st.session_state.pipeline_running = False
                st.session_state.pipeline_result = None
                st.session_state.progress_stage = ""
                st.session_state.progress_value = 0.0
                st.session_state.progress_message = ""
                st.rerun()

def show_documentation_page():
    st.header("Documentation")

    docs_dir = PROJECT_ROOT / "docs"
    md_files = list(docs_dir.glob("*.md"))

    if md_files:
        selected_doc = st.selectbox(
            "Select Document",
            [f.stem for f in md_files],
            format_func=lambda x: x.replace('_', ' ').title()
        )

        if selected_doc:
            filepath = docs_dir / f"{selected_doc}.md"
            content = load_markdown_file(filepath)
            st.markdown(content)
    else:
        st.warning("No documentation files found in docs/ directory")

def show_settings_page():
    st.header("Settings Overview")

    st.subheader("Pipeline Components")
    for key, value in settings.PIPELINE_COMPONENTS.items():
        st.text(f"{key}: {value}")

    st.subheader("Stage Modes")
    for key, value in settings.PIPELINE_STAGE_MODES.items():
        st.text(f"{key}: {value}")

    st.subheader("API Keys Status")
    api_status = {
        "Gemini": bool(settings.GEMINI_API_KEY),
        "OpenAI": bool(settings.OPENAI_API_KEY),
        "YouTube": bool(settings.YOUTUBE_API_KEY),
        "ElevenLabs": bool(os.getenv("ELEVENLABS_API_KEY", "")),
    }

    for api, configured in api_status.items():
        status = "✅ Configured" if configured else "❌ Not configured"
        st.text(f"{api}: {status}")

def show_tests_page():
    st.header("Test Execution")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Run Unit Tests"):
            with st.spinner("Running pytest..."):
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "pytest", "--tb=short", "-q"],
                        capture_output=True,
                        text=True,
                        cwd=PROJECT_ROOT
                    )
                    st.code(result.stdout)
                    if result.stderr:
                        st.error(result.stderr)
                except Exception as e:
                    st.error(f"Test execution failed: {str(e)}")

    with col2:
        if st.button("Run Integration Test"):
            with st.spinner("Running integration test..."):
                try:
                    result = subprocess.run(
                        [sys.executable, "run_modular_demo.py"],
                        capture_output=True,
                        text=True,
                        cwd=PROJECT_ROOT
                    )
                    st.code(result.stdout)
                    if result.stderr:
                        st.warning(result.stderr)
                except Exception as e:
                    st.error(f"Integration test failed: {str(e)}")

if __name__ == "__main__":
    main()
