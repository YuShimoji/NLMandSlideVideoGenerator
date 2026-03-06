import streamlit as st
import asyncio


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
                    progress_callback=lambda message: progress_placeholder.info(message)  # type: ignore[arg-type]
                )
                result_placeholder.json(results)
            except (ImportError, AttributeError, TypeError, ValueError, RuntimeError, OSError) as e:
                result_placeholder.error(f"テスト実行中にエラーが発生しました: {str(e)}")
            except Exception as e:
                result_placeholder.error(f"テスト実行中にエラーが発生しました: {str(e)}")

        asyncio.run(execute_tests())
