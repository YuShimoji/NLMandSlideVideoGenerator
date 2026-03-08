"""Settings page for the web UI."""

import streamlit as st
import os

from config.settings import settings
from core.persistence import db_manager


def show_settings_page():
    """設定ページ表示"""
    st.header("⚙️ Settings")

    st.markdown("アプリケーション設定の表示と管理")

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
                ["1920x1080 (1080p)", "1280x720 (720p)", "854x480 (480p)"],
                index=0 if resolution == (1920, 1080) else 1 if resolution == (1280, 720) else 2 if resolution == (854, 480) else 0,
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
        provider_str = str(tts.get("provider") or "none")
        provider_value = provider_str.lower()
        provider_labels = {
            "none": "none (無効)",
            "openai": "OpenAI",
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
            ("GEMINI_API_KEY", "Gemini"),
        ]
        for env_var, label in api_keys:
            value = os.environ.get(env_var, "")

            if value:
                st.success(f"✅ 環境変数 `{env_var}` が設定されています: `{value}`")
            else:
                st.info(f"ℹ️ 環境変数 `{env_var}` が未設定です。")

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

        except (ImportError, AttributeError, TypeError, OSError, ValueError, RuntimeError) as e:
            st.error(f"履歴の取得に失敗: {e}")
        except Exception as e:
            st.error(f"履歴の取得に失敗: {e}")

        # クリーンアップ
        st.divider()
        if st.button("🧹 古い履歴を削除（90日以上前）"):
            try:
                db_manager.cleanup_old_records(days=90)
                st.success("古い履歴を削除しました")
            except (AttributeError, TypeError, OSError, ValueError, RuntimeError) as e:
                st.error(f"削除エラー: {e}")
            except Exception as e:
                st.error(f"削除エラー: {e}")

    st.divider()
    st.info("💡 設定を変更するには `config/settings.py` または `.env` ファイルを編集してください。")
