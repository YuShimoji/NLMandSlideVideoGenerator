"""リサーチ・台本照合ページモジュール"""

import asyncio
import json
import traceback
from pathlib import Path
from io import BytesIO

import streamlit as st

from notebook_lm.research_models import ResearchPackage
from notebook_lm.script_alignment import ScriptAlignmentAnalyzer


def show_research_page():
    """リサーチ・台本照合ページを表示"""
    st.header("🔍 リサーチ・台本照合")
    st.markdown("""
    収集した資料（Research Package）と台本を照合し、根拠の有無や矛盾を確認します。
    確認後、動画制作に使用する最終的なCSVを出力できます。
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. リサーチパッケージの読み込み")
        package_file = st.file_uploader("package.json (ResearchPackage) を選択", type=["json"], key="research_pkg")

    with col2:
        st.subheader("2. 台本の読み込み")
        script_file = st.file_uploader("台本ファイル (txt, csv, json) を選択", type=["txt", "csv", "json"], key="research_script")

    if package_file and script_file:
        try:
            # Load package
            package_data = json.load(package_file)
            package = ResearchPackage.from_dict(package_data)

            # Save temporary script file for ScriptAlignmentAnalyzer
            temp_script_path = Path("temp_script") / script_file.name
            temp_script_path.parent.mkdir(exist_ok=True)
            with open(temp_script_path, "wb") as f:
                f.write(script_file.getbuffer())

            analyzer = ScriptAlignmentAnalyzer()

            async def _run_analysis():
                normalized_script = await analyzer.load_script(temp_script_path)
                return await analyzer.analyze(package, normalized_script)

            with st.spinner("分析中... (LLMセマンティック照合を含む場合、少し時間がかかります)"):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        report = pool.submit(asyncio.run, _run_analysis()).result()
                else:
                    report = asyncio.run(_run_analysis())

            st.divider()
            st.subheader("📊 分析結果サマリー")

            # Summary metrics with colour
            s = report.summary
            total = s.get("total_segments", 0)
            supported = s.get("supported", 0)
            orphaned = s.get("orphaned", 0)
            missing = s.get("missing", 0)
            conflict = s.get("conflict", 0)

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("総セグメント", total)
            m2.metric("✅ 根拠あり", supported)
            m3.metric("⚠️ 根拠なし", orphaned)
            m4.metric("📄 資料のみ", missing)
            m5.metric("❌ 矛盾", conflict)

            if conflict > 0:
                st.error(f"矛盾が {conflict} 件検出されました。該当箇所を確認してください。")
            elif orphaned > 0:
                st.warning(f"根拠のない記述が {orphaned} 件あります。採用/拒否を判断してください。")
            else:
                st.success("すべてのセグメントに根拠が確認されました。")

            # Editable review table
            st.markdown("### 📋 詳細照合リスト")

            if "analysis_results" not in st.session_state or st.session_state.get("last_report_id") != report.report_id:
                st.session_state.analysis_results = report.analysis
                st.session_state.last_report_id = report.report_id

            analysis = st.session_state.analysis_results

            _STATUS_BADGES = {
                "supported": "🟢",
                "orphaned": "🟡",
                "missing": "🔵",
                "conflict": "🔴",
                "adopted": "✅",
                "rejected": "🚫",
            }

            for i, item in enumerate(analysis):
                status = item.get("status", "orphaned")
                text = item.get("text", "")
                speaker = item.get("speaker", "ナレーター")
                badge = _STATUS_BADGES.get(status, "⬜")

                with st.expander(f"{badge} [{status}] {speaker}: {text[:60]}...", expanded=(status not in ("supported", "adopted"))):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"**話者:** {speaker}")
                        st.markdown(f"**内容:** {text}")
                        if item.get("matched_claim"):
                            st.info(f"**根拠:** {item['matched_claim']}\n\n**出典:** {item['matched_source']}")
                        if item.get("suggestion"):
                            st.warning(f"**提案:** {item['suggestion']}")

                    with col_b:
                        if status == "supported":
                            st.success("✅ 根拠あり")
                        elif status == "missing":
                            st.info("📄 資料にのみ存在")
                        else:
                            options = ["保留", "採用 (adopted)", "拒否 (rejected)"]
                            default_index = 0
                            if status == "adopted":
                                default_index = 1
                            elif status == "rejected":
                                default_index = 2
                            choice = st.radio(
                                "判定:", options,
                                key=f"choice_{i}",
                                index=default_index,
                            )
                            if "採用" in choice:
                                item["status"] = "adopted"
                            elif "拒否" in choice:
                                item["status"] = "rejected"
                            else:
                                if status not in ("orphaned", "conflict"):
                                    item["status"] = "orphaned"

            st.divider()

            # CSV export
            st.subheader("📥 最終CSV出力")
            st.markdown("採用/拒否の判定が完了したら、最終CSVを出力できます。`rejected` のセグメントはCSVから除外されます。")

            if st.button("🚀 最終CSVを出力", key="export_final_csv"):
                output_dir = Path("output_csv")
                output_dir.mkdir(exist_ok=True)
                output_path = output_dir / f"final_script_{package.package_id}.csv"

                final_path = analyzer.export_to_csv(analysis, output_path)
                st.success(f"✅ CSVを出力しました: {final_path}")
                with open(final_path, "rb") as f:
                    csv_data = f.read()
                st.download_button(
                    "⬇️ CSVをダウンロード",
                    csv_data,
                    file_name=final_path.name,
                    mime="text/csv",
                )

        except Exception as e:
            st.error(f"エラーが発生しました: {str(e)}")
            st.code(traceback.format_exc())
