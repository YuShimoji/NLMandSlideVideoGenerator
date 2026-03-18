"""
バッチ制作キューページ (SP-040 Phase 3)

topics.json のアップロードまたはインタラクティブ作成 → バッチ実行 → 結果表示。
"""
import asyncio
import json
import traceback
from pathlib import Path
from typing import Any

import streamlit as st


def _default_batch_config() -> dict[str, Any]:
    """空のバッチ設定テンプレートを返す。"""
    return {
        "batch_name": "",
        "defaults": {
            "style": "default",
            "duration": 1800,
            "auto_images": True,
            "auto_review": True,
            "speaker_map": {},
        },
        "topics": [],
    }


def _load_topics_from_upload(uploaded_file) -> dict[str, Any] | None:
    """アップロードされた topics.json を読み込む。"""
    try:
        content = uploaded_file.read().decode("utf-8")
        data = json.loads(content)
        if not isinstance(data, dict) or "topics" not in data:
            st.error("topics.json に 'topics' キーが必要です。")
            return None
        return data
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        st.error(f"JSON パースエラー: {e}")
        return None


def _render_defaults_editor(config: dict[str, Any]) -> dict[str, Any]:
    """デフォルト設定 UI を描画し、更新された defaults を返す。"""
    defaults = config.get("defaults", {})

    col1, col2 = st.columns(2)

    with col1:
        style = st.selectbox(
            "台本スタイル",
            ["default", "news", "educational", "summary"],
            index=["default", "news", "educational", "summary"].index(
                defaults.get("style", "default")
            )
            if defaults.get("style", "default")
            in ["default", "news", "educational", "summary"]
            else 0,
            help="全トピック共通のスタイル。個別トピックでオーバーライド可能",
        )
        duration_min = st.number_input(
            "目標動画尺 (分)",
            min_value=1,
            max_value=120,
            value=defaults.get("duration", 1800) // 60,
            help="秒に変換してパイプラインに渡す",
        )

    with col2:
        auto_images = st.checkbox(
            "ストック画像を自動取得",
            value=defaults.get("auto_images", True),
            help="Pexels/Pixabay API で背景画像を収集",
        )
        auto_review = st.checkbox(
            "自動レビュー",
            value=defaults.get("auto_review", True),
            help="supported→adopted に自動判定",
        )

    speaker_map_str = st.text_input(
        "話者マッピング JSON",
        value=json.dumps(defaults.get("speaker_map", {}), ensure_ascii=False)
        if defaults.get("speaker_map")
        else "",
        placeholder='{"Host1":"れいむ","Host2":"まりさ"}',
        help="全トピック共通の話者マッピング",
    )

    speaker_map = {}
    if speaker_map_str.strip():
        try:
            speaker_map = json.loads(speaker_map_str)
        except json.JSONDecodeError:
            st.warning("話者マッピングの JSON が不正です。空として扱います。")

    return {
        "style": style,
        "duration": int(duration_min) * 60,
        "auto_images": auto_images,
        "auto_review": auto_review,
        "speaker_map": speaker_map,
    }


