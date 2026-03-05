"""
Pipeline Page - Video Generation Interface
"""
import asyncio
from datetime import datetime

import streamlit as st

from src.web.logic.pipeline_manager import run_pipeline_async


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

            except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
                st.error(f"パイプライン実行中にエラーが発生しました: {str(e)}")
                st.session_state.pipeline_running = False

            except Exception as e:
                st.error(f"パイプライン実行中にエラーが発生しました: {str(e)}")
                st.session_state.pipeline_running = False

        # Run async function
        asyncio.run(execute_pipeline())

    # Show progress
    if st.session_state.pipeline_running:
        st.info("🎬 パイプライン実行中...")

    # Show results
    if st.session_state.pipeline_result:
        show_pipeline_results(st.session_state.pipeline_result)
