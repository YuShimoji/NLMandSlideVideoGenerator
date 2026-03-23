"""Playwright NLM半自動化のユニットテスト (SP-053 Phase 3)

実際のブラウザ起動は行わず、NLMAutomationクラスの初期化と設定をテストする。
"""

from pathlib import Path
import pytest

from src.notebook_lm.playwright_nlm import (
    NLMAutomation,
    DEFAULT_USER_DATA_DIR,
    NLM_BASE_URL,
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
    async def test_add_source_without_launch_raises(self):
        nlm = NLMAutomation()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await nlm.add_source_url("https://example.com")

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
