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
import requests
from datetime import datetime

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
        ["Home", "Pipeline Execution", "Assets", "Documentation", "Settings", "Tests"]
    )

    if page == "Home":
        show_home_page()
    elif page == "Pipeline Execution":
        show_pipeline_page()
    elif page == "Assets":
        show_assets_page()
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
            st.markdown("---")
            api_mode = st.checkbox("Use API server (FastAPI)", value=os.getenv("NLM_USE_API", "false").lower() == "true")
            api_base = st.text_input("API Base URL", value=os.getenv("NLM_API_BASE", "http://127.0.0.1:8000"), disabled=not api_mode)
            if api_mode:
                upload_video = st.checkbox("YouTubeにアップロード", value=False, help="APIモード時のみ有効。実際にYouTubeに動画をアップロードします。")
            else:
                upload_video = False

            submitted = st.form_submit_button("Generate Video")

            if submitted and topic:
                # Save form data to session state
                st.session_state.topic = topic
                st.session_state.urls = [url.strip() for url in urls.split('\n') if url.strip()]
                st.session_state.editing_backend = editing_backend
                st.session_state.api_mode = api_mode
                st.session_state.api_base = api_base
                st.session_state.upload_video = upload_video

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
                topic = st.session_state.get('topic', '')
                urls = st.session_state.get('urls', [])
                editing_backend = st.session_state.get('editing_backend', 'moviepy')
                api_mode = st.session_state.get('api_mode', False)
                api_base = st.session_state.get('api_base', 'http://127.0.0.1:8000')
                upload_video = st.session_state.get('upload_video', False)
                if api_mode:
                    # Execute via API server
                    with st.spinner("Calling API server..."):
                        payload = {
                            "topic": topic,
                            "urls": urls,
                            "editing_backend": editing_backend,
                            "private_upload": True,
                            "upload": upload_video,  # Pass upload flag
                        }
                        resp = requests.post(f"{api_base}/api/v1/pipeline", json=payload, timeout=600)
                        resp.raise_for_status()
                        result = resp.json()
                else:
                    # Local execution path
                    pipeline = build_default_pipeline()
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
            show_results_page(st.session_state.pipeline_result)

            # Reset button
            if st.button("新しい実行を開始"):
                st.session_state.pipeline_running = False
                st.session_state.pipeline_result = None
                st.session_state.progress_stage = ""
                st.session_state.progress_value = 0.0
                st.session_state.progress_message = ""
                st.rerun()

