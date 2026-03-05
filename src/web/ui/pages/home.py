"""
Home page for Web Application
"""
import streamlit as st

from config.settings import settings
from ._utils import _run_environment_check


def show_home_page():
    """ホームページ表示"""
    # タイトルはweb_app.pyで表示済みなのでここでは省略

    st.markdown("""
    **CSVと音声ファイルから簡単に動画を生成できます**

    YMM4で作成した音声素材を使って、スライド動画を自動生成します。
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
