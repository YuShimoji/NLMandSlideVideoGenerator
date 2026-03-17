"""
素材パイプラインページ (SP-032 Phase D)

トピック入力 → collect → script gen → align → review → CsvAssembler の一気通貫UI。
"""
import asyncio
import json
import traceback
from pathlib import Path

import streamlit as st


def show_material_pipeline_page():
    """素材パイプラインページを表示"""
    st.header("素材パイプライン")
    st.markdown(
        "トピックを入力するだけで、資料収集→台本生成→照合→レビュー→CSV出力まで一気通貫で実行します。"
    )

    # --- 入力セクション ---
    st.subheader("1. パラメータ設定")

    col1, col2 = st.columns(2)

    with col1:
        topic = st.text_input(
            "トピック",
            value="",
            placeholder="例: 量子コンピュータの最新動向2026",
            help="調査・台本生成の対象トピック",
        )
        urls_text = st.text_area(
            "シードURL (任意)",
            height=80,
            placeholder="https://example.com/article1\nhttps://example.com/article2",
            help="1行に1つずつ。指定しない場合はWeb検索のみ",
        )

    with col2:
        max_sources = st.number_input(
            "最大ソース数",
            min_value=1,
            max_value=20,
            value=5,
            help="収集する資料の上限",
        )
        auto_review = st.checkbox(
            "自動レビュー",
            value=True,
            help="supported→adopted、それ以外→rejected に自動判定。OFFの場合は照合結果をページ内でレビュー",
        )

    # --- スライド・話者マッピング (オプション) ---
    with st.expander("詳細オプション"):
        col_a, col_b = st.columns(2)

        with col_a:
            slides_dir_str = st.text_input(
                "スライドPNGディレクトリ (任意)",
                value="",
                placeholder="C:\\slides\\my_topic",
                help="指定するとCsvAssemblerが画像パスをCSVに組み込む",
            )
            auto_images = st.checkbox(
                "ストック画像で背景を充実化",
                value=False,
                help="Pexels/Pixabay APIからトピックに合った画像を自動取得し、テキストスライドと交互に配置",
            )

        with col_b:
            speaker_map_str = st.text_input(
                "話者マッピング JSON (任意)",
                value='',
                placeholder='{"Host1":"れいむ","Host2":"まりさ"}',
                help="台本上の話者名→YMM4ボイス名の変換",
            )
            target_duration = st.number_input(
                "目標動画尺 (分)",
                min_value=1,
                max_value=120,
                value=5,
                help="台本生成時の目標尺",
            )

        # テンプレート選択
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
        from core.style_template import StyleTemplateManager
        _tmpl_mgr = StyleTemplateManager()
        _tmpl_mgr.load_all()
        _tmpl_names = _tmpl_mgr.list_templates() or ["default"]
        selected_template = st.selectbox(
            "スタイルテンプレート",
            _tmpl_names,
            index=0,
            help="字幕・アニメーション・タイミングのプリセット",
        )

        # 台本スタイルプリセット (SP-036)
        from notebook_lm.gemini_integration import GeminiIntegration
        _gi = GeminiIntegration.__new__(GeminiIntegration)
        _script_presets = _gi.list_presets()
        _preset_names = [p["name"] for p in _script_presets] if _script_presets else ["default"]
        selected_script_style = st.selectbox(
            "台本スタイル",
            _preset_names,
            index=0,
            help="Geminiプロンプトのスタイルプリセット (ニュース/解説/まとめ等)",
        )

    # --- 再開機能 ---
    with st.expander("途中再開 (Resume)"):
        resume_dir_str = st.text_input(
            "再開するwork_dirパス",
            value="",
            placeholder="data/research/rp_20260316_120000",
            help="以前中断したパイプラインのwork_dirを指定して途中から再開",
        )
        if resume_dir_str.strip():
            resume_path = Path(resume_dir_str.strip())
            state_file = resume_path / "pipeline_state.json"
            if state_file.exists():
                import sys
                sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
                from core.pipeline_state import PipelineState
                prev_state = PipelineState.load(resume_path)
                st.info(f"トピック: {prev_state.topic}")
                first = prev_state.first_incomplete_step()
                st.info(f"再開ポイント: {first or '全完了'}")
                st.code(prev_state.summary())
            elif resume_path.exists():
                st.warning("pipeline_state.json が見つかりません（古い形式のwork_dir）")
            else:
                st.error("指定パスが存在しません")

    # --- 実行ボタン ---
    if "mp_running" not in st.session_state:
        st.session_state.mp_running = False
    if "mp_result" not in st.session_state:
        st.session_state.mp_result = None

    st.divider()

    resume_dir = Path(resume_dir_str.strip()) if resume_dir_str.strip() else None
    can_execute = (topic.strip() or resume_dir) and not st.session_state.mp_running

    if st.button(
        "パイプライン再開" if resume_dir else "パイプライン実行",
        type="primary",
        disabled=not can_execute,
    ):
        st.session_state.mp_running = True
        st.session_state.mp_result = None

        urls = [u.strip() for u in urls_text.split("\n") if u.strip()] or None
        slides_dir = Path(slides_dir_str) if slides_dir_str.strip() else None
        speaker_mapping = None
        if speaker_map_str.strip():
            try:
                speaker_mapping = json.loads(speaker_map_str)
            except json.JSONDecodeError:
                st.error("話者マッピングのJSON形式が不正です。")
                st.session_state.mp_running = False
                return

        async def _execute():
            from scripts.research_cli import run_pipeline

            return await run_pipeline(
                topic=topic,
                urls=urls,
                max_sources=int(max_sources),
                auto_review=auto_review,
                slides_dir=slides_dir,
                speaker_mapping=speaker_mapping,
                auto_images=auto_images,
                target_duration=target_duration * 60.0,
                resume_dir=resume_dir,
                style=selected_script_style,
            )

        try:
            with st.spinner("パイプライン実行中..."):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        csv_path: Path = pool.submit(asyncio.run, _execute()).result()  # type: ignore[assignment]
                else:
                    csv_path = asyncio.run(_execute())  # type: ignore[assignment]

            st.session_state.mp_result = {
                "success": True,
                "csv_path": str(csv_path),
            }

        except Exception as e:
            st.session_state.mp_result = {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

        finally:
            st.session_state.mp_running = False
            st.rerun()

    # --- 実行中表示 ---
    if st.session_state.mp_running:
        st.info("パイプライン実行中...")

    # --- 結果表示 ---
    result = st.session_state.mp_result
    if result:
        if result.get("success"):
            csv_path = Path(result["csv_path"])
            st.success(f"パイプライン完了: {csv_path.name}")

            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.metric("出力ファイル", csv_path.name)
                st.text(f"パス: {csv_path}")

            with col_r2:
                if csv_path.exists():
                    csv_content = csv_path.read_text(encoding="utf-8")
                    lines = [line for line in csv_content.strip().split("\n") if line]
                    st.metric("CSV行数", len(lines))

            # Pre-Export 検証
            if csv_path.exists():
                from core.export_validator import ExportValidator
                _validator = ExportValidator(check_image_exists=True)
                _vresult = _validator.validate_csv(csv_path)
                if _vresult.passed:
                    st.success(f"Pre-Export検証: PASS ({_vresult.warning_count} warnings)")
                else:
                    st.error(f"Pre-Export検証: FAIL ({_vresult.error_count} errors, {_vresult.warning_count} warnings)")
                if _vresult.issues:
                    with st.expander(f"検証結果詳細 ({len(_vresult.issues)}件)"):
                        for _issue in _vresult.issues:
                            _icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}[_issue.severity.value]
                            _row_info = f" (row {_issue.row})" if _issue.row else ""
                            st.text(f"{_icon} {_issue.code}{_row_info}: {_issue.message}")

            # CSVプレビュー
            if csv_path.exists():
                st.subheader("2. CSVプレビュー")
                csv_text = csv_path.read_text(encoding="utf-8")
                st.code(csv_text[:2000], language="csv")

                # ダウンロードボタン
                st.download_button(
                    "CSVをダウンロード",
                    csv_text.encode("utf-8"),
                    file_name=csv_path.name,
                    mime="text/csv",
                )

            # 作業ディレクトリ内の生成物
            work_dir = csv_path.parent
            st.subheader("3. 生成物一覧")
            artifacts = list(work_dir.glob("*"))
            if artifacts:
                for art in sorted(artifacts):
                    if art.is_dir():
                        continue
                    icon = "📄"
                    if art.suffix == ".json":
                        icon = "📋"
                    elif art.suffix == ".csv":
                        icon = "📊"
                    elif art.suffix == ".txt":
                        icon = "📝"
                    st.text(f"  {icon} {art.name}")

            # --- 画像ギャラリー ---
            stock_dir = work_dir / "stock_images"
            if stock_dir.exists():
                image_files = sorted(stock_dir.glob("*.jpg")) + sorted(stock_dir.glob("*.png"))
                if image_files:
                    st.subheader("4. 収集画像ギャラリー")
                    st.caption(f"{len(image_files)} 枚の画像を収集済み")

                    cols_per_row = 3
                    for row_start in range(0, len(image_files), cols_per_row):
                        cols = st.columns(cols_per_row)
                        for col_idx, img_path in enumerate(
                            image_files[row_start : row_start + cols_per_row]
                        ):
                            with cols[col_idx]:
                                st.image(
                                    str(img_path),
                                    caption=img_path.stem[:30],
                                    use_container_width=True,  # type: ignore[call-arg]
                                )

            # --- クレジット表示 ---
            credits_path = work_dir / "image_credits.txt"
            if credits_path.exists():
                credits_text = credits_path.read_text(encoding="utf-8")
                if credits_text.strip():
                    st.subheader("5. 画像クレジット")
                    st.text(credits_text)
                    st.download_button(
                        "クレジットをダウンロード",
                        credits_text.encode("utf-8"),
                        file_name="image_credits.txt",
                        mime="text/plain",
                    )

            # --- 台本プレビュー ---
            script_path = work_dir / "generated_script.json"
            if script_path.exists():
                with st.expander("台本プレビュー (JSON)"):
                    script_data = json.loads(script_path.read_text(encoding="utf-8"))
                    st.json(script_data)

        else:
            st.error(f"パイプラインエラー: {result.get('error', '不明')}")
            if result.get("traceback"):
                with st.expander("詳細"):
                    st.code(result["traceback"])
