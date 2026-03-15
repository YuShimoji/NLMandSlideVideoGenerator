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

    # --- 実行ボタン ---
    if "mp_running" not in st.session_state:
        st.session_state.mp_running = False
    if "mp_result" not in st.session_state:
        st.session_state.mp_result = None

    st.divider()

    if st.button(
        "パイプライン実行",
        type="primary",
        disabled=st.session_state.mp_running or not topic.strip(),
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

        progress_area = st.empty()
        status_area = st.empty()

        async def _execute():
            from scripts.research_cli import run_pipeline

            return await run_pipeline(
                topic=topic,
                urls=urls,
                max_sources=max_sources,
                auto_review=auto_review,
                slides_dir=slides_dir,
                speaker_mapping=speaker_mapping,
                auto_images=auto_images,
                target_duration=target_duration * 60.0,
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
                        csv_path = pool.submit(asyncio.run, _execute()).result()
                else:
                    csv_path = asyncio.run(_execute())

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
                    lines = [l for l in csv_content.strip().split("\n") if l]
                    st.metric("CSV行数", len(lines))

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
                                    use_container_width=True,
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