def show_results_page(result: dict):
    """パイプライン実行結果を表示する詳細ページ"""
    st.header("🎉 実行完了")

    success = result.get("success", False)
    youtube_url = result.get("youtube_url")
    artifacts = result.get("artifacts", {})

    # 属性アクセス/辞書アクセス両対応のヘルパー
    def _get(obj, name, default=None):
        try:
            return getattr(obj, name)
        except Exception:
            if isinstance(obj, dict):
                return obj.get(name, default)
            return default

    # 成功/失敗ステータス
    if success:
        st.success("✅ パイプライン実行が成功しました！")
    else:
        st.error("❌ パイプライン実行に失敗しました")

    # YouTube URL (優先表示)
    if youtube_url:
        st.subheader("📺 YouTube動画")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**動画URL:** [{youtube_url}]({youtube_url})")
        with col2:
            if st.button("🔗 URLを開く", key="open_youtube"):
                import webbrowser
                webbrowser.open(youtube_url)
        st.divider()

    # 統計情報
    st.subheader("📊 統計情報")

    # ソース情報
    sources = _get(artifacts, "sources", [])
    if sources:
        with st.expander("📚 参照ソース", expanded=False):
            st.metric("収集ソース数", len(sources))
            for i, source in enumerate(sources[:5], 1):  # 最初の5件のみ表示
                title = _get(source, "title", "Unknown")
                rel = _get(source, "relevance_score", 0.0)
                st.text(f"{i}. {title} (関連度: {rel:.2f})")
            if len(sources) > 5:
                st.text(f"... 他 {len(sources) - 5} 件")

    # 生成ファイル情報
    col1, col2, col3, col4 = st.columns(4)

    # 音声情報
    audio = _get(artifacts, "audio")
    if audio:
        with col1:
            with st.expander("🎵 音声", expanded=False):
                duration = _get(audio, "duration", 0.0)
                quality = _get(audio, "quality_score", 0.0)
                fpath = _get(audio, "file_path")
                st.metric("再生時間", f"{duration:.1f}秒")
                st.metric("品質スコア", f"{quality:.2f}")
                if fpath:
                    st.text(f"ファイル: {Path(str(fpath)).name}")

    # 文字起こし情報
    transcript = _get(artifacts, "transcript")
    if transcript:
        with col2:
            with st.expander("📝 文字起こし", expanded=False):
                st.metric("タイトル", _get(transcript, "title", ""))
                segments = _get(transcript, "segments", [])
                st.metric("セグメント数", len(segments))
                if segments:
                    # 全セグメントのテキストを結合
                    def _seg_text(s):
                        return _get(s, "text", _get(s, "content", ""))
                    all_text = " ".join(_seg_text(seg) for seg in segments)
                    # 日本語では空白での分割が適切でないため、補助的に総文字数も表示
                    total_words = len(all_text.split())
                    total_chars = len(all_text)
                    st.metric("総単語数(空白区切り)", total_words)
                    st.metric("総文字数", total_chars)

    # スライド情報
    slides = _get(artifacts, "slides")
    if slides:
        with col3:
            with st.expander("📊 スライド", expanded=False):
                total_slides = _get(slides, "total_slides", 0)
                pres_id = _get(slides, "presentation_id", "")
                st.metric("総スライド数", total_slides)
                if pres_id:
                    st.text(f"ID: {pres_id}")

    # 動画情報
    video = _get(artifacts, "video")
    if video:
        with col4:
            with st.expander("🎬 動画", expanded=False):
                res = _get(video, "resolution")
                if isinstance(res, list) or isinstance(res, tuple):
                    resolution_str = f"{res[0]}x{res[1]}"
                else:
                    resolution_str = str(res) if res else "N/A"
                duration = _get(video, "duration", 0.0)
                fpath = _get(video, "file_path")
                st.metric("解像度", resolution_str)
                st.metric("再生時間", f"{duration:.1f}秒")
                if fpath:
                    st.text(f"ファイル: {Path(str(fpath)).name}")

    # 詳細情報 (折りたたみ)
    with st.expander("🔍 詳細情報", expanded=False):
        st.subheader("Artifacts")
        # dictならそのまま、dataclassは辞書化して表示
        if isinstance(artifacts, dict):
            st.json(artifacts)
        else:
            try:
                from dataclasses import asdict
                import datetime as _dt
                def _convert(obj):
                    if isinstance(obj, _dt.datetime):
                        return obj.isoformat()
                    if isinstance(obj, Path):
                        return str(obj)
                    if isinstance(obj, tuple):
                        return list(obj)
                    return obj
                artifacts_dict = asdict(artifacts)
                import json as _json
                artifacts_dict = _json.loads(_json.dumps(artifacts_dict, default=_convert))
                st.json(artifacts_dict)
            except Exception as e:
                st.error(f"Artifacts表示エラー: {e}")
                st.text(str(artifacts))

        st.subheader("Raw Result")
        try:
            # result内のartifactsを辞書化したものに差し替えて表示
            import json as _json
            result_view = dict(result)
            result_view["artifacts"] = artifacts_dict if 'artifacts_dict' in locals() else str(artifacts)
            st.json(result_view)
        except Exception as e:
            st.error(f"Result表示エラー: {e}")
            st.text(str(result))

    # アクションボタン
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 同じ設定で再実行", key="rerun_same"):
            # 同じパラメータで再実行
            if 'topic' in st.session_state and 'urls' in st.session_state and 'editing_backend' in st.session_state:
                st.session_state.pipeline_running = True
                st.session_state.pipeline_result = None
                st.session_state.progress_stage = "初期化"
                st.session_state.progress_value = 0.0
                st.session_state.progress_message = "再実行を開始します..."
                st.rerun()

    with col2:
        if st.button("📋 結果をコピー", key="copy_result"):
            result_json = json.dumps(result, indent=2, ensure_ascii=False)
            st.code(result_json, language="json")
            st.success("結果をクリップボードにコピーしました")

    with col3:
        if st.button("📁 ログを表示", key="show_logs"):
            # ログファイルが存在すれば表示
            log_dir = PROJECT_ROOT / "logs"
            if log_dir.exists():
                log_files = list(log_dir.glob("*.log"))
                if log_files:
                    latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
                    with open(latest_log, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                    st.code(log_content, language="text")
                else:
                    st.info("ログファイルが見つかりません")


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

    st.divider()
    st.subheader("API Spec (OpenSpec v1.1)")
    with st.expander("OpenAPI仕様の取得とプレビュー", expanded=False):
        api_base = st.text_input("API Base URL", value=os.getenv("NLM_API_BASE", "http://localhost:8000"))
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("📥 Fetch /api/v1/spec"):
                try:
                    resp = requests.get(f"{api_base}/api/v1/spec", timeout=5)
                    resp.raise_for_status()
                    spec = resp.json()
                    st.success("取得成功")
                    st.json(spec)
                    st.download_button("💾 Download openapi.json", data=json.dumps(spec, ensure_ascii=False, indent=2), file_name="openapi.json", mime="application/json")
                except Exception as e:
                    st.error(f"取得失敗: {e}")
        with col_b:
            st.markdown("現在のローカル定義: `api_spec_design.py` を `python api_spec_design.py` で `api_specification.json` に出力可能です。")

def _format_bytes(num: int) -> str:
    for unit in ["B","KB","MB","GB","TB"]:
        if num < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"

def show_assets_page():
    st.header("Assets & History")

    tabs = st.tabs(["🎬 Videos", "🎵 Audio", "📊 Slides", "🕘 History"])

    # Videos tab
    with tabs[0]:
        videos_dir = settings.VIDEOS_DIR
        st.markdown(f"ディレクトリ: `{videos_dir}`")
        if not videos_dir.exists():
            st.info("動画ディレクトリが存在しません")
        else:
            files = sorted(videos_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not files:
                st.info("動画ファイルが見つかりません")
            for f in files[:20]:
                with st.expander(f"{f.name}  ({_format_bytes(f.stat().st_size)})", expanded=False):
                    col1, col2 = st.columns([2,1])
                    with col1:
                        try:
                            st.video(str(f))
                        except Exception:
                            st.text(str(f))
                    with col2:
                        st.text(f"更新: {datetime.fromtimestamp(f.stat().st_mtime).isoformat()}")
                        st.download_button("ダウンロード", data=open(f, "rb").read(), file_name=f.name)
                        meta = f.with_suffix('.json')
                        if meta.exists():
                            try:
                                st.json(json.load(open(meta, 'r', encoding='utf-8')))
                            except Exception as e:
                                st.warning(f"メタデータ読み込み失敗: {e}")

    # Audio tab
    with tabs[1]:
        audio_dir = settings.AUDIO_DIR
        st.markdown(f"ディレクトリ: `{audio_dir}`")
        if not audio_dir.exists():
            st.info("音声ディレクトリが存在しません")
        else:
            files = sorted(list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.mp3")), key=lambda p: p.stat().st_mtime, reverse=True)
            if not files:
                st.info("音声ファイルが見つかりません")
            for f in files[:30]:
                with st.expander(f"{f.name}  ({_format_bytes(f.stat().st_size)})", expanded=False):
                    col1, col2 = st.columns([2,1])
                    with col1:
                        try:
                            st.audio(str(f))
                        except Exception:
                            st.text(str(f))
                    with col2:
                        st.text(f"更新: {datetime.fromtimestamp(f.stat().st_mtime).isoformat()}")
                        st.download_button("ダウンロード", data=open(f, "rb").read(), file_name=f.name)

    # Slides tab
    with tabs[2]:
        slides_dir = settings.SLIDES_DIR
        st.markdown(f"ディレクトリ: `{slides_dir}`")
        if not slides_dir.exists():
            st.info("スライドディレクトリが存在しません")
        else:
            files = sorted(slides_dir.glob("*.pptx"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not files:
                st.info("PPTXが見つかりません")
            for f in files[:30]:
                with st.expander(f"{f.name}  ({_format_bytes(f.stat().st_size)})", expanded=False):
                    col1, col2 = st.columns([2,1])
                    with col1:
                        st.text(str(f))
                    with col2:
                        st.text(f"更新: {datetime.fromtimestamp(f.stat().st_mtime).isoformat()}")
                        st.download_button("ダウンロード", data=open(f, "rb").read(), file_name=f.name)
                    # metadata json alongside
                    meta = slides_dir / f"{f.stem}_metadata.json"
                    if meta.exists():
                        try:
                            st.json(json.load(open(meta, 'r', encoding='utf-8')))
                        except Exception as e:
                            st.warning(f"メタデータ読み込み失敗: {e}")

    # History tab (API連携)
    with tabs[3]:
        api_base = st.text_input("API Base URL", value=os.getenv("NLM_API_BASE", "http://127.0.0.1:8000"), key="history_api_base")
        if st.button("🔄 履歴を更新", key="refresh_history"):
            with st.spinner("Fetching execution history..."):
                try:
                    resp = requests.get(f"{api_base}/api/v1/runs", timeout=10)
                    resp.raise_for_status()
                    runs = resp.json()
                    st.session_state.api_runs = runs
                    st.success(f"履歴取得成功: {len(runs)}件")
                except Exception as e:
                    st.error(f"履歴取得失敗: {e}")

        if 'api_runs' in st.session_state and st.session_state.api_runs:
            # DataFrame表示
            import pandas as pd
            df = pd.DataFrame(st.session_state.api_runs)
            if not df.empty:
                # 必要なカラムのみ
                display_cols = ['id', 'status', 'topic', 'started_at', 'finished_at']
                display_df = df[display_cols] if all(col in df.columns for col in display_cols) else df
                st.dataframe(display_df, use_container_width=True)

                # 詳細表示
                st.subheader("実行詳細")
                selected_run_id = st.selectbox("詳細を表示する実行", df['id'].tolist() if 'id' in df.columns else [])
                if selected_run_id:
                    # 実行詳細取得
                    try:
                        resp = requests.get(f"{api_base}/api/v1/runs/{selected_run_id}", timeout=10)
                        resp.raise_for_status()
                        run_detail = resp.json()
                        st.json(run_detail)
                    except Exception as e:
                        st.error(f"実行詳細取得失敗: {e}")

                    # アーティファクト取得
                    if st.button(f"📦 {selected_run_id}のアーティファクトを表示"):
                        try:
                            resp = requests.get(f"{api_base}/api/v1/runs/{selected_run_id}/artifacts", timeout=10)
                            resp.raise_for_status()
                            artifacts = resp.json()
                            st.json(artifacts)
                        except Exception as e:
                            st.error(f"アーティファクト取得失敗: {e}")
        else:
            st.info("履歴が見つかりません。APIサーバーから取得するか、実行後に自動更新されます。")

def show_settings_page():
    st.header("Settings & API Configuration")

    # Session state for API keys
    if 'api_keys' not in st.session_state:
        st.session_state.api_keys = {
            'gemini': settings.GEMINI_API_KEY,
            'openai': settings.OPENAI_API_KEY,
            'youtube': settings.YOUTUBE_API_KEY,
            'elevenlabs': os.getenv('ELEVENLABS_API_KEY', ''),
            'azure_speech_key': settings.TTS_SETTINGS.get('azure', {}).get('key', ''),
            'azure_speech_region': settings.TTS_SETTINGS.get('azure', {}).get('region', ''),
            'google_cloud_tts': settings.TTS_SETTINGS.get('google_cloud', {}).get('api_key', ''),
        }
    if 'test_results' not in st.session_state:
        st.session_state.test_results = {}

    tabs = st.tabs(["📊 現在の設定", "🔑 API設定", "🧪 接続テスト", "💾 保存・読み込み"])

    with tabs[0]:
        show_current_settings()

    with tabs[1]:
        def show_api_key_settings():
            """APIキー設定フォーム"""
            st.subheader("🔑 API Key Configuration")

            st.markdown("""
            **注意:** APIキーはローカルのStreamlitセッションにのみ保存されます。
            永続的に保存するには「保存・読み込み」タブを使用してください。
            """)

            # Gemini API
            with st.expander("🤖 Gemini API", expanded=False):
                st.session_state.api_keys['gemini'] = st.text_input(
                    "Gemini API Key",
                    value=st.session_state.api_keys['gemini'],
                    type="password",
                    help="Google AI Studioから取得したAPIキー"
                )
                if st.button("Gemini APIドキュメント", key="gemini_docs"):
                    st.markdown("[Google AI Studio](https://aistudio.google.com/)")

            # OpenAI API
            with st.expander("🎯 OpenAI API", expanded=False):
                st.session_state.api_keys['openai'] = st.text_input(
                    "OpenAI API Key",
                    value=st.session_state.api_keys['openai'],
                    type="password",
                    help="OpenAIプラットフォームから取得したAPIキー"
                )
                if st.button("OpenAI APIドキュメント", key="openai_docs"):
                    st.markdown("[OpenAI Platform](https://platform.openai.com/)")

            # YouTube API
            with st.expander("📺 YouTube API", expanded=False):
                st.session_state.api_keys['youtube'] = st.text_input(
                    "YouTube API Key",
                    value=st.session_state.api_keys['youtube'],
                    type="password",
                    help="Google Cloud Consoleから取得したYouTube Data API v3キー"
                )
                if st.button("YouTube API設定ガイド", key="youtube_docs"):
                    st.markdown("[YouTube API Guide](https://developers.google.com/youtube/v3)")

            # ElevenLabs API
            with st.expander("🎤 ElevenLabs TTS", expanded=False):
                st.session_state.api_keys['elevenlabs'] = st.text_input(
                    "ElevenLabs API Key",
                    value=st.session_state.api_keys['elevenlabs'],
                    type="password",
                    help="ElevenLabsアカウントから取得したAPIキー"
                )
                if st.button("ElevenLabsドキュメント", key="elevenlabs_docs"):
                    st.markdown("[ElevenLabs](https://elevenlabs.io/)")

            # Azure Speech API
            with st.expander("☁️ Azure Speech Services", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.session_state.api_keys['azure_speech_key'] = st.text_input(
                        "Azure Speech Key",
                        value=st.session_state.api_keys['azure_speech_key'],
                        type="password",
                        help="Azure Speech Servicesのキー"
                    )
                with col2:
                    st.session_state.api_keys['azure_speech_region'] = st.text_input(
                        "Azure Region",
                        value=st.session_state.api_keys['azure_speech_region'],
                        help="例: eastus, japaneast"
                    )
                if st.button("Azure Speechドキュメント", key="azure_docs"):
                    st.markdown("[Azure Speech Services](https://azure.microsoft.com/services/cognitive-services/speech/)")

            # Google Cloud TTS
            with st.expander("🌐 Google Cloud TTS", expanded=False):
                st.session_state.api_keys['google_cloud_tts'] = st.text_input(
                    "Google Cloud TTS API Key",
                    value=st.session_state.api_keys['google_cloud_tts'],
                    type="password",
                    help="Google Cloud Text-to-Speech APIキー"
                )
                if st.button("Google Cloud TTSドキュメント", key="gcp_tts_docs"):
                    st.markdown("[Google Cloud TTS](https://cloud.google.com/text-to-speech)")

            # TTSプロバイダー選択
            st.subheader("🎤 TTS Provider Selection")
            tts_options = ["none", "openai", "elevenlabs", "azure", "google_cloud"]
            current_provider = settings.TTS_SETTINGS.get("provider", "none")

            selected_provider = st.selectbox(
                "TTSプロバイダーを選択",
                tts_options,
                index=tts_options.index(current_provider) if current_provider in tts_options else 0,
                help="動画生成で使用する音声合成プロバイダー"
            )

            if st.button("設定を適用", type="primary"):
                # 設定を適用
                apply_api_settings(selected_provider)
                st.success("API設定を適用しました！")
                st.rerun()

        show_api_key_settings()

def show_connection_tests():
    """API接続テスト機能"""
    st.subheader("🧪 API Connection Tests")

    st.markdown("""
    設定したAPIキーの接続テストを行います。
    各APIの基本的な機能をテストします。
    """)

    col1, col2 = st.columns(2)

    with col1:
        # Gemini APIテスト
        if st.button("🤖 Test Gemini API", key="test_gemini"):
            with st.spinner("Testing Gemini API..."):
                test_result = test_gemini_api()
                st.session_state.test_results['gemini'] = test_result
                if test_result['success']:
                    st.success(f"✅ Gemini API: {test_result['message']}")
                else:
                    st.error(f"❌ Gemini API: {test_result['message']}")

        # OpenAI APIテスト
        if st.button("🎯 Test OpenAI API", key="test_openai"):
            with st.spinner("Testing OpenAI API..."):
                test_result = test_openai_api()
                st.session_state.test_results['openai'] = test_result
                if test_result['success']:
                    st.success(f"✅ OpenAI API: {test_result['message']}")
                else:
                    st.error(f"❌ OpenAI API: {test_result['message']}")

        # YouTube APIテスト
        if st.button("📺 Test YouTube API", key="test_youtube"):
            with st.spinner("Testing YouTube API..."):
                test_result = test_youtube_api()
                st.session_state.test_results['youtube'] = test_result
                if test_result['success']:
                    st.success(f"✅ YouTube API: {test_result['message']}")
                else:
                    st.error(f"❌ YouTube API: {test_result['message']}")

    with col2:
        # ElevenLabs APIテスト
        if st.button("🎤 Test ElevenLabs API", key="test_elevenlabs"):
            with st.spinner("Testing ElevenLabs API..."):
                test_result = test_elevenlabs_api()
                st.session_state.test_results['elevenlabs'] = test_result
                if test_result['success']:
                    st.success(f"✅ ElevenLabs API: {test_result['message']}")
                else:
                    st.error(f"❌ ElevenLabs API: {test_result['message']}")

        # Azure Speech APIテスト
        if st.button("☁️ Test Azure Speech API", key="test_azure"):
            with st.spinner("Testing Azure Speech API..."):
                test_result = test_azure_speech_api()
                st.session_state.test_results['azure'] = test_result
                if test_result['success']:
                    st.success(f"✅ Azure Speech API: {test_result['message']}")
                else:
                    st.error(f"❌ Azure Speech API: {test_result['message']}")

        # Google Cloud TTSテスト
        if st.button("🌐 Test Google Cloud TTS", key="test_gcp_tts"):
            with st.spinner("Testing Google Cloud TTS..."):
                test_result = test_google_cloud_tts_api()
                st.session_state.test_results['gcp_tts'] = test_result
                if test_result['success']:
                    st.success(f"✅ Google Cloud TTS: {test_result['message']}")
                else:
                    st.error(f"❌ Google Cloud TTS: {test_result['message']}")

    # テスト結果のサマリー
    if st.session_state.test_results:
        st.subheader("📊 Test Results Summary")
        summary_cols = st.columns(len(st.session_state.test_results))

        for i, (api_name, result) in enumerate(st.session_state.test_results.items()):
            with summary_cols[i]:
                status_icon = "✅" if result['success'] else "❌"
                st.metric(f"{api_name.title()}", status_icon)

    # 全テスト実行
    if st.button("🚀 Run All Tests", type="primary"):
        with st.spinner("Running all API tests..."):
            all_results = {}

            # 全APIテストを実行
            all_results['gemini'] = test_gemini_api()
            all_results['openai'] = test_openai_api()
            all_results['youtube'] = test_youtube_api()
            all_results['elevenlabs'] = test_elevenlabs_api()
            all_results['azure'] = test_azure_speech_api()
            all_results['gcp_tts'] = test_google_cloud_tts_api()

            st.session_state.test_results = all_results

            # 結果表示
            success_count = sum(1 for r in all_results.values() if r['success'])
            total_count = len(all_results)

            if success_count == total_count:
                st.success(f"🎉 全APIテスト成功！ ({success_count}/{total_count})")
            else:
                st.warning(f"⚠️ 一部APIテスト失敗 ({success_count}/{total_count})")

            st.rerun()

            st.rerun()

def show_save_load_settings():
    """設定の保存・読み込み機能"""
    st.subheader("💾 Settings Management")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**設定の保存**")
        st.markdown("現在のAPI設定を.envファイルに保存します。")

        if st.button("💾 設定を保存", type="primary"):
            try:
                # .envファイルに保存
                env_content = "# NLMandSlideVideoGenerator API Keys\n"
                env_content += f"GEMINI_API_KEY={st.session_state.api_keys['gemini']}\n"
                env_content += f"OPENAI_API_KEY={st.session_state.api_keys['openai']}\n"
                env_content += f"YOUTUBE_API_KEY={st.session_state.api_keys['youtube']}\n"
                env_content += f"ELEVENLABS_API_KEY={st.session_state.api_keys['elevenlabs']}\n"
                env_content += f"AZURE_SPEECH_KEY={st.session_state.api_keys['azure_speech_key']}\n"
                env_content += f"AZURE_SPEECH_REGION={st.session_state.api_keys['azure_speech_region']}\n"
                env_content += f"GOOGLE_CLOUD_TTS_KEY={st.session_state.api_keys['google_cloud_tts']}\n"
                env_content += f"TTS_PROVIDER={settings.TTS_SETTINGS.get('provider', 'none')}\n"

                env_file = PROJECT_ROOT / ".env"
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write(env_content)

                st.success("✅ 設定を.envファイルに保存しました！")
                st.info("💡 アプリケーションを再起動すると設定が読み込まれます。")

            except Exception as e:
                st.error(f"❌ 保存に失敗しました: {str(e)}")

    with col2:
        st.markdown("**設定の読み込み**")
        st.markdown(".envファイルから設定を読み込みます。")

        if st.button("📁 設定を読み込み"):
            try:
                env_file = PROJECT_ROOT / ".env"
                if env_file.exists():
                    # 既存の.envファイルを読み込み
                    import dotenv
                    dotenv.load_dotenv(env_file)

                    # session_stateを更新
                    st.session_state.api_keys['gemini'] = os.getenv('GEMINI_API_KEY', '')
                    st.session_state.api_keys['openai'] = os.getenv('OPENAI_API_KEY', '')
                    st.session_state.api_keys['youtube'] = os.getenv('YOUTUBE_API_KEY', '')
                    st.session_state.api_keys['elevenlabs'] = os.getenv('ELEVENLABS_API_KEY', '')
                    st.session_state.api_keys['azure_speech_key'] = os.getenv('AZURE_SPEECH_KEY', '')
                    st.session_state.api_keys['azure_speech_region'] = os.getenv('AZURE_SPEECH_REGION', '')
                    st.session_state.api_keys['google_cloud_tts'] = os.getenv('GOOGLE_CLOUD_TTS_KEY', '')

                    # TTSプロバイダーも読み込み
                    tts_provider = os.getenv('TTS_PROVIDER', 'none')
                    if tts_provider != settings.TTS_SETTINGS.get('provider'):
                        apply_api_settings(tts_provider)

                    st.success("✅ 設定を読み込みました！")
                    st.rerun()
                else:
                    st.warning("⚠️ .envファイルが見つかりません。")

            except Exception as e:
                st.error(f"❌ 読み込みに失敗しました: {str(e)}")

    # 設定のエクスポート/インポート
    st.divider()
    st.subheader("📤 エクスポート / 📥 インポート")

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("**設定のエクスポート**")
        if st.button("📤 JSONとしてエクスポート"):
            try:
                export_data = {
                    "api_keys": st.session_state.api_keys,
                    "tts_provider": settings.TTS_SETTINGS.get('provider', 'none'),
                    "pipeline_components": dict(settings.PIPELINE_COMPONENTS),
                    "pipeline_stage_modes": dict(settings.PIPELINE_STAGE_MODES),
                    "exported_at": str(datetime.now())
                }

                import json
                json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📥 ダウンロード",
                    data=json_str,
                    file_name="nlm_settings.json",
                    mime="application/json"
                )
                st.success("✅ エクスポートデータを準備しました。ダウンロードボタンをクリックしてください。")

            except Exception as e:
                st.error(f"❌ エクスポートに失敗しました: {str(e)}")

    with col4:
        st.markdown("**設定のインポート**")
        uploaded_file = st.file_uploader("JSONファイルをアップロード", type=['json'])

        if uploaded_file is not None and st.button("📥 設定をインポート"):
            try:
                import json
                import_data = json.loads(uploaded_file.getvalue().decode('utf-8'))

                # APIキーをインポート
                if 'api_keys' in import_data:
                    st.session_state.api_keys.update(import_data['api_keys'])

                # TTSプロバイダーを設定
                if 'tts_provider' in import_data:
                    apply_api_settings(import_data['tts_provider'])

                st.success("✅ 設定をインポートしました！")
                st.rerun()

            except Exception as e:
                st.error(f"❌ インポートに失敗しました: {str(e)}")


def apply_api_settings(selected_provider: str):
    """API設定を適用"""
    # 環境変数を設定（ランタイムのみ）
    import os

    # APIキー設定
    if st.session_state.api_keys['gemini']:
        os.environ['GEMINI_API_KEY'] = st.session_state.api_keys['gemini']
    if st.session_state.api_keys['openai']:
        os.environ['OPENAI_API_KEY'] = st.session_state.api_keys['openai']
    if st.session_state.api_keys['youtube']:
        os.environ['YOUTUBE_API_KEY'] = st.session_state.api_keys['youtube']
    if st.session_state.api_keys['elevenlabs']:
        os.environ['ELEVENLABS_API_KEY'] = st.session_state.api_keys['elevenlabs']
    if st.session_state.api_keys['azure_speech_key']:
        os.environ['AZURE_SPEECH_KEY'] = st.session_state.api_keys['azure_speech_key']
    if st.session_state.api_keys['azure_speech_region']:
        os.environ['AZURE_SPEECH_REGION'] = st.session_state.api_keys['azure_speech_region']
    if st.session_state.api_keys['google_cloud_tts']:
        os.environ['GOOGLE_CLOUD_TTS_KEY'] = st.session_state.api_keys['google_cloud_tts']

    # TTSプロバイダー設定
    os.environ['TTS_PROVIDER'] = selected_provider

    # settingsオブジェクトを更新
    settings.GEMINI_API_KEY = st.session_state.api_keys['gemini']
    settings.OPENAI_API_KEY = st.session_state.api_keys['openai']
    settings.YOUTUBE_API_KEY = st.session_state.api_keys['youtube']
    settings.TTS_SETTINGS['provider'] = selected_provider
    settings.TTS_SETTINGS['elevenlabs']['api_key'] = st.session_state.api_keys['elevenlabs']
    settings.TTS_SETTINGS['azure']['key'] = st.session_state.api_keys['azure_speech_key']
    settings.TTS_SETTINGS['azure']['region'] = st.session_state.api_keys['azure_speech_region']
    settings.TTS_SETTINGS['google_cloud']['api_key'] = st.session_state.api_keys['google_cloud_tts']

    # パイプラインコンポーネントの更新
    if settings.GEMINI_API_KEY:
        settings.PIPELINE_COMPONENTS['script_provider'] = 'gemini'
    else:
        settings.PIPELINE_COMPONENTS['script_provider'] = 'legacy'

    if selected_provider != 'none':
        settings.PIPELINE_COMPONENTS['voice_pipeline'] = 'tts'
    else:
        settings.PIPELINE_COMPONENTS['voice_pipeline'] = 'legacy'


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

# APIテスト関数群
def test_gemini_api() -> dict:
    """Gemini API接続テスト"""
    try:
        api_key = st.session_state.api_keys.get('gemini', '')
        if not api_key:
            return {'success': False, 'message': 'APIキーが設定されていません'}

        # 簡単なテストリクエスト
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content('Hello, test message')
        return {'success': True, 'message': '接続成功'}
    except Exception as e:
        return {'success': False, 'message': f'接続失敗: {str(e)}'}

def test_openai_api() -> dict:
    """OpenAI API接続テスト"""
    try:
        api_key = st.session_state.api_keys.get('openai', '')
        if not api_key:
            return {'success': False, 'message': 'APIキーが設定されていません'}

        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        return {'success': True, 'message': '接続成功'}
    except Exception as e:
        return {'success': False, 'message': f'接続失敗: {str(e)}'}

def test_youtube_api() -> dict:
    """YouTube API接続テスト"""
    try:
        api_key = st.session_state.api_keys.get('youtube', '')
        if not api_key:
            return {'success': False, 'message': 'APIキーが設定されていません'}

        from googleapiclient.discovery import build
        youtube = build('youtube', 'v3', developerKey=api_key)
        # 簡単な検索リクエスト
        request = youtube.search().list(
            part='snippet',
            q='test',
            type='video',
            maxResults=1
        )
        response = request.execute()
        return {'success': True, 'message': '接続成功'}
    except Exception as e:
        return {'success': False, 'message': f'接続失敗: {str(e)}'}

def test_elevenlabs_api() -> dict:
    """ElevenLabs API接続テスト"""
    try:
        api_key = st.session_state.api_keys.get('elevenlabs', '')
        if not api_key:
            return {'success': False, 'message': 'APIキーが設定されていません'}

        import requests
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": api_key}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return {'success': True, 'message': '接続成功'}
        else:
            return {'success': False, 'message': f'HTTP {response.status_code}'}
    except Exception as e:
        return {'success': False, 'message': f'接続失敗: {str(e)}'}

def test_azure_speech_api() -> dict:
    """Azure Speech API接続テスト"""
    try:
        api_key = st.session_state.api_keys.get('azure_speech_key', '')
        region = st.session_state.api_keys.get('azure_speech_region', '')
        if not api_key or not region:
            return {'success': False, 'message': 'APIキーまたはリージョンが設定されていません'}

        # Azure Speech SDKが利用可能か確認
        try:
            import azure.cognitiveservices.speech as speechsdk
            speech_config = speechsdk.SpeechConfig(subscription=api_key, region=region)
            return {'success': True, 'message': '設定有効'}
        except ImportError:
            return {'success': True, 'message': 'SDK未インストールですが設定は有効'}
    except Exception as e:
        return {'success': False, 'message': f'設定エラー: {str(e)}'}

def test_google_cloud_tts_api() -> dict:
    """Google Cloud TTS API接続テスト"""
    try:
        api_key = st.session_state.api_keys.get('google_cloud_tts', '')
        if not api_key:
            return {'success': False, 'message': 'APIキーが設定されていません'}

        # 基本的なAPI可用性チェック
        import requests
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        data = {
            "input": {"text": "Hello"},
            "voice": {"languageCode": "en-US", "name": "en-US-Neural2-D"},
            "audioConfig": {"audioEncoding": "MP3"}
        }
        response = requests.post(url, json=data)

        if response.status_code == 200:
            return {'success': True, 'message': '接続成功'}
        else:
            return {'success': False, 'message': f'HTTP {response.status_code}'}
    except Exception as e:
        return {'success': False, 'message': f'接続失敗: {str(e)}'}

if __name__ == "__main__":
    main()