def _render_topic_list(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """トピックリスト UI を描画し、更新されたリストを返す。"""
    updated: list[dict[str, Any]] = []

    for i, t in enumerate(topics):
        col_topic, col_style, col_dur, col_del = st.columns([4, 2, 1, 1])
        with col_topic:
            new_topic = st.text_input(
                f"トピック {i + 1}",
                value=t.get("topic", ""),
                key=f"batch_topic_{i}",
                label_visibility="collapsed",
                placeholder=f"トピック {i + 1}",
            )
        with col_style:
            new_style = st.text_input(
                "スタイル",
                value=t.get("style", ""),
                key=f"batch_style_{i}",
                label_visibility="collapsed",
                placeholder="(defaults)",
            )
        with col_dur:
            dur_val = t.get("duration", 0)
            new_dur = st.number_input(
                "尺(分)",
                min_value=0,
                max_value=120,
                value=dur_val // 60 if dur_val else 0,
                key=f"batch_dur_{i}",
                label_visibility="collapsed",
            )
        with col_del:
            delete = st.checkbox("削除", key=f"batch_del_{i}", label_visibility="collapsed")

        if not delete:
            entry: dict[str, Any] = {"topic": new_topic}
            if new_style.strip():
                entry["style"] = new_style.strip()
            if new_dur > 0:
                entry["duration"] = int(new_dur) * 60
            # seed_urls は元データを引き継ぐ
            if t.get("seed_urls"):
                entry["seed_urls"] = t["seed_urls"]
            updated.append(entry)

    return updated


async def _execute_batch(
    config: dict[str, Any],
    output_dir: Path,
    interval: int,
    progress_container,
) -> dict[str, Any]:
    """バッチを実行し、結果辞書を返す。"""
    from scripts.research_cli import run_pipeline

    defaults = config.get("defaults", {})
    topics = config.get("topics", [])
    batch_name = config.get("batch_name", "batch")

    base_output = output_dir / batch_name
    base_output.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    total = len(topics)

    for i, topic_config in enumerate(topics):
        topic_text = topic_config.get("topic", "")
        if not topic_text:
            results.append({"topic": "", "status": "skipped", "reason": "empty topic"})
            continue

        merged = {**defaults, **topic_config}
        topic_output = base_output / f"topic_{i + 1:02d}"
        topic_output.mkdir(parents=True, exist_ok=True)

        progress_container.progress(
            (i) / total,
            text=f"[{i + 1}/{total}] {topic_text[:40]}...",
        )

        try:
            speaker_map = merged.get("speaker_map") or defaults.get("speaker_map")
            if isinstance(speaker_map, str):
                speaker_map = json.loads(speaker_map)

            csv_path = await run_pipeline(
                topic=topic_text,
                urls=merged.get("seed_urls"),
                max_sources=merged.get("max_sources", 5),
                auto_review=merged.get("auto_review", True),
                slides_dir=Path(merged["slides_dir"]) if merged.get("slides_dir") else None,
                output_dir=topic_output,
                speaker_mapping=speaker_map,
                auto_images=merged.get("auto_images", True),
                target_duration=merged.get("duration", 300.0),
                style=merged.get("style", "default"),
            )
            results.append({"topic": topic_text, "status": "success", "csv": str(csv_path)})
        except Exception as e:
            results.append({"topic": topic_text, "status": "failed", "error": str(e)})

        # API クォータ管理
        if i < total - 1 and interval > 0:
            import time

            progress_container.progress(
                (i + 1) / total,
                text=f"API クォータ待機中... ({interval}s)",
            )
            time.sleep(interval)

    progress_container.progress(1.0, text="バッチ完了")

    # batch_result.json 書き出し
    result_data = {"batch_name": batch_name, "results": results}
    result_path = base_output / "batch_result.json"
    result_path.write_text(
        json.dumps(result_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "success": True,
        "batch_name": batch_name,
        "result_path": str(result_path),
        "output_dir": str(base_output),
        "results": results,
    }


def _render_results(result: dict[str, Any]) -> None:
    """バッチ結果を表示する。"""
    results = result.get("results", [])
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] == "skipped")

    st.subheader("バッチ結果")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("合計", len(results))
    col2.metric("成功", success)
    col3.metric("失敗", failed)
    col4.metric("スキップ", skipped)

    # トピック別ステータス
    for i, r in enumerate(results):
        status = r.get("status", "unknown")
        icon = {"success": "OK", "failed": "NG", "skipped": "SKIP"}.get(status, "?")
        topic = r.get("topic", "(empty)")

        if status == "success":
            st.success(f"[{icon}] {i + 1}. {topic}")
            if r.get("csv"):
                st.caption(f"  CSV: {r['csv']}")
        elif status == "failed":
            st.error(f"[{icon}] {i + 1}. {topic}")
            if r.get("error"):
                st.caption(f"  Error: {r['error']}")
        else:
            st.info(f"[{icon}] {i + 1}. {topic}")
            if r.get("reason"):
                st.caption(f"  Reason: {r['reason']}")

    # batch_result.json ダウンロード
    result_path = result.get("result_path")
    if result_path and Path(result_path).exists():
        content = Path(result_path).read_text(encoding="utf-8")
        st.download_button(
            "batch_result.json をダウンロード",
            content.encode("utf-8"),
            file_name="batch_result.json",
            mime="application/json",
        )

    # 出力ディレクトリの案内
    output_dir = result.get("output_dir")
    if output_dir:
        st.info(f"出力ディレクトリ: {output_dir}")


