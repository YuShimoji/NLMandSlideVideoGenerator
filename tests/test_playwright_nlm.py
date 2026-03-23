"""Playwright NLM半自動化のユニットテスト (SP-047 Phase 3)

実際のブラウザ起動は行わず、NLMAutomationクラスの初期化・設定・
未起動時のエラーハンドリングをテストする。
"""

from pathlib import Path
import pytest

from src.notebook_lm.playwright_nlm import (
    NLMAutomation,
    DEFAULT_USER_DATA_DIR,
    NLM_BASE_URL,
    SELECTORS,
)


class TestNLMAutomation:
    """NLMAutomationの初期化テスト"""

    def test_default_init(self):
        nlm = NLMAutomation()
        assert nlm.user_data_dir == DEFAULT_USER_DATA_DIR
        assert nlm.download_dir == Path("data/downloads")
        assert nlm.headless is False
        assert nlm._context is None
        assert nlm._page is None

    def test_custom_init(self, tmp_path: Path):
        nlm = NLMAutomation(
            user_data_dir=tmp_path / "browser",
            download_dir=tmp_path / "dl",
            headless=True,
        )
        assert nlm.user_data_dir == tmp_path / "browser"
        assert nlm.download_dir == tmp_path / "dl"
        assert nlm.headless is True

    def test_page_property_before_launch(self):
        nlm = NLMAutomation()
        assert nlm.page is None

    def test_nlm_base_url(self):
        assert NLM_BASE_URL == "https://notebooklm.google.com/"

    def test_default_user_data_dir_is_in_home(self):
        assert ".nlm-playwright" in str(DEFAULT_USER_DATA_DIR)


class TestSelectorsConfig:
    """セレクタ定義の整合性テスト"""

    def test_all_required_selectors_present(self):
        required = [
            "logged_in", "new_notebook_btn", "add_source_btn",
            "source_website", "source_text", "source_file",
            "url_input", "text_input", "submit_source",
            "audio_section", "generate_btn", "audio_ready", "download_btn",
        ]
        for key in required:
            assert key in SELECTORS, f"Missing selector: {key}"

    def test_selectors_are_nonempty_strings(self):
        for key, value in SELECTORS.items():
            assert isinstance(value, str), f"{key} is not a string"
            assert len(value) > 0, f"{key} is empty"


class TestRequirePageErrors:
    """未起動時に全メソッドがRuntimeErrorを出すことの確認"""

    @pytest.mark.asyncio
    async def test_navigate_without_launch_raises(self):
        nlm = NLMAutomation()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await nlm.navigate_to_nlm()

    @pytest.mark.asyncio
    async def test_is_logged_in_without_launch(self):
        nlm = NLMAutomation()
        assert await nlm.is_logged_in() is False

    @pytest.mark.asyncio
    async def test_add_source_url_without_launch_raises(self):
        nlm = NLMAutomation()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await nlm.add_source_url("https://example.com")

    @pytest.mark.asyncio
    async def test_add_source_text_without_launch_raises(self):
        nlm = NLMAutomation()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await nlm.add_source_text("some text")

    @pytest.mark.asyncio
    async def test_add_source_file_without_launch_raises(self):
        nlm = NLMAutomation()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await nlm.add_source_file(Path("test.pdf"))

    @pytest.mark.asyncio
    async def test_create_notebook_without_launch_raises(self):
        nlm = NLMAutomation()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await nlm.create_notebook("test")

    @pytest.mark.asyncio
    async def test_generate_audio_without_launch_raises(self):
        nlm = NLMAutomation()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await nlm.generate_audio_overview()

    @pytest.mark.asyncio
    async def test_wait_for_audio_without_launch_raises(self):
        nlm = NLMAutomation()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await nlm.wait_for_audio_ready(timeout=100)

    @pytest.mark.asyncio
    async def test_download_without_launch_raises(self):
        nlm = NLMAutomation()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await nlm.download_audio()


class TestGetPageInfo:
    """get_page_info のテスト"""

    @pytest.mark.asyncio
    async def test_no_page_returns_error(self):
        nlm = NLMAutomation()
        info = await nlm.get_page_info()
        assert info == {"error": "no page"}


class TestCloseIdempotent:
    """close() の冪等性テスト"""

    @pytest.mark.asyncio
    async def test_close_without_launch(self):
        nlm = NLMAutomation()
        # close() を未起動状態で呼んでもエラーにならない
        await nlm.close()
        assert nlm._context is None
        assert nlm._playwright is None

    @pytest.mark.asyncio
    async def test_close_twice(self):
        nlm = NLMAutomation()
        await nlm.close()
        await nlm.close()  # 2回呼んでもエラーにならない
