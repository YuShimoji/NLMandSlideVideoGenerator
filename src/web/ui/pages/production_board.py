"""
プロダクションボード画面 (SP-053 Phase 1)

動画制作ラインをカンバンスタイルで管理する。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from src.core.production_line import (
    LineStatus,
    ProductionLine,
    ProductionLineStore,
    _update_status_from_phase,
)


# --- 定数 ---

BOARD_COLUMNS = [
    ("nlm", "NLM準備", "Phase 0-1"),
    ("structuring", "構造化", "Phase 2-5"),
    ("producing", "YMM4制作", "Phase 6"),
    ("publishing", "公開準備", "Phase 7"),
]

STATUS_INDICATORS = {
    "draft": "[ ]",
    "selecting": "[?]",
    "structuring": "[~]",
    "producing": "[~]",
    "reviewing": "[!]",
    "publishing": "[>]",
    "done": "[v]",
    "failed": "[x]",
    "cancelled": "[-]",
}


def _get_store() -> ProductionLineStore:
    """セッションスコープのストアインスタンスを取得する"""
    if "production_store" not in st.session_state:
        st.session_state.production_store = ProductionLineStore()
    return st.session_state.production_store


def _render_line_card(line: ProductionLine) -> None:
    """ライン1件をカード風に表示する"""
    indicator = STATUS_INDICATORS.get(line.status, "[ ]")
    age = _format_age(line.updated_at)

    st.markdown(
        f"**{indicator} {line.topic[:30]}**"
        + (f"{'...' if len(line.topic) > 30 else ''}")
    )
    st.caption(f"{line.display_status} | {age}")

    if line.segment_count > 0:
        st.caption(f"{line.segment_count}seg / {line.estimated_duration / 60:.0f}min")

    if line.error_log:
        st.caption(f"[x] {line.error_log[-1][:50]}")

    col_detail, col_action = st.columns([1, 1])
    with col_detail:
        if st.button("詳細", key=f"detail_{line.line_id}", use_container_width=True):
            st.session_state.selected_line_id = line.line_id
            st.session_state.board_view = "detail"
            st.rerun()
    with col_action:
        if line.status == "draft":
            if st.button("開始", key=f"start_{line.line_id}", use_container_width=True):
                line.set_status(LineStatus.SELECTING)
                _get_store().update(line)
                st.rerun()


def _render_board() -> None:
    """カンバンボードを表示する"""
    store = _get_store()
    all_lines = store.list_all()

    # 統計
    counts = store.count_by_status()
    done_count = counts.get("done", 0)
    active_count = sum(v for k, v in counts.items() if k not in ("done", "cancelled", "failed"))

    st.markdown(f"**統計**: {done_count}本完了 / {active_count}本進行中 / 合計{len(all_lines)}本")

    # カンバン列
    cols = st.columns(len(BOARD_COLUMNS))

    for i, (col_key, col_title, col_desc) in enumerate(BOARD_COLUMNS):
        with cols[i]:
            column_lines = store.list_by_column(col_key)
            st.subheader(f"{col_title}")
            st.caption(col_desc)
            st.markdown("---")

            if not column_lines:
                st.caption("(なし)")
            else:
                for line in column_lines:
                    _render_line_card(line)
                    st.markdown("---")

    # 完了・失敗・キャンセル
    finished = [l for l in all_lines if l.status in ("done", "failed", "cancelled")]
    if finished:
        with st.expander(f"完了・停止済み ({len(finished)}件)"):
            for line in finished:
                indicator = STATUS_INDICATORS.get(line.status, "[ ]")
                st.markdown(f"{indicator} **{line.topic}** — {line.display_status} ({_format_age(line.updated_at)})")


def _render_new_line_form() -> None:
    """新規ライン作成フォーム"""
    st.subheader("新規制作ライン")

    with st.form("new_line_form"):
        topic = st.text_input(
            "トピック名",
            placeholder="例: 量子コンピュータの最新動向2026",
        )
        source_urls = st.text_area(
            "ソースURL (任意、1行1URL)",
            height=80,
            placeholder="https://example.com/article1",
        )
        audio_path = st.text_input(
            "Audio Overviewファイルパス (任意)",
            placeholder="data/topics/xxx/audio/overview.mp3",
        )

        submitted = st.form_submit_button("作成", type="primary")

        if submitted and topic.strip():
            store = _get_store()
            line = ProductionLine.create(topic.strip())

            if source_urls.strip():
                line.source_urls = [u.strip() for u in source_urls.split("\n") if u.strip()]
            if audio_path.strip():
                line.audio_path = audio_path.strip()

            # トピックディレクトリ作成
            Path(line.topic_dir).mkdir(parents=True, exist_ok=True)

            store.add(line)
            st.success(f"制作ライン作成: {topic}")
            st.rerun()
        elif submitted:
            st.warning("トピック名を入力してください")


def _render_line_detail(line: ProductionLine) -> None:
    """ライン詳細画面"""
    st.subheader(f"{line.topic}")
    st.caption(f"ID: {line.line_id} | {line.display_status} | Phase {line.current_phase}")

    # Phase進捗バー
    phase_labels = ["NLM", "Audio", "構造化", "台本", "スライド", "CSV", "YMM4", "公開"]
    phase_cols = st.columns(8)
    for i, label in enumerate(phase_labels):
        with phase_cols[i]:
            if f"phase_{i}_end" in line.phase_timestamps:
                st.markdown(f"**[v] {label}**")
            elif i == line.current_phase:
                st.markdown(f"**[~] {label}**")
            else:
                st.markdown(f"[ ] {label}")

    st.markdown("---")

    # 成果物一覧
    st.subheader("成果物")
    artifacts = {
        "音声ファイル": line.audio_path,
        "テキスト": line.transcript_path,
        "構造化台本": line.script_json_path,
        "スライド": line.slides_dir,
        "CSV": line.csv_path,
        "メタデータ": line.metadata_path,
        "MP4": line.mp4_path,
        "サムネイル": line.thumbnail_path,
    }

    for name, path in artifacts.items():
        if path:
            exists = Path(path).exists() if path else False
            status = "[v]" if exists else "[?]"
            st.markdown(f"- {status} **{name}**: `{path}`")

    if line.youtube_url:
        st.markdown(f"- [v] **YouTube**: {line.youtube_url}")

    # セグメント情報
    if line.segment_count > 0:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("セグメント", line.segment_count)
        col2.metric("推定尺", f"{line.estimated_duration / 60:.1f}分")
        col3.metric("話者", ", ".join(line.speaker_names) if line.speaker_names else "-")

    # AI評価
    if line.ai_score > 0:
        st.markdown("---")
        st.subheader("AI評価")
        st.markdown(f"スコア: {'*' * int(line.ai_score)} ({line.ai_score:.1f}/5.0)")
        if line.ai_comment:
            st.markdown(f"コメント: {line.ai_comment}")
        if line.go_decision is not None:
            st.markdown(f"判定: **{'Go' if line.go_decision else 'No-Go'}**")

    # アクション
    st.markdown("---")
    st.subheader("アクション")

    action_cols = st.columns(4)

    with action_cols[0]:
        if line.csv_path and Path(line.csv_path).exists():
            if st.button("CSVパスをコピー"):
                st.code(line.csv_path)
                st.info("上記パスをコピーしてYMM4に貼り付けてください")

    with action_cols[1]:
        if line.status not in ("done", "cancelled"):
            next_phase = line.current_phase + 1
            if next_phase <= 7:
                can_advance, reason = line.can_advance_to(next_phase)
                if can_advance:
                    if st.button(f"Phase {next_phase} へ進める"):
                        line.complete_phase(line.current_phase)
                        line.advance_phase(next_phase)
                        _update_status_by_phase(line)
                        _get_store().update(line)
                        st.rerun()
                else:
                    st.button(f"Phase {next_phase} へ進める", disabled=True)
                    st.caption(reason)

    with action_cols[2]:
        if line.status == "failed":
            if st.button("リトライ"):
                line.retry_from_current()
                _get_store().update(line)
                st.rerun()
        elif line.status not in ("done", "cancelled"):
            if st.button("完了にする"):
                line.set_status(LineStatus.DONE)
                _get_store().update(line)
                st.rerun()

    with action_cols[3]:
        if line.status not in ("done", "cancelled"):
            if st.button("キャンセル"):
                line.set_status(LineStatus.CANCELLED)
                _get_store().update(line)
                st.rerun()

    # パイプライン実行 (Phase 2-5)
    if line.current_phase <= 5 and line.status not in ("done", "cancelled", "failed"):
        st.markdown("---")
        st.subheader("パイプライン自動実行 (Phase 2-5)")

        can_run = bool(line.transcript_path or line.audio_path)
        if not can_run:
            st.warning("テキストファイルまたは音声ファイルのパスを設定してください (下の「パスを更新」)")
        else:
            with st.expander("パイプライン設定"):
                pip_col1, pip_col2 = st.columns(2)
                with pip_col1:
                    pip_style = st.selectbox(
                        "台本スタイル",
                        ["default", "news", "educational", "summary"],
                        key=f"pip_style_{line.line_id}",
                    )
                    pip_duration = st.number_input(
                        "目標動画尺 (分)",
                        min_value=1, max_value=120, value=20,
                        key=f"pip_dur_{line.line_id}",
                    )
                with pip_col2:
                    pip_auto_images = st.checkbox(
                        "ストック画像自動取得",
                        value=True,
                        key=f"pip_img_{line.line_id}",
                    )
                    pip_auto_review = st.checkbox(
                        "自動レビュー",
                        value=True,
                        key=f"pip_rev_{line.line_id}",
                    )

            if st.button("パイプライン実行", key=f"run_pip_{line.line_id}", type="primary"):
                _run_pipeline_for_line(
                    line,
                    style=pip_style,
                    target_duration=int(pip_duration) * 60,
                    auto_images=pip_auto_images,
                    auto_review=pip_auto_review,
                )

    # パス更新フォーム
    st.markdown("---")
    with st.expander("パスを更新"):
        with st.form(f"update_paths_{line.line_id}"):
            new_audio = st.text_input("Audio Overview", value=line.audio_path)
            new_transcript = st.text_input("テキスト", value=line.transcript_path)
            new_script = st.text_input("構造化台本", value=line.script_json_path)
            new_csv = st.text_input("CSV", value=line.csv_path)
            new_mp4 = st.text_input("MP4", value=line.mp4_path)

            if st.form_submit_button("更新"):
                line.audio_path = new_audio.strip()
                line.transcript_path = new_transcript.strip()
                line.script_json_path = new_script.strip()
                line.csv_path = new_csv.strip()
                line.mp4_path = new_mp4.strip()

                # script.jsonからセグメント情報を取得
                if line.script_json_path and Path(line.script_json_path).exists():
                    _load_script_info(line)

                _get_store().update(line)
                st.success("更新しました")
                st.rerun()

    # エラーログ
    if line.error_log:
        st.markdown("---")
        with st.expander(f"エラーログ ({len(line.error_log)}件)"):
            for entry in reversed(line.error_log):
                st.text(entry)


def _update_status_by_phase(line: ProductionLine) -> None:
    """フェーズに応じてステータスを自動更新する (後方互換ラッパー)"""
    _update_status_from_phase(line)


def _run_pipeline_for_line(
    line: ProductionLine,
    style: str = "default",
    target_duration: float = 1200.0,
    auto_images: bool = True,
    auto_review: bool = True,
) -> None:
    """ラインのパイプラインを実行する (Phase 2-5)"""
    import asyncio

    line.set_status(LineStatus.STRUCTURING)
    line.advance_phase(2)
    _get_store().update(line)

    progress = st.progress(0.0, text="パイプライン開始...")

    try:
        # research_cli.pyのrun_pipelineを呼ぶ
        from scripts.research_cli import run_pipeline

        transcript_path = Path(line.transcript_path) if line.transcript_path else None
        audio_path_val = Path(line.audio_path) if line.audio_path else None
        output_dir = Path(line.topic_dir) / "output_csv"

        async def _run():
            return await run_pipeline(
                topic=line.topic,
                auto_review=auto_review,
                output_dir=output_dir,
                auto_images=auto_images,
                target_duration=target_duration,
                style=style,
                transcript_path=transcript_path,
                audio_path=audio_path_val,
            )

        progress.progress(0.2, text="台本構造化中...")

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                csv_path = pool.submit(asyncio.run, _run()).result()
        else:
            csv_path = asyncio.run(_run())

        progress.progress(0.9, text="完了処理中...")

        # 結果をラインに反映
        line.csv_path = str(csv_path)
        line.metadata_path = str(csv_path.parent / "metadata.json")

        # script.jsonがあればセグメント情報を取得
        script_candidates = [
            Path(line.topic_dir) / "output_csv" / "script.json",
            csv_path.parent / "script.json",
        ]
        for sp in script_candidates:
            if sp.exists():
                line.script_json_path = str(sp)
                _load_script_info(line)
                break

        line.complete_phase(5)
        line.advance_phase(6)
        line.set_status(LineStatus.PRODUCING)
        _get_store().update(line)

        progress.progress(1.0, text="パイプライン完了")
        st.success(f"CSV生成完了: {csv_path}")
        st.rerun()

    except Exception as e:
        line.add_error(f"Pipeline failed: {e}")
        line.set_status(LineStatus.FAILED)
        _get_store().update(line)
        progress.progress(1.0, text="エラー")
        st.error(f"パイプラインエラー: {e}")


def _load_script_info(line: ProductionLine) -> None:
    """script.jsonからセグメント情報を読み込む"""
    try:
        data = json.loads(Path(line.script_json_path).read_text(encoding="utf-8"))
        segments = data.get("segments", data if isinstance(data, list) else [])
        line.segment_count = len(segments)
        speakers = set()
        for seg in segments:
            if seg.get("speaker"):
                speakers.add(seg["speaker"])
        line.speaker_names = sorted(speakers)
    except (json.JSONDecodeError, OSError):
        pass


def _format_age(iso_str: str) -> str:
    """ISO日時文字列を経過時間に変換する"""
    if not iso_str:
        return "不明"
    try:
        dt = datetime.fromisoformat(iso_str)
        delta = datetime.now() - dt
        if delta.days > 0:
            return f"{delta.days}日前"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}時間前"
        minutes = delta.seconds // 60
        return f"{minutes}分前"
    except (ValueError, TypeError):
        return "不明"


def _render_batch_selection() -> None:
    """バッチ選定画面: 複数トピックを一括評価"""
    st.subheader("バッチ選定")

    # draft状態のライン一覧
    store = _get_store()
    drafts = store.list_by_status(LineStatus.DRAFT)

    if not drafts:
        st.info("下書きラインがありません。「新規作成」タブでトピックを追加してください。")
        return

    st.markdown(f"**{len(drafts)}件の下書きライン**")
    st.caption("Go/No-Go を判定して、Goしたラインを構造化フェーズに送ります")

    # ライン一覧 + Go/No-Go ボタン
    decisions: dict[str, bool | None] = {}

    for line in drafts:
        with st.container():
            cols = st.columns([3, 1, 1, 1, 1])

            with cols[0]:
                st.markdown(f"**{line.topic}**")
                source_count = len(line.source_urls)
                has_audio = bool(line.audio_path)
                st.caption(
                    f"ソース: {source_count}件"
                    + (f" | 音声: あり" if has_audio else "")
                )

            with cols[1]:
                if line.ai_score > 0:
                    st.markdown(f"{'*' * int(line.ai_score)} {line.ai_score:.1f}")
                else:
                    st.caption("未評価")

            with cols[2]:
                if st.button("Go", key=f"go_{line.line_id}"):
                    decisions[line.line_id] = True

            with cols[3]:
                if st.button("No-Go", key=f"nogo_{line.line_id}"):
                    decisions[line.line_id] = False

            with cols[4]:
                if not line.audio_path and not line.transcript_path:
                    st.caption("(音声/テキスト未設定)")

            st.markdown("---")

    # 一括決定ボタン
    batch_cols = st.columns(3)
    with batch_cols[0]:
        if st.button("全てGo", type="primary"):
            for line in drafts:
                decisions[line.line_id] = True
    with batch_cols[1]:
        if st.button("全てNo-Go"):
            for line in drafts:
                decisions[line.line_id] = False

    # 決定を適用
    for line_id, go in decisions.items():
        line = store.get(line_id)
        if line is None:
            continue
        line.go_decision = go
        if go:
            line.set_status(LineStatus.SELECTING)
        else:
            line.set_status(LineStatus.CANCELLED)
        store.update(line)

    if decisions:
        go_count = sum(1 for v in decisions.values() if v)
        nogo_count = sum(1 for v in decisions.values() if not v)
        if go_count:
            st.success(f"{go_count}件をGoに設定しました")
        if nogo_count:
            st.info(f"{nogo_count}件をNo-Goに設定しました")
        st.rerun()


def _render_script_preview(line: ProductionLine) -> None:
    """台本プレビュー画面"""
    if st.button("< 詳細に戻る"):
        st.session_state.board_view = "detail"
        st.rerun()

    st.subheader(f"台本プレビュー: {line.topic}")

    if not line.script_json_path or not Path(line.script_json_path).exists():
        st.warning("構造化台本がまだ生成されていません")
        return

    data = json.loads(Path(line.script_json_path).read_text(encoding="utf-8"))
    segments = data.get("segments", data if isinstance(data, list) else [])

    # 統計
    stat_cols = st.columns(4)
    stat_cols[0].metric("セグメント", len(segments))
    stat_cols[1].metric("推定尺", f"{line.estimated_duration / 60:.1f}分")

    speakers = sorted({s.get("speaker", "?") for s in segments if s.get("speaker")})
    stat_cols[2].metric("話者", len(speakers))
    stat_cols[3].metric("平均尺/seg", f"{line.estimated_duration / max(len(segments), 1):.0f}秒")

    # フィルタ
    filter_options = ["全て"] + speakers
    selected_filter = st.selectbox("フィルタ", filter_options, key="script_filter")

    st.markdown("---")

    # セグメント一覧
    for i, seg in enumerate(segments):
        speaker = seg.get("speaker", "?")
        text = seg.get("text", seg.get("content", ""))
        duration = seg.get("duration_estimate", seg.get("duration", 0))
        image = seg.get("image_path", "")
        animation = seg.get("animation", "")

        if selected_filter != "全て" and speaker != selected_filter:
            continue

        with st.container():
            seg_cols = st.columns([1, 8])
            with seg_cols[0]:
                st.markdown(f"**#{i+1:02d}**")
                if duration:
                    st.caption(f"{duration:.0f}秒")
            with seg_cols[1]:
                st.markdown(f"**[{speaker}]** {text[:200]}{'...' if len(text) > 200 else ''}")
                meta_parts = []
                if image:
                    meta_parts.append(f"画像: {Path(image).name}")
                if animation:
                    meta_parts.append(f"アニメ: {animation}")
                if meta_parts:
                    st.caption(" | ".join(meta_parts))

    st.markdown("---")
    if st.button("CSV再生成 (パイプライン Phase 4-5)"):
        st.info("詳細画面からパイプラインを実行してください")


def _render_publish_panel(line: ProductionLine) -> None:
    """後処理+公開パネル (Phase 7)"""
    st.subheader("公開準備")

    # MP4検証
    st.markdown("### MP4検証")
    if line.mp4_path and Path(line.mp4_path).exists():
        st.markdown(f"ファイル: `{line.mp4_path}`")
        if st.button("FFprobe検証を実行"):
            _run_mp4_validation(line)
    else:
        st.warning("MP4ファイルが未設定です。「パスを更新」からMP4パスを設定してください。")

    # メタデータ
    st.markdown("---")
    st.markdown("### メタデータ")

    if line.metadata_path and Path(line.metadata_path).exists():
        meta = json.loads(Path(line.metadata_path).read_text(encoding="utf-8"))

        with st.form(f"metadata_edit_{line.line_id}"):
            title = st.text_input("タイトル", value=meta.get("title", line.topic))
            description = st.text_area("説明文", value=meta.get("description", ""), height=120)
            tags_str = st.text_input("タグ (カンマ区切り)", value=", ".join(meta.get("tags", [])))
            privacy = st.selectbox(
                "公開設定",
                ["private", "unlisted", "public"],
                index=["private", "unlisted", "public"].index(meta.get("privacy_status", "private")),
            )

            if st.form_submit_button("メタデータを保存"):
                meta["title"] = title
                meta["description"] = description
                meta["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]
                meta["privacy_status"] = privacy
                Path(line.metadata_path).write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                st.success("メタデータを保存しました")
    else:
        st.info("メタデータファイルがまだ生成されていません")

    # YouTube公開
    st.markdown("---")
    st.markdown("### YouTube公開")

    if line.youtube_url:
        st.success(f"公開済み: {line.youtube_url}")
    else:
        can_publish = (
            line.mp4_path
            and Path(line.mp4_path).exists()
            and line.metadata_path
            and Path(line.metadata_path).exists()
        )
        if can_publish:
            if st.button("YouTubeにアップロード", type="primary"):
                _run_youtube_upload(line)
        else:
            st.warning("MP4とメタデータが揃っていません")


def _run_mp4_validation(line: ProductionLine) -> None:
    """MP4品質検証を実行"""
    try:
        from src.youtube.publisher import validate_mp4
        result = validate_mp4(line.mp4_path)
        if result.get("passed", False):
            st.success(f"全検証項目PASS: {result.get('summary', '')}")
        else:
            st.error(f"検証失敗: {result.get('errors', [])}")
    except ImportError:
        st.info("FFprobe検証はCLIから実行してください: python -m src.youtube.publisher validate " + line.mp4_path)
    except Exception as e:
        st.error(f"検証エラー: {e}")


def _run_youtube_upload(line: ProductionLine) -> None:
    """YouTube公開を実行"""
    try:
        from src.youtube.publisher import YouTubePublisher
        publisher = YouTubePublisher()
        result = publisher.publish(
            mp4_path=line.mp4_path,
            metadata_path=line.metadata_path,
        )
        line.youtube_url = result.get("url", "")
        line.youtube_video_id = result.get("video_id", "")
        line.set_status(LineStatus.DONE)
        _get_store().update(line)
        st.success(f"公開完了: {line.youtube_url}")
        st.rerun()
    except ImportError:
        st.error("YouTube publisher モジュールが利用できません")
    except Exception as e:
        line.add_error(f"YouTube upload failed: {e}")
        line.set_status(LineStatus.FAILED)
        _get_store().update(line)
        st.error(f"公開エラー: {e}")


def show_production_board_page() -> None:
    """プロダクションボードのメインエントリポイント"""
    st.header("プロダクションボード")

    # ビュー切り替え
    if "board_view" not in st.session_state:
        st.session_state.board_view = "board"
    if "selected_line_id" not in st.session_state:
        st.session_state.selected_line_id = None

    # ナビゲーション
    view = st.session_state.board_view
    selected_id = st.session_state.selected_line_id

    if view == "script_preview" and selected_id:
        line = _get_store().get(selected_id)
        if line:
            _render_script_preview(line)
        else:
            st.session_state.board_view = "board"
            st.rerun()
    elif view == "detail" and selected_id:
        if st.button("< ボードに戻る"):
            st.session_state.board_view = "board"
            st.session_state.selected_line_id = None
            st.rerun()

        line = _get_store().get(selected_id)
        if line:
            _render_line_detail(line)

            # 台本プレビューへのリンク
            if line.script_json_path and Path(line.script_json_path).exists():
                if st.button("台本プレビューを開く"):
                    st.session_state.board_view = "script_preview"
                    st.rerun()

            # Phase 7: 公開パネル
            if line.current_phase >= 7 or line.status == "reviewing":
                _render_publish_panel(line)
        else:
            st.error("ラインが見つかりません")
            st.session_state.board_view = "board"
    else:
        # ボードビュー
        tab_board, tab_new, tab_batch = st.tabs(["ボード", "新規作成", "バッチ選定"])

        with tab_board:
            _render_board()

        with tab_new:
            _render_new_line_form()

        with tab_batch:
            _render_batch_selection()