def show_batch_queue_page() -> None:
    """バッチ制作キューページを表示する。"""
    st.header("バッチ制作キュー")
    st.markdown(
        "複数トピックをキューに積み、順次パイプライン実行します。"
        "topics.json をアップロードするか、下のフォームで作成してください。"
    )

    # --- セッション初期化 ---
    if "batch_config" not in st.session_state:
        st.session_state.batch_config = _default_batch_config()
    if "batch_running" not in st.session_state:
        st.session_state.batch_running = False
    if "batch_result" not in st.session_state:
        st.session_state.batch_result = None

    # --- 1. 入力方法の選択 ---
    st.subheader("1. トピック設定")

    tab_upload, tab_manual = st.tabs(["ファイルアップロード", "手動入力"])

    with tab_upload:
        uploaded = st.file_uploader(
            "topics.json をアップロード",
            type=["json"],
            help="samples/batch_topics_example.json を参考にしてください",
        )
        if uploaded is not None:
            loaded = _load_topics_from_upload(uploaded)
            if loaded:
                st.session_state.batch_config = loaded
                st.success(
                    f"読み込み完了: {len(loaded.get('topics', []))} トピック"
                )

    with tab_manual:
        config = st.session_state.batch_config

        batch_name = st.text_input(
            "バッチ名",
            value=config.get("batch_name", ""),
            placeholder="2026-03-18_evening",
            help="出力ディレクトリ名に使用",
        )
        config["batch_name"] = batch_name

        # トピック追加ボタン
        if st.button("トピックを追加"):
            config.setdefault("topics", []).append({"topic": ""})

        # トピックリスト
        if config.get("topics"):
            st.markdown("**トピック** (スタイル/尺は空欄で defaults を使用)")
            config["topics"] = _render_topic_list(config["topics"])
        else:
            st.info("「トピックを追加」でトピックを追加してください。")

        st.session_state.batch_config = config

    # --- 2. デフォルト設定 ---
    st.subheader("2. デフォルト設定")
    with st.expander("共通パラメータ", expanded=False):
        st.session_state.batch_config["defaults"] = _render_defaults_editor(
            st.session_state.batch_config
        )

    # --- 3. 実行オプション ---
    st.subheader("3. 実行")
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        output_dir_str = st.text_input(
            "出力ベースディレクトリ",
            value="output_batch",
            help="この下に batch_name/ ディレクトリが作られる",
        )
    with col_opt2:
        interval = st.number_input(
            "トピック間インターバル (秒)",
            min_value=0,
            max_value=300,
            value=30,
            help="API クォータ回避の待機秒数",
        )

    # --- 現在の設定プレビュー ---
    config = st.session_state.batch_config
    topic_count = len([t for t in config.get("topics", []) if t.get("topic", "").strip()])

    with st.expander("設定プレビュー (JSON)"):
        st.json(config)

    st.download_button(
        "topics.json としてダウンロード",
        json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="topics.json",
        mime="application/json",
    )

    # --- 実行ボタン ---
    st.divider()
    can_execute = topic_count > 0 and not st.session_state.batch_running

    if st.button(
        f"バッチ実行 ({topic_count} トピック)",
        type="primary",
        disabled=not can_execute,
    ):
        st.session_state.batch_running = True
        st.session_state.batch_result = None

        progress = st.progress(0.0, text="バッチ開始...")

        try:
            async def _run():
                return await _execute_batch(
                    config=st.session_state.batch_config,
                    output_dir=Path(output_dir_str),
                    interval=int(interval),
                    progress_container=progress,
                )

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    batch_result = pool.submit(asyncio.run, _run()).result()
            else:
                batch_result = asyncio.run(_run())

            st.session_state.batch_result = batch_result

        except Exception as e:
            st.session_state.batch_result = {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
        finally:
            st.session_state.batch_running = False
            st.rerun()

    # --- 実行中表示 ---
    if st.session_state.batch_running:
        st.info("バッチ実行中...")

    # --- 結果表示 ---
    result = st.session_state.batch_result
    if result:
        if result.get("success"):
            _render_results(result)
        else:
            st.error(f"バッチエラー: {result.get('error', '不明')}")
            if result.get("traceback"):
                with st.expander("詳細"):
                    st.code(result["traceback"])

    # --- 既存バッチ結果の閲覧 ---
    st.divider()
    st.subheader("4. 過去のバッチ結果を閲覧")
    result_path_str = st.text_input(
        "batch_result.json パス",
        value="",
        placeholder="output_batch/2026-03-17_evening/batch_result.json",
        help="過去のバッチ結果ファイルを読み込んで表示",
    )
    if result_path_str.strip():
        rp = Path(result_path_str.strip())
        if rp.exists():
            try:
                data = json.loads(rp.read_text(encoding="utf-8"))
                _render_results(
                    {
                        "success": True,
                        "batch_name": data.get("batch_name", ""),
                        "result_path": str(rp),
                        "output_dir": str(rp.parent),
                        "results": data.get("results", []),
                    }
                )
            except (json.JSONDecodeError, KeyError) as e:
                st.error(f"結果ファイルの読み込みに失敗: {e}")
        else:
            st.warning("指定パスが存在しません。")
