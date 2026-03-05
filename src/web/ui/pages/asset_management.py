"""アセット管理ページモジュール"""
import json
from datetime import datetime
from pathlib import Path
from typing import List

import streamlit as st

from config.settings import settings
from core.logger import logger


def show_assets_page():
    """アセット管理ページ表示"""
    st.header("📦 Assets Management")

    st.markdown("生成されたアセットの管理と閲覧")

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
        dir_path: Path = config["dir"]  # type: ignore
        if dir_path.exists():
            stat_files: List[Path] = []
            patterns: list[str] = config["patterns"]  # type: ignore
            for pattern in patterns:
                stat_files.extend(dir_path.glob(pattern))
            count = len(stat_files)
            size = sum(f.stat().st_size for f in stat_files if f.is_file())
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
            dir_path: Path = config["dir"]  # type: ignore
            if not dir_path.exists():
                st.warning(f"ディレクトリが存在しません: {dir_path}")
                if st.button("ディレクトリを作成", key=f"mkdir_{name}"):
                    dir_path.mkdir(parents=True, exist_ok=True)
                    st.rerun()
                continue

            # ファイル一覧取得
            files: List[Path] = []
            patterns: list[str] = config["patterns"]  # type: ignore
            for pattern in patterns:
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
                        except (OSError, AttributeError, TypeError, ValueError) as exc:
                            logger.debug(f"ダウンロードボタン用のファイル読込に失敗: {exc}")
                            st.button("⬇️ ダウンロード", disabled=True, key=f"dl_err_{id(f)}")
                        except Exception as exc:
                            logger.debug(f"ダウンロードボタン用のファイル読込に失敗: {exc}")
                            st.button("⬇️ ダウンロード", disabled=True, key=f"dl_err_{id(f)}")

                    with col3:
                        # 削除ボタン
                        if st.button("🗑️ 削除", key=f"delete_{f.name}_{id(f)}"):
                            try:
                                f.unlink()
                                st.success(f"削除しました: {f.name}")
                                st.rerun()
                            except (OSError, AttributeError, TypeError, ValueError) as e:
                                st.error(f"削除エラー: {e}")
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
                    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as e:
                        st.caption(f"プレビュー不可: {e}")
                    except Exception as e:
                        st.caption(f"プレビュー不可: {e}")

            if len(files) > 20:
                st.info(f"他 {len(files) - 20} ファイルは省略されています")
