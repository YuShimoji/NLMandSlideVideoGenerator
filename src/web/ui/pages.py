"""
UI Pages for Web Application
"""
import streamlit as st
from pathlib import Path
from datetime import datetime
import json
import traceback
import io
from contextlib import redirect_stdout

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
    # タイトルはweb_app.pyで表示済みなのでここでは省略

    st.markdown("""
    **CSVと音声ファイルから簡単に動画を生成できます**
    
    NotebookLMやSofTalkで作成した素材を使って、スライド動画を自動生成します。
    """)
    
    # 主要アクションへの導線
    st.divider()
    
    col_main1, col_main2 = st.columns(2)
    
    with col_main1:
        st.markdown("### 🚀 今すぐ動画を作る")
        st.markdown("""
        **CSV Timeline Pipeline** を使って動画を生成します。
        
        **必要なもの:**
        - 📝 CSVファイル（話者名、テロップ）
        - 🔊 WAV音声ファイル（各行に対応）
        """)
        st.info("💡 左のメニューから **CSV Pipeline** を選択してください")
    
    with col_main2:
        st.markdown("### 📋 クイックスタート")
        st.markdown("""
        1. **CSVを準備**: A列=話者名、B列=テロップ
        2. **音声を準備**: 各行に対応するWAVファイル
        3. **CSV Pipeline** でファイルをアップロード
        4. **動画生成開始** をクリック
        """)
        with st.expander("📄 サンプルCSV"):
            st.code("""Speaker1,これは1行目のテロップです
Speaker2,これは2行目のテロップです
Speaker1,これは3行目のテロップです""", language="csv")
    
    st.divider()
    
    # 機能ガイド
    st.subheader("📖 機能ガイド")
    
    col_guide1, col_guide2, col_guide3 = st.columns(3)
    
    with col_guide1:
        st.markdown("**✅ 今すぐ使える**")
        st.markdown("""
        - CSV Pipeline（動画生成）
        - YMM4プロジェクト出力
        - 字幕生成（SRT/ASS/VTT）
        - サムネイル自動生成
        """)
    
    with col_guide2:
        st.markdown("**⚙️ 設定・管理**")
        st.markdown("""
        - 環境チェック（下記）
        - Settings（出力設定）
        - Assets（生成物の確認）
        """)
    
    with col_guide3:
        st.markdown("**🔮 API設定後に利用可能**")
        st.markdown("""
        - Pipeline Execution
        - AI自動スクリプト生成
        - YouTubeアップロード
        """)
    
    st.divider()
    
    # 技術情報（折りたたみ）
    with st.expander("🔧 システム状態（開発者向け）"):
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
    
    # 環境チェックセクション
    st.divider()
    st.subheader("🔧 環境チェック")
    
    if st.button("環境をチェック"):
        with st.spinner("環境をチェック中..."):
            check_results = _run_environment_check()
            
            col_env1, col_env2 = st.columns(2)
            
            with col_env1:
                st.markdown("**必須コンポーネント:**")
                for name, (status, detail) in check_results["essential"].items():
                    icon = "✅" if status else "❌"
                    st.text(f"{icon} {name}: {detail}")
            
            with col_env2:
                st.markdown("**オプション:**")
                for name, (status, detail) in check_results["optional"].items():
                    icon = "✅" if status else "⚠️"
                    st.text(f"{icon} {name}: {detail}")
            
            # サマリー
            all_essential = all(s for s, _ in check_results["essential"].values())
            if all_essential:
                st.success("✅ 必須コンポーネントはすべて揃っています")
            else:
                st.error("❌ 一部の必須コンポーネントが不足しています")


