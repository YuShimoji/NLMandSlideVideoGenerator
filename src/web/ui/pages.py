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
    st.header("📦 Assets Management")

    st.markdown("生成されたアセットの管理と閲覧")

    from config.settings import settings
    import base64

    # アセット種別の定義
    asset_types = {
        "🎥 動画": {
            "dir": settings.VIDEOS_DIR,
            "patterns": ["*.mp4", "*.webm", "*.avi"],
            "preview": "video",
            "icon": "🎥",
        },
        "🖼️ サムネイル": {
            "dir": settings.THUMBNAILS_DIR,
            "patterns": ["*.png", "*.jpg", "*.jpeg"],
            "preview": "image",
            "icon": "🖼️",
        },
        "🎵 音声": {
            "dir": settings.AUDIO_DIR,
            "patterns": ["*.mp3", "*.wav", "*.m4a"],
            "preview": "audio",
            "icon": "🎵",
        },
        "📝 台本": {
            "dir": settings.TRANSCRIPTS_DIR,
            "patterns": ["*.json", "*.txt"],
            "preview": "text",
            "icon": "📝",
        },
        "🖼️ スライド": {
            "dir": settings.SLIDES_DIR,
            "patterns": ["*.png", "*.pptx"],
            "preview": "image",
            "icon": "🖼️",
        },
    }

    # 統計サマリー
    st.subheader("📊 アセット統計")
    cols = st.columns(len(asset_types))
    total_size = 0
    for i, (name, config) in enumerate(asset_types.items()):
        dir_path = config["dir"]
        if dir_path.exists():
            files = []
            for pattern in config["patterns"]:
                files.extend(dir_path.glob(pattern))
            count = len(files)
            size = sum(f.stat().st_size for f in files if f.is_file())
            total_size += size
        else:
            count = 0
            size = 0
        with cols[i]:
            st.metric(config["icon"], f"{count} files", f"{size // (1024*1024):.1f} MB")
    
    st.caption(f"総容量: {total_size // (1024*1024):.1f} MB")
    st.divider()

    # タブ表示
    asset_tabs = st.tabs(list(asset_types.keys()))

    for tab, (name, config) in zip(asset_tabs, asset_types.items()):
        with tab:
            dir_path = config["dir"]
            if not dir_path.exists():
                st.warning(f"ディレクトリが存在しません: {dir_path}")
                if st.button(f"ディレクトリを作成", key=f"mkdir_{name}"):
                    dir_path.mkdir(parents=True, exist_ok=True)
                    st.rerun()
                continue

            # ファイル一覧取得
            files = []
            for pattern in config["patterns"]:
                files.extend(dir_path.glob(pattern))
            files = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)

            if not files:
                st.info("ファイルがありません")
                continue

            # 検索・フィルタ
            col1, col2 = st.columns([2, 1])
            with col1:
                search_query = st.text_input("🔍 ファイル名検索", key=f"search_{name}")
            with col2:
                sort_option = st.selectbox(
                    "並び替え",
                    ["更新日時 (新しい順)", "更新日時 (古い順)", "名前 (A-Z)", "サイズ (大きい順)"],
                    key=f"sort_{name}"
                )

            # フィルタ適用
            if search_query:
                files = [f for f in files if search_query.lower() in f.name.lower()]

            # ソート適用
            if sort_option == "更新日時 (古い順)":
                files = sorted(files, key=lambda f: f.stat().st_mtime)
            elif sort_option == "名前 (A-Z)":
                files = sorted(files, key=lambda f: f.name.lower())
            elif sort_option == "サイズ (大きい順)":
                files = sorted(files, key=lambda f: f.stat().st_size, reverse=True)

            st.caption(f"表示: {len(files)} ファイル")

            # ファイル一覧表示
            for f in files[:20]:  # 最新20件
                with st.expander(f"📄 {f.name}", expanded=False):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    stat = f.stat()
                    with col1:
                        st.text(f"サイズ: {stat.st_size // 1024:,} KB")
                        st.text(f"更新: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')}")
                    
                    with col2:
                        # ダウンロードボタン
                        try:
                            with open(f, "rb") as file:
                                st.download_button(
                                    "⬇️ ダウンロード",
                                    file.read(),
                                    file_name=f.name,
                                    key=f"download_{f.name}_{id(f)}"
                                )
                        except Exception:
                            st.button("⬇️ ダウンロード", disabled=True, key=f"dl_err_{id(f)}")
                    
                    with col3:
                        # 削除ボタン
                        if st.button("🗑️ 削除", key=f"delete_{f.name}_{id(f)}"):
                            try:
                                f.unlink()
                                st.success(f"削除しました: {f.name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"削除エラー: {e}")
                    
                    # プレビュー
                    preview_type = config["preview"]
                    try:
                        if preview_type == "image" and f.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                            st.image(str(f), use_container_width=True)
                        elif preview_type == "audio" and f.suffix.lower() in [".mp3", ".wav", ".m4a"]:
                            st.audio(str(f))
                        elif preview_type == "video" and f.suffix.lower() in [".mp4", ".webm"]:
                            st.video(str(f))
                        elif preview_type == "text":
                            with open(f, "r", encoding="utf-8") as file:
                                content = file.read()
                                if f.suffix == ".json":
                                    st.json(json.loads(content))
                                else:
                                    st.text(content[:2000])
                                    if len(content) > 2000:
                                        st.caption("... (truncated)")
                    except Exception as e:
                        st.caption(f"プレビュー不可: {e}")

            if len(files) > 20:
                st.info(f"他 {len(files) - 20} ファイルは省略されています")


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
    st.header("⚙️ Settings")

    st.markdown("アプリケーション設定の表示と管理")

    from config.settings import settings
    import os

    # セッション状態の初期化
    if "settings_modified" not in st.session_state:
        st.session_state.settings_modified = {}

    # タブで設定カテゴリを分類
    tabs = st.tabs(["📁 ディレクトリ", "🎥 動画", "🗣️ TTS", "📺 YouTube", "🔧 パイプライン", "📊 ジョブ履歴"])

    # ディレクトリ設定
    with tabs[0]:
        st.subheader("ディレクトリ設定")
        
        dirs_info = [
            ("データディレクトリ", settings.DATA_DIR),
            ("動画出力先", settings.VIDEOS_DIR),
            ("音声出力先", settings.AUDIO_DIR),
            ("スライド出力先", settings.SLIDES_DIR),
            ("サムネイル出力先", settings.THUMBNAILS_DIR),
            ("台本出力先", settings.TRANSCRIPTS_DIR),
        ]
        
        for label, dir_path in dirs_info:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.text_input(label, value=str(dir_path), disabled=True, key=f"dir_{label}")
            with col2:
                exists = dir_path.exists()
                st.write("✅ 存在" if exists else "❌ 未作成")
            with col3:
                if not exists:
                    if st.button("作成", key=f"mkdir_{label}"):
                        dir_path.mkdir(parents=True, exist_ok=True)
                        st.success(f"作成しました: {dir_path}")
                        st.rerun()

        # ディスク使用量
        st.divider()
        st.subheader("ディスク使用量")
        total_size = 0
        for label, dir_path in dirs_info:
            if dir_path.exists():
                size = sum(f.stat().st_size for f in dir_path.rglob("*") if f.is_file())
                total_size += size
                st.text(f"{label}: {size // (1024*1024):.1f} MB")
        st.metric("合計", f"{total_size // (1024*1024):.1f} MB")

    # 動画設定
    with tabs[1]:
        st.subheader("動画設定")
        
        video = settings.VIDEO_SETTINGS
        
        col1, col2 = st.columns(2)
        with col1:
            resolution = video.get("resolution", (1920, 1080))
            st.selectbox(
                "解像度",
                ["1920x1080 (1080p)", "1280x720 (720p)", "3840x2160 (4K)"],
                index=0 if resolution == (1920, 1080) else 1 if resolution == (1280, 720) else 2,
                disabled=True,
                key="video_resolution"
            )
            st.number_input("FPS", value=video.get("fps", 30), disabled=True, key="video_fps")
        
        with col2:
            st.text_input("動画コーデック", value=video.get("video_codec", "libx264"), disabled=True)
            st.text_input("音声コーデック", value=video.get("audio_codec", "aac"), disabled=True)
        
        st.caption("⚠️ これらの設定は config/settings.py で変更できます")

    # TTS設定
    with tabs[2]:
        st.subheader("TTS (音声合成) 設定")
        
        tts = settings.TTS_SETTINGS
        
        provider = st.selectbox(
            "TTSプロバイダ",
            ["gemini", "elevenlabs", "azure", "softalk", "none"],
            index=["gemini", "elevenlabs", "azure", "softalk", "none"].index(tts.get("provider", "gemini")),
            disabled=True,
            key="tts_provider"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("デフォルト言語", value=tts.get("default_language", "ja"), disabled=True)
            st.text_input("デフォルト音声", value=tts.get("default_voice", ""), disabled=True)
        with col2:
            st.number_input("話速", value=float(tts.get("speed", 1.0)), disabled=True, format="%.1f")
            st.number_input("ピッチ", value=float(tts.get("pitch", 0)), disabled=True, format="%.1f")
        
        # 環境変数の確認
        st.divider()
        st.subheader("API キー状態")
        api_keys = [
            ("GOOGLE_API_KEY", "Gemini"),
            ("ELEVENLABS_API_KEY", "ElevenLabs"),
            ("AZURE_SPEECH_KEY", "Azure Speech"),
            ("SOFTALK_EXE", "SofTalk"),
        ]
        for env_var, label in api_keys:
            value = os.environ.get(env_var, "")
            if value:
                st.success(f"✅ {label}: 設定済み")
            else:
                st.warning(f"⚠️ {label}: 未設定 ({env_var})")

    # YouTube設定
    with tabs[3]:
        st.subheader("YouTube 設定")
        
        yt = settings.YOUTUBE_SETTINGS
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("デフォルト言語", value=yt.get("default_language", "ja"), disabled=True)
            st.text_input("カテゴリID", value=str(yt.get("default_category_id", "22")), disabled=True)
        with col2:
            st.text_input("プライバシー設定", value=yt.get("default_privacy", "private"), disabled=True)
        
        st.divider()
        st.subheader("認証状態")
        credentials_path = Path("config/youtube_credentials.json")
        token_path = Path("config/youtube_token.json")
        
        if credentials_path.exists():
            st.success("✅ OAuth クレデンシャル: 設定済み")
        else:
            st.error("❌ OAuth クレデンシャル: 未設定")
            st.caption("config/youtube_credentials.json を配置してください")
        
        if token_path.exists():
            st.success("✅ アクセストークン: 取得済み")
        else:
            st.warning("⚠️ アクセストークン: 未取得（初回実行時に認証が必要）")

    # パイプライン設定
    with tabs[4]:
        st.subheader("パイプライン設定")
        
        components = settings.PIPELINE_COMPONENTS
        modes = settings.PIPELINE_STAGE_MODES
        
        st.markdown("**コンポーネント構成**")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("スクリプトプロバイダ", value=components.get("script_provider", ""), disabled=True)
            st.text_input("音声パイプライン", value=components.get("voice_pipeline", ""), disabled=True)
        with col2:
            st.text_input("編集バックエンド", value=components.get("editing_backend", ""), disabled=True)
            st.text_input("プラットフォームアダプタ", value=components.get("platform_adapter", ""), disabled=True)
        
        st.divider()
        st.markdown("**ステージモード**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.selectbox(
                "Stage 1 (スクリプト生成)",
                ["real", "mock", "hybrid"],
                index=["real", "mock", "hybrid"].index(modes.get("stage1", "mock")),
                disabled=True,
                key="stage1_mode"
            )
        with col2:
            st.selectbox(
                "Stage 2 (編集・レンダリング)",
                ["real", "mock", "hybrid"],
                index=["real", "mock", "hybrid"].index(modes.get("stage2", "mock")),
                disabled=True,
                key="stage2_mode"
            )
        with col3:
            st.selectbox(
                "Stage 3 (公開)",
                ["real", "mock", "hybrid"],
                index=["real", "mock", "hybrid"].index(modes.get("stage3", "mock")),
                disabled=True,
                key="stage3_mode"
            )

    # ジョブ履歴
    with tabs[5]:
        st.subheader("ジョブ履歴")
        
        try:
            from core.persistence import db_manager
            records = db_manager.get_generation_history(limit=20)
            
            if records:
                for record in records:
                    status = record.get("status", "unknown")
                    status_icon = {
                        "completed": "✅",
                        "failed": "❌",
                        "cancelled": "⚪",
                        "running": "🔄",
                    }.get(status, "❓")
                    
                    with st.expander(f"{status_icon} {record.get('topic', 'N/A')} - {record.get('created_at', '')}", expanded=False):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.text(f"ジョブID: {record.get('job_id', 'N/A')}")
                            st.text(f"ステータス: {status}")
                            st.text(f"作成日時: {record.get('created_at', 'N/A')}")
                        with col2:
                            st.text(f"完了日時: {record.get('completed_at', 'N/A')}")
                            duration = record.get("duration")
                            if duration:
                                st.text(f"所要時間: {duration:.1f}秒")
                            if record.get("error_message"):
                                st.error(f"エラー: {record.get('error_message')}")
                        
                        artifacts = record.get("artifacts")
                        if artifacts and isinstance(artifacts, dict):
                            st.json(artifacts)
            else:
                st.info("ジョブ履歴がありません")
                
        except Exception as e:
            st.error(f"履歴の取得に失敗: {e}")
        
        # クリーンアップ
        st.divider()
        if st.button("🧹 古い履歴を削除（90日以上前）"):
            try:
                db_manager.cleanup_old_records(days=90)
                st.success("古い履歴を削除しました")
            except Exception as e:
                st.error(f"削除エラー: {e}")

    st.divider()
    st.info("💡 設定を変更するには `config/settings.py` または `.env` ファイルを編集してください。")


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
