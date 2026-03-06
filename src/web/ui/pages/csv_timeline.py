"""CSVタイムラインパイプラインページ"""
import streamlit as st
from pathlib import Path
import traceback



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
            st.caption(theme_descriptions.get(placeholder_theme or "dark", ""))

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
                        csv_content = csv_file.getvalue().decode('utf-8-sig')
                        lines = [line for line in csv_content.strip().split('\n') if line.strip()]
                        csv_row_count = len(lines)
                        st.text(f"行数: {csv_row_count}行")

                        # 先頭3行を表示
                        preview_lines = lines[:3]
                        st.code('\n'.join(preview_lines), language='csv')
                        if len(lines) > 3:
                            st.caption(f"... 他 {len(lines) - 3} 行")
                    except (UnicodeError, AttributeError, TypeError, ValueError) as e:
                        st.error(f"CSVの読み込みに失敗: {e}")
                    except Exception as e:
                        st.error(f"CSVの読み込みに失敗: {e}")

            with col_preview2:
                st.markdown("**音声ファイル:**")
                if audio_dir:
                    audio_path_obj = Path(audio_dir).expanduser()
                    if audio_path_obj.exists() and audio_path_obj.is_dir():
                        wav_files = sorted(audio_path_obj.glob("*.wav"))
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
    # 音声準備ガイダンス（YMM4推奨）
    # ========================================
    with st.expander("🎙️ 音声をまだ用意していない場合（YMM4で作成）"):
        st.markdown("""
        ### YMM4でゆっくりボイス音声を生成（推奨）

        **手順**:
        1. YMM4を起動し、新規プロジェクトを作成
        2. CSVタイムラインをYMM4のプラグインでインポート
        3. YMM4のゆっくりボイス機能で各行の音声を生成
        4. 音声ファイルを `001.wav`, `002.wav`, ... として書き出し
        5. 書き出したディレクトリを上の「音声ディレクトリ」欄に指定

        **参考ドキュメント**:
        - [YMM4プラグインガイド](../docs/user_guide_manual_workflow.md)
        - [音声経路比較](../docs/voice_path_comparison.md)

        **ヒント**:
        - YMM4は内蔵のゆっくりボイスで高品質な音声を生成できます
        - 話者ごとに声色やピッチを調整可能
        - YMM4で直接動画をレンダリングすることも可能
        """)

    st.divider()

    # 実行ボタン

    if st.button("🚀 動画生成開始", disabled=not can_run or st.session_state.csv_pipeline_running):
        if not can_run:
            st.error("CSVファイルと音声ファイル（またはディレクトリ）を指定してください")
        else:
            import tempfile
            import asyncio
            from typing import Optional

            # 音声ファイルの準備
            final_audio_path: Optional[Path] = None
            temp_audio_dir: Optional[str] = None

            if audio_dir:
                # ディレクトリパス指定の場合
                final_audio_path = Path(audio_dir).expanduser()
                if not final_audio_path.exists() or not final_audio_path.is_dir():
                    st.error(f"音声ディレクトリが存在しません: {final_audio_path}")
                    st.info("パスの例: samples/basic_dialogue/audio")
                    return
            elif audio_files_uploaded:
                # アップロードされたWAVファイルを一時ディレクトリに保存
                temp_audio_dir = tempfile.mkdtemp(prefix="audio_")
                final_audio_path = Path(temp_audio_dir)

                # ファイル名でソートして連番で保存
                sorted_files = sorted(audio_files_uploaded, key=lambda x: x.name)
                for i, uploaded_file in enumerate(sorted_files, start=1):
                    wav_path = final_audio_path / f"{i:03d}.wav"
                    with open(wav_path, "wb") as wav_file:
                        wav_file.write(uploaded_file.getvalue())

                st.info(f"📂 {len(sorted_files)}個のWAVファイルを一時ディレクトリに保存しました")

            st.session_state.csv_pipeline_running = True

            # 進捗表示
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                # CSVを一時ファイルに保存
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
                    if csv_file is not None:
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

                if final_audio_path is None:
                    st.error("音声ファイルが指定されていません")
                    return

                async def run_pipeline():
                    assert final_audio_path is not None
                    return await run_csv_pipeline_async(
                        csv_path=csv_path,
                        audio_dir=final_audio_path,
                        topic=topic,
                        quality=quality or "720p",
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
                        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
                            st.warning(f"動画プレビューを表示できません: {e}")
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
            except (OSError, RuntimeError, AttributeError, TypeError, ValueError) as e:
                message = str(e)
                if "ffmpeg" in message.lower():
                    st.error("FFmpeg関連のエラーが発生しました。FFmpegがインストールされているか確認してください。")
                    st.info("コマンドラインで `python scripts/check_environment.py` を実行すると環境チェックが行えます。")
                else:
                    st.error("予期しないエラーが発生しました。ログを確認してください。")
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
