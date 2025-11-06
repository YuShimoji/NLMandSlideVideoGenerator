"""
UI Pages for Web Application
"""
import streamlit as st
from pathlib import Path
from datetime import datetime
import json

from config.settings import settings


def load_markdown_file(filepath):
    """Load markdown content from file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error loading file: {str(e)}"


def show_home_page():
    """ホームページ表示"""
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
    """パイプライン実行ページ表示"""
    st.header("Pipeline Execution")

    # Session state for progress tracking
    if 'pipeline_running' not in st.session_state:
        st.session_state.pipeline_running = False
    if 'pipeline_result' not in st.session_state:
        st.session_state.pipeline_result = None

    # Input section
    st.subheader("Video Generation Parameters")

    col1, col2 = st.columns(2)

    with col1:
        topic = st.text_input("Topic", value="AI技術の最新動向", help="動画のトピックを入力")
        urls = st.text_area("Additional URLs (optional)", height=100,
                          help="関連するURLを1行に1つずつ入力",
                          placeholder="https://example.com/article1\nhttps://example.com/article2")

    with col2:
        quality = st.selectbox("Video Quality", ["1080p", "720p", "480p"], index=0)
        private_upload = st.checkbox("Private Upload", value=True,
                                   help="YouTubeにプライベート動画としてアップロード")
        upload = st.checkbox("Upload to YouTube", value=True,
                           help="生成後にYouTubeにアップロード")

    # Stage mode selection
    st.subheader("Stage Configuration")
    col1, col2, col3 = st.columns(3)

    with col1:
        stage1_mode = st.selectbox("Stage 1 Mode",
                                 ["auto", "manual", "skip"],
                                 index=0,
                                 help="スクリプト生成と音声合成のモード")

    with col2:
        stage2_mode = st.selectbox("Stage 2 Mode",
                                 ["auto", "manual", "skip"],
                                 index=0,
                                 help="動画編集とレンダリングのモード")

    with col3:
        stage3_mode = st.selectbox("Stage 3 Mode",
                                 ["auto", "manual", "skip"],
                                 index=0,
                                 help="投稿と配信のモード")

    # User preferences
    with st.expander("Advanced Options"):
        col1, col2 = st.columns(2)
        with col1:
            generate_thumbnail = st.checkbox("Generate Thumbnail", value=True)
            thumbnail_style = st.selectbox("Thumbnail Style",
                                         ["modern", "classic", "minimal"],
                                         index=0) if generate_thumbnail else None

        with col2:
            schedule_publish = st.checkbox("Schedule Publish", value=False)
            publish_datetime = st.date_input("Publish Date") if schedule_publish else None
            publish_time = st.time_input("Publish Time") if schedule_publish else None

    # Execute button
    if st.button("🎬 Generate Video", type="primary", disabled=st.session_state.pipeline_running):
        if not topic.strip():
            st.error("トピックを入力してください")
            return

        # Prepare parameters
        urls_list = [url.strip() for url in urls.split('\n') if url.strip()]

        user_preferences = {}
        if generate_thumbnail:
            user_preferences["generate_thumbnail"] = True
            user_preferences["thumbnail_style"] = thumbnail_style

        if schedule_publish and publish_datetime and publish_time:
            schedule_dt = datetime.combine(publish_datetime, publish_time)
            user_preferences["schedule"] = schedule_dt.isoformat()

        stage_modes = {
            "stage1": stage1_mode,
            "stage2": stage2_mode,
            "stage3": stage3_mode
        }

        # Start pipeline execution
        st.session_state.pipeline_running = True
        st.session_state.pipeline_result = None

        # Import here to avoid circular imports
        from src.web.logic.pipeline_manager import run_pipeline_async

        # Run pipeline
        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        async def execute_pipeline():
            try:
                result = await run_pipeline_async(
                    topic=topic,
                    urls=urls_list,
                    quality=quality,
                    private_upload=private_upload,
                    upload=upload,
                    stage_modes=stage_modes,
                    user_preferences=user_preferences,
                    progress_callback=lambda phase, progress, message: update_progress(
                        progress_placeholder, status_placeholder, phase, progress, message
                    )
                )
                st.session_state.pipeline_result = result
                st.session_state.pipeline_running = False
                st.rerun()

            except Exception as e:
                st.error(f"パイプライン実行中にエラーが発生しました: {str(e)}")
                st.session_state.pipeline_running = False

        # Run async function
        import asyncio
        asyncio.run(execute_pipeline())

    # Show progress
    if st.session_state.pipeline_running:
        st.info("🎬 パイプライン実行中...")

    # Show results
    if st.session_state.pipeline_result:
        show_pipeline_results(st.session_state.pipeline_result)


def update_progress(progress_placeholder, status_placeholder, phase, progress, message):
    """プログレス更新"""
    progress_placeholder.progress(progress / 100)
    status_placeholder.info(f"{phase}: {message}")


def show_pipeline_results(result):
    """パイプライン実行結果表示"""
    st.success("🎉 動画生成完了!")

    if result.get("success"):
        st.subheader("生成結果")

        # Basic info
        col1, col2 = st.columns(2)
        with col1:
            if result.get("youtube_url"):
                st.markdown(f"**YouTube URL:** {result['youtube_url']}")
            st.markdown(f"**Job ID:** {result.get('job_id', 'N/A')}")

        # Artifacts
        artifacts = result.get("artifacts", {})
        if artifacts:
            st.subheader("生成アーティファクト")

            tabs = st.tabs(["音声", "スライド", "動画", "その他"])

            with tabs[0]:
                if artifacts.get("audio"):
                    audio = artifacts["audio"]
                    st.markdown(f"**ファイル:** {audio.file_path.name}")
                    st.markdown(f"**時間:** {audio.duration:.1f}秒")
                    st.markdown(f"**品質スコア:** {audio.quality_score:.2f}")

            with tabs[1]:
                if artifacts.get("slides"):
                    slides = artifacts["slides"]
                    st.markdown(f"**スライド数:** {slides.total_slides}枚")
                    st.markdown(f"**ファイル:** {slides.file_path.name}")

            with tabs[2]:
                if artifacts.get("video"):
                    video = artifacts["video"]
                    st.markdown(f"**ファイル:** {video.file_path.name}")
                    st.markdown(f"**時間:** {video.duration:.1f}秒")
                    st.markdown(f"**解像度:** {video.resolution}")

            with tabs[3]:
                if artifacts.get("script"):
                    st.markdown("**スクリプト生成:** 完了")
                if artifacts.get("thumbnail_path"):
                    st.markdown("**サムネイル生成:** 完了")
                if artifacts.get("timeline_plan"):
                    st.markdown("**タイムラインプラン:** 生成済み")
    else:
        st.error("動画生成に失敗しました")


def show_assets_page():
    """アセット管理ページ表示"""
    st.header("Assets Management")

    st.markdown("生成されたアセットの管理と閲覧")

    # TODO: Implement assets management
    st.info("アセット管理機能は開発中です")


def show_documentation_page():
    """ドキュメンテーションページ表示"""
    st.header("Documentation")

    PROJECT_ROOT = Path(__file__).parent.parent.parent

    doc_files = {
        "セットアップガイド": PROJECT_ROOT / "README_SETUP.md",
        "使用方法": PROJECT_ROOT / "README.md",
        "最終セットアップ": PROJECT_ROOT / "FINAL_SETUP_GUIDE.md"
    }

    selected_doc = st.selectbox("ドキュメント選択", list(doc_files.keys()))

    if selected_doc:
        filepath = doc_files[selected_doc]
        if filepath.exists():
            content = load_markdown_file(filepath)
            st.markdown(content)
        else:
            st.error(f"ファイルが見つかりません: {filepath}")


def show_settings_page():
    """設定ページ表示"""
    st.header("Settings")

    st.markdown("アプリケーション設定")

    # TODO: Implement settings management
    st.info("設定管理機能は開発中です")


def show_tests_page():
    """テストページ表示"""
    st.header("Tests")

    st.markdown("テスト実行と結果確認")

    if st.button("API統合テスト実行"):
        # Import here to avoid circular imports
        from src.web.logic.test_manager import run_api_tests_async

        progress_placeholder = st.empty()
        result_placeholder = st.empty()

        async def execute_tests():
            try:
                results = await run_api_tests_async(
                    progress_callback=lambda message: progress_placeholder.info(message)
                )
                result_placeholder.json(results)
            except Exception as e:
                result_placeholder.error(f"テスト実行中にエラーが発生しました: {str(e)}")

        import asyncio
        asyncio.run(execute_tests())