def _run_environment_check():
    """環境チェックを実行"""
    import subprocess
    import shutil
    
    results = {
        "essential": {},
        "optional": {},
    }
    
    # Python パッケージ
    packages = [
        ("moviepy", "MoviePy"),
        ("PIL", "Pillow"),
        ("streamlit", "Streamlit"),
    ]
    for module, name in packages:
        try:
            __import__(module)
            results["essential"][name] = (True, "インストール済み")
        except ImportError:
            results["essential"][name] = (False, "未インストール")
    
    # FFmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            version_line = result.stdout.split('\n')[0] if result.stdout else "バージョン不明"
            results["optional"]["FFmpeg"] = (True, version_line[:40])
        except Exception:
            results["optional"]["FFmpeg"] = (True, ffmpeg_path)
    else:
        results["optional"]["FFmpeg"] = (False, "未インストール（winget install FFmpeg）")
    
    # pysrt
    try:
        import pysrt
        results["optional"]["pysrt"] = (True, "字幕ハードサブ可能")
    except ImportError:
        results["optional"]["pysrt"] = (False, "未インストール（pip install pysrt）")
    
    # AutoHotkey (Windows only)
    ahk_paths = [
        Path("C:/Program Files/AutoHotkey/AutoHotkey.exe"),
        Path("C:/Program Files/AutoHotkey/v2/AutoHotkey.exe"),
    ]
    ahk_found = any(p.exists() for p in ahk_paths)
    if ahk_found:
        results["optional"]["AutoHotkey"] = (True, "YMM4連携可能")
    else:
        results["optional"]["AutoHotkey"] = (False, "YMM4自動操作に必要")
    
    return results


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
    st.header("📖 Documentation")

    # src/web/ui/pages.py → 4階層上がプロジェクトルート
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

    doc_files = {
        "📘 クイックスタート": PROJECT_ROOT / "docs" / "user_guide_manual_workflow.md",
        "📄 CSV入力仕様": PROJECT_ROOT / "docs" / "spec_csv_input_format.md",
        "🔧 セットアップガイド": PROJECT_ROOT / "README_SETUP.md",
        "📚 README": PROJECT_ROOT / "README.md",
        "💬 字幕ハードサブガイド": PROJECT_ROOT / "docs" / "subtitle_hardsub_guide.md",
        "🎙️ TTS/SofTalk連携": PROJECT_ROOT / "docs" / "tts_batch_softalk_aquestalk.md",
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
        provider_value = (tts.get("provider") or "none").lower()
        provider_labels = {
            "none": "none (無効)",
            "openai": "OpenAI",
            "elevenlabs": "ElevenLabs",
            "azure": "Azure Speech",
            "google_cloud": "Google Cloud TTS",
        }
        st.text_input(
            "現在のTTSプロバイダ",
            value=provider_labels.get(provider_value, provider_value),
            disabled=True,
            key="tts_provider",
        )
        
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
            st.text_input("カテゴリID", value=str(yt.get("category_id", "27")), disabled=True)
        with col2:
            st.text_input("プライバシー設定", value=yt.get("privacy_status", "private"), disabled=True)
        
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
        mode_options = ["auto", "manual", "skip"]
        stage1_value = modes.get("stage1", "auto")
        stage2_value = modes.get("stage2", "auto")
        stage3_value = modes.get("stage3", "auto")
        stage1_index = mode_options.index(stage1_value) if stage1_value in mode_options else 0
        stage2_index = mode_options.index(stage2_value) if stage2_value in mode_options else 0
        stage3_index = mode_options.index(stage3_value) if stage3_value in mode_options else 0
        with col1:
            st.selectbox(
                "Stage 1 (スクリプト生成)",
                mode_options,
                index=stage1_index,
                disabled=True,
                key="stage1_mode"
            )
        with col2:
            st.selectbox(
                "Stage 2 (編集・レンダリング)",
                mode_options,
                index=stage2_index,
                disabled=True,
                key="stage2_mode"
            )
        with col3:
            st.selectbox(
                "Stage 3 (公開)",
                mode_options,
                index=stage3_index,
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


def show_csv_pipeline_page():
    """CSVパイプラインページ表示"""
    st.header("📝 CSV Timeline Pipeline")
    
    st.markdown("""
    CSVファイルと音声ファイルから動画を生成します。
    
    **CSVフォーマット:**
    - A列: 話者名 (Speaker1, Speaker2, ...)
    - B列: テロップテキスト
    """)
    
    # Session state
    if 'csv_pipeline_running' not in st.session_state:
        st.session_state.csv_pipeline_running = False
    if 'csv_pipeline_result' not in st.session_state:
        st.session_state.csv_pipeline_result = None
    if 'csv_audio_dir' not in st.session_state:
        st.session_state.csv_audio_dir = ""
    
    st.subheader("入力設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # CSVファイルアップロード
        csv_file = st.file_uploader(
            "CSVファイル",
            type=["csv"],
            help="話者とテロップのCSVファイル"
        )
        
        # 音声入力方式の選択
        audio_input_mode = st.radio(
            "音声入力方式",
            ["📁 ディレクトリパス指定", "📤 WAVファイルをアップロード"],
            horizontal=True,
            help="音声ファイルの入力方式を選択"
        )
        
        audio_dir = ""
        audio_files_uploaded = None
        
        if audio_input_mode == "📁 ディレクトリパス指定":
            # 音声ディレクトリ
            audio_dir = st.text_input(
                "音声ディレクトリ",
                value=st.session_state.csv_audio_dir,
                key="csv_audio_dir",
                help="WAVファイルが格納されたディレクトリパス（001.wav, 002.wav, ...）",
                placeholder="例: samples/basic_dialogue/audio"
            )
        else:
            # 音声ファイルアップロード（複数ファイル対応）
            audio_files_uploaded = st.file_uploader(
                "WAVファイル（複数選択可）",
                type=["wav"],
                accept_multiple_files=True,
                help="001.wav, 002.wav, ... の順番でCSV行に対応します"
            )
            if audio_files_uploaded:
                st.info(f"📎 {len(audio_files_uploaded)}個のWAVファイルを選択中")
                # ファイル名を表示
                with st.expander("選択されたファイル一覧"):
                    for i, f in enumerate(sorted(audio_files_uploaded, key=lambda x: x.name)):
                        st.text(f"{i+1}. {f.name}")
        
        # トピック
        topic = st.text_input(
            "トピック名",
            value="CSVタイムライン動画",
            help="動画のタイトルに使用"
        )
    
    with col2:
        # 出力設定
        quality = st.selectbox(
            "動画品質",
            ["1080p", "720p", "480p"],
            index=1
        )
        
        export_ymm4 = st.checkbox(
            "YMM4エクスポート",
            value=False,
            help="YMM4用のプロジェクトファイルも出力"
        )
        
        upload = st.checkbox(
            "YouTubeアップロード",
            value=False,
            help="生成後にYouTubeにアップロード"
        )
        
        private_upload = st.checkbox(
            "限定公開",
            value=True,
            help="YouTubeに限定公開でアップロード",
            disabled=not upload
        )
    
    # 詳細設定
    with st.expander("詳細設定"):
        col_detail1, col_detail2 = st.columns(2)
        
        with col_detail1:
            max_chars = st.number_input(
                "1スライドあたり最大文字数",
                min_value=20,
                max_value=200,
                value=60,
                help="この文字数を超える行は自動分割されます"
            )
        
        with col_detail2:
            placeholder_theme = st.selectbox(
                "スライドテーマ",
                ["dark", "light", "blue", "green", "warm"],
                index=0,
                help="プレースホルダースライドの配色テーマ"
            )
            theme_descriptions = {
                "dark": "🌙 ダーク（黒系背景・白文字）",
                "light": "☀️ ライト（白系背景・黒文字）",
                "blue": "🔵 ブルー（紺系背景・青アクセント）",
                "green": "🟢 グリーン（深緑背景・緑アクセント）",
                "warm": "🟠 ウォーム（茶系背景・オレンジアクセント）",
            }
            st.caption(theme_descriptions.get(placeholder_theme, ""))
    
    # 入力素材プレビュー
    has_audio_input = audio_dir or (audio_files_uploaded and len(audio_files_uploaded) > 0)
    can_run = csv_file is not None and has_audio_input
    
    if csv_file or has_audio_input:
        with st.expander("📋 入力素材プレビュー", expanded=True):
            col_preview1, col_preview2 = st.columns(2)
            
            csv_row_count = 0
            audio_file_count = 0
            
            with col_preview1:
                if csv_file:
                    st.markdown("**CSVファイル:**")
                    try:
                        import io
                        csv_content = csv_file.getvalue().decode('utf-8-sig')
                        lines = [l for l in csv_content.strip().split('\n') if l.strip()]
                        csv_row_count = len(lines)
                        st.text(f"行数: {csv_row_count}行")
                        
                        # 先頭3行を表示
                        preview_lines = lines[:3]
                        st.code('\n'.join(preview_lines), language='csv')
                        if len(lines) > 3:
                            st.caption(f"... 他 {len(lines) - 3} 行")
                    except Exception as e:
                        st.error(f"CSVの読み込みに失敗: {e}")
            
            with col_preview2:
                st.markdown("**音声ファイル:**")
                if audio_dir:
                    audio_path = Path(audio_dir).expanduser()
                    if audio_path.exists() and audio_path.is_dir():
                        wav_files = sorted(audio_path.glob("*.wav"))
                        audio_file_count = len(wav_files)
                        st.text(f"WAVファイル数: {audio_file_count}個")
                        for wf in wav_files[:5]:
                            st.text(f"  • {wf.name}")
                        if len(wav_files) > 5:
                            st.caption(f"... 他 {len(wav_files) - 5} ファイル")
                    else:
                        st.warning("ディレクトリが見つかりません")
                elif audio_files_uploaded:
                    audio_file_count = len(audio_files_uploaded)
                    st.text(f"アップロード済み: {audio_file_count}ファイル")
            
            # ミスマッチ警告
            if csv_row_count > 0 and audio_file_count > 0:
                if csv_row_count != audio_file_count:
                    st.warning(f"⚠️ CSV行数({csv_row_count})と音声ファイル数({audio_file_count})が一致しません。処理は可能ですが、対応を確認してください。")
                else:
                    st.success(f"✅ CSV行数と音声ファイル数が一致しています（{csv_row_count}件）")
    
    # ========================================
    # 音声生成（SofTalk/AquesTalk）セクション
    # ========================================
    with st.expander("🎙️ 音声をまだ用意していない場合（SofTalk/AquesTalk TTS）"):
        st.markdown("""
        CSVから行ごとの音声ファイル（001.wav, 002.wav, ...）を自動生成できます。  
        **SofTalk** または **AquesTalk** がインストールされている必要があります。
        """)
        
        # Session state for TTS
        if 'tts_running' not in st.session_state:
            st.session_state.tts_running = False
        if 'tts_generated_dir' not in st.session_state:
            st.session_state.tts_generated_dir = None
        if 'tts_log' not in st.session_state:
            st.session_state.tts_log = []
        
        col_tts1, col_tts2 = st.columns(2)
        
        with col_tts1:
            tts_engine = st.selectbox(
                "TTSエンジン",
                ["softalk", "aquestalk"],
                index=0,
                help="使用するTTSエンジンを選択"
            )
            
            # 出力ディレクトリ（CSVファイル名から自動生成）
            default_tts_out = ""
            if csv_file:
                csv_stem = Path(csv_file.name).stem
                default_tts_out = f"data/audio/{csv_stem}_timeline"
            
            tts_out_dir = st.text_input(
                "出力ディレクトリ",
                value=default_tts_out,
                help="生成したWAVファイルの保存先",
                placeholder="例: data/audio/my_timeline"
            )
        
        with col_tts2:
            tts_speaker_map = st.text_input(
                "話者マップJSON（任意）",
                value="",
                help="話者名→声プリセットのマッピングJSONファイルパス",
                placeholder="例: config/speaker_map_yukkuri.json"
            )
            
            tts_dry_run = st.checkbox(
                "ドライラン（実行せずコマンド確認のみ）",
                value=False,
                help="実際にはTTSを実行せず、生成されるコマンドをログに出力"
            )
        
        # 環境変数の確認表示
        import os
        env_var_name = "SOFTALK_EXE" if tts_engine == "softalk" else "AQUESTALK_EXE"
        env_var_value = os.getenv(env_var_name, "")
        
        if env_var_value:
            st.success(f"✅ 環境変数 `{env_var_name}` が設定されています: `{env_var_value}`")
        else:
            st.warning(f"⚠️ 環境変数 `{env_var_name}` が未設定です。TTS実行前に設定してください。")
            st.code(f'$env:{env_var_name} = "C:\\Program Files\\{tts_engine.capitalize()}\\{tts_engine}.exe"', language="powershell")
        
        # TTS実行ボタン
        tts_can_run = csv_file is not None and tts_out_dir and (env_var_value or tts_dry_run)
        
        if st.button("🔊 音声ファイルを生成", disabled=not tts_can_run or st.session_state.tts_running):
            if not csv_file:
                st.error("CSVファイルを先に選択してください")
            elif not tts_out_dir:
                st.error("出力ディレクトリを指定してください")
            else:
                import tempfile
                st.session_state.tts_running = True
                st.session_state.tts_log = []
                
                try:
                    # CSVを一時ファイルに保存
                    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
                        tmp.write(csv_file.getvalue())
                        tts_csv_path = Path(tmp.name)
                    
                    # tts_batch スクリプトをインポートして実行
                    import sys
                    project_root = Path(__file__).parent.parent.parent.parent
                    if str(project_root) not in sys.path:
                        sys.path.insert(0, str(project_root))
                    
                    from scripts.tts_batch_softalk_aquestalk import run_batch
                    
                    tts_out_path = Path(tts_out_dir).expanduser().resolve()
                    speaker_map_path = Path(tts_speaker_map) if tts_speaker_map else None

                    log_buffer = io.StringIO()
                    
                    with st.spinner(f"{'ドライラン中...' if tts_dry_run else 'TTS実行中...'}"):
                        with redirect_stdout(log_buffer):
                            result = run_batch(
                                csv_path=tts_csv_path,
                                out_dir=tts_out_path,
                                engine=tts_engine,
                                voice_preset=None,
                                text_encoding="utf-8",
                                dry_run=tts_dry_run,
                                speaker_map_path=speaker_map_path,
                            )

                    st.session_state.tts_log = log_buffer.getvalue().splitlines()

                    if result == 0:
                        if tts_dry_run:
                            st.success("✅ ドライラン完了（実際のファイルは生成されていません）")
                            st.info("ログを確認し、問題なければドライランをオフにして再実行してください。")
                        else:
                            # 生成されたファイル数を確認
                            generated_files = list(tts_out_path.glob("*.wav"))
                            st.success(f"✅ 音声生成完了: {len(generated_files)}ファイル → `{tts_out_path}`")
                            
                            # 生成ディレクトリを保存（後で audio_dir に自動セット可能）
                            st.session_state.tts_generated_dir = str(tts_out_path)
                            st.session_state.csv_audio_dir = str(tts_out_path)

                            st.info("💡 上の「音声ディレクトリ」欄にこのパスを自動で設定しました。反映されない場合は下のボタンで再設定できます。")
                            st.code(str(tts_out_path), language="text")
                    else:
                        st.error(f"❌ TTS実行に失敗しました（終了コード: {result}）")
                        st.info("環境変数の設定やTTSエンジンのインストール状況を確認してください。")
                
                except FileNotFoundError as e:
                    st.error(f"❌ ファイルが見つかりません: {e}")
                except RuntimeError as e:
                    st.error(f"❌ 実行エラー: {e}")
                    if "環境変数" in str(e):
                        st.info(f"環境変数 `{env_var_name}` を設定してください。")
                except Exception as e:
                    st.error(f"❌ 予期せぬエラー: {e}")
                finally:
                    st.session_state.tts_running = False
        
        # 前回生成したディレクトリやログがあれば表示
        if st.session_state.tts_generated_dir:
            st.info(f"📂 前回生成: `{st.session_state.tts_generated_dir}`")

            col_tts_util1, col_tts_util2 = st.columns(2)

            with col_tts_util1:
                if st.button("このディレクトリを音声ディレクトリにセット", key="set_audio_dir_from_tts"):
                    st.session_state.csv_audio_dir = st.session_state.tts_generated_dir
                    st.success("音声ディレクトリ欄に設定しました。")

            with col_tts_util2:
                if st.session_state.tts_log:
                    with st.expander("TTSログを表示", expanded=tts_dry_run):
                        for line in st.session_state.tts_log:
                            st.text(line)
        elif st.session_state.tts_log:
            with st.expander("TTSログを表示", expanded=tts_dry_run):
                for line in st.session_state.tts_log:
                    st.text(line)
    
    st.divider()
    
    # 実行ボタン
    
    if st.button("🚀 動画生成開始", disabled=not can_run or st.session_state.csv_pipeline_running):
        if not can_run:
            st.error("CSVファイルと音声ファイル（またはディレクトリ）を指定してください")
        else:
            import tempfile
            import asyncio
            
            # 音声ファイルの準備
            audio_path_obj = None
            temp_audio_dir = None
            
            if audio_dir:
                # ディレクトリパス指定の場合
                audio_path_obj = Path(audio_dir).expanduser()
                if not audio_path_obj.exists() or not audio_path_obj.is_dir():
                    st.error(f"音声ディレクトリが存在しません: {audio_path_obj}")
                    st.info("パスの例: samples/basic_dialogue/audio")
                    return
            elif audio_files_uploaded:
                # アップロードされたWAVファイルを一時ディレクトリに保存
                temp_audio_dir = tempfile.mkdtemp(prefix="audio_")
                audio_path_obj = Path(temp_audio_dir)
                
                # ファイル名でソートして連番で保存
                sorted_files = sorted(audio_files_uploaded, key=lambda x: x.name)
                for i, uploaded_file in enumerate(sorted_files, start=1):
                    wav_path = audio_path_obj / f"{i:03d}.wav"
                    with open(wav_path, "wb") as f:
                        f.write(uploaded_file.getvalue())
                
                st.info(f"📂 {len(sorted_files)}個のWAVファイルを一時ディレクトリに保存しました")

            st.session_state.csv_pipeline_running = True
            
            # 進捗表示
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # CSVを一時ファイルに保存
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
                    tmp.write(csv_file.getvalue())
                    csv_path = Path(tmp.name)
                
                status_text.info("パイプラインを初期化中...")
                progress_bar.progress(10)
                
                # パイプライン実行
                from config.settings import settings, create_directories
                from src.web.logic.pipeline_manager import run_csv_pipeline_async

                create_directories()

                # 設定の上書き
                if max_chars:
                    settings.SLIDES_SETTINGS["max_chars_per_slide"] = max_chars

                if placeholder_theme:
                    settings.PLACEHOLDER_THEME = placeholder_theme

                if export_ymm4:
                    settings.PIPELINE_COMPONENTS["editing_backend"] = "ymm4"

                status_text.info("パイプラインを実行中...")
                progress_bar.progress(10)

                # 進捗情報を格納するリスト（コールバック内で更新）
                progress_log = []

                def update_progress(phase: str, progress: float, message: str):
                    """パイプラインからの進捗コールバック"""
                    pct = int(progress * 100)
                    progress_log.append({"phase": phase, "progress": pct, "message": message})
                    # Streamlitの制約上、asyncio内からのUI更新は限定的
                    # ログに記録し、完了後に表示する

                async def run_pipeline():
                    return await run_csv_pipeline_async(
                        csv_path=csv_path,
                        audio_dir=audio_path_obj,
                        topic=topic,
                        quality=quality,
                        private_upload=private_upload,
                        upload=upload,
                        stage_modes=settings.PIPELINE_STAGE_MODES,
                        user_preferences={},
                        progress_callback=update_progress,
                    )

                result = asyncio.run(run_pipeline())
                
                progress_bar.progress(100)
                status_text.success("動画生成完了!")
                
                # 進捗ログを表示
                if progress_log:
                    with st.expander("📊 処理ログ", expanded=False):
                        for entry in progress_log:
                            st.text(f"[{entry['progress']:3d}%] {entry['phase']}: {entry['message']}")
                
                # 結果表示
                st.session_state.csv_pipeline_result = result
                
                artifacts = result.get("artifacts")
                if artifacts:
                    st.subheader("📦 生成結果")
                    job_id = result.get("job_id")
                    if job_id:
                        st.text(f"ジョブID: {job_id}")
                        st.caption("💡 過去のジョブ履歴は [⚙️ 設定] → [ジョブ履歴] タブで確認できます")
                    
                    # 動画ファイル
                    video_path = getattr(artifacts.video, "file_path", None) if hasattr(artifacts, 'video') else None
                    if video_path and Path(video_path).exists():
                        st.success(f"🎬 動画出力: {video_path}")
                        
                        # 動画プレビュー
                        try:
                            st.video(str(video_path))
                        except Exception as e:
                            st.warning(f"動画プレビューを表示できません: {e}")
                        
                        # ファイルサイズ表示
                        file_size = Path(video_path).stat().st_size
                        st.caption(f"ファイルサイズ: {file_size / (1024*1024):.2f} MB")
                    
                    # 字幕ファイル
                    transcript = getattr(artifacts, "transcript", None)
                    if transcript:
                        st.markdown("**📝 字幕ファイル:**")
                        subtitle_dir = Path("data/transcripts")
                        if subtitle_dir.exists():
                            subtitle_files = list(subtitle_dir.glob(f"{transcript.title}*"))
                            if subtitle_files:
                                for sf in subtitle_files:
                                    st.text(f"  • {sf.name}")
                    
                    # サムネイル
                    thumbnail_path = getattr(artifacts, "thumbnail_path", None)
                    if thumbnail_path and Path(thumbnail_path).exists():
                        st.markdown("**🖼️ サムネイル:**")
                        st.image(str(thumbnail_path), width=400)
                        st.caption(f"パス: {thumbnail_path}")
                    
                    # YMM4プロジェクト
                    editing_outputs = getattr(artifacts, "editing_outputs", None)
                    if editing_outputs and "ymm4" in editing_outputs:
                        st.markdown("**🎞️ YMM4プロジェクト:**")
                        ymm4_info = editing_outputs["ymm4"]
                        for key, value in ymm4_info.items():
                            st.text(f"  • {key}: {value}")
                    
                    # YouTube用メタデータ（コピペ用）
                    st.markdown("---")
                    st.markdown("### 📋 YouTube投稿用メタデータ")
                    st.caption("以下のテキストをコピーしてYouTube投稿時に使用できます")
                    
                    # タイトル
                    video_title = transcript.title if transcript else topic
                    st.text_input("タイトル（コピー用）", value=video_title, key="yt_title_copy")
                    
                    # 概要欄
                    description_text = f"""【動画概要】
{video_title}

【目次】
"""
                    if transcript and transcript.segments:
                        for i, seg in enumerate(transcript.segments[:10], 1):
                            time_str = f"{int(seg.start_time // 60):02d}:{int(seg.start_time % 60):02d}"
                            preview_text = seg.text[:30] + "..." if len(seg.text) > 30 else seg.text
                            description_text += f"{time_str} {preview_text}\n"
                    
                    description_text += f"""
#動画 #解説 #{video_title.split()[0] if video_title else '動画'}
"""
                    st.text_area("概要欄（コピー用）", value=description_text, height=200, key="yt_desc_copy")
                    
                    # タグ
                    tags = [video_title.split()[0] if video_title else "動画", "解説", "チュートリアル"]
                    st.text_input("タグ（コピー用）", value=", ".join(tags), key="yt_tags_copy")
                
                # 一時ファイル削除
                csv_path.unlink(missing_ok=True)
                if temp_audio_dir:
                    import shutil
                    shutil.rmtree(temp_audio_dir, ignore_errors=True)
                
            except FileNotFoundError:
                st.error("ファイルまたはディレクトリが見つかりません。CSVファイルと音声ディレクトリのパスを確認してください。")
                with st.expander("詳細なエラーログ"):
                    st.code(traceback.format_exc())
            except Exception as e:
                message = str(e)
                if "ffmpeg" in message.lower():
                    st.error("FFmpeg関連のエラーが発生しました。FFmpegがインストールされているか確認してください。")
                    st.info("コマンドラインで `python scripts/check_environment.py` を実行すると環境チェックが行えます。")
                else:
                    st.error("予期しないエラーが発生しました。ログを確認してください。")
                with st.expander("詳細なエラーログ"):
                    st.code(traceback.format_exc())
            finally:
                st.session_state.csv_pipeline_running = False
    
    # 前回の結果表示
    if st.session_state.csv_pipeline_result:
        with st.expander("前回の実行結果"):
            job_id = st.session_state.csv_pipeline_result.get("job_id")
            if job_id:
                st.text(f"ジョブID: {job_id}")
                st.caption("💡 過去のジョブ履歴は [⚙️ 設定] → [ジョブ履歴] タブで確認できます")
            st.json(st.session_state.csv_pipeline_result)
    
    st.divider()
    
    # サンプルCSV
    st.subheader("サンプルCSV")
    st.code("""Speaker1,これは1行目のテロップです
Speaker2,これは2行目のテロップです
Speaker1,3行目は長いテロップで、自動的に分割されます。文字数が多い場合は複数のスライドに分けられます。
Speaker2,最後のテロップです""", language="csv")
    
    st.info("💡 音声ファイルは `001.wav`, `002.wav`, ... の形式でディレクトリに配置してください。")


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
