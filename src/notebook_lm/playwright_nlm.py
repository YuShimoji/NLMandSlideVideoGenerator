"""
NotebookLM Web UI の Playwright 半自動化 (SP-047 Phase 3)

制作者がNotebookLMでの操作を半自動化するためのヘルパー。
persistent browser contextでGoogle認証を維持し、
ソース投入→Audio Overview生成→ダウンロード→テキスト化を支援する。

根本ワークフロー (DESIGN_FOUNDATIONS.md Section 0):
  NLMソース投入 → Audio Overview生成 → 音声DL
  → (SP-051 AudioTranscriber で自動テキスト化、または NLM 再投入でテキスト化)

使い方:
  async with NLMAutomation() as nlm:
      await nlm.navigate_to_nlm()
      if not await nlm.is_logged_in():
          await nlm.wait_for_login()
      nb_url = await nlm.create_notebook("AI動向")
      await nlm.add_source_url("https://example.com/article")
      await nlm.generate_audio_overview()
      await nlm.wait_for_audio_ready()
      audio_path = await nlm.download_audio()
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Playwright persistent context 用のデフォルトディレクトリ
DEFAULT_USER_DATA_DIR = Path.home() / ".nlm-playwright" / "browser-data"
NLM_BASE_URL = "https://notebooklm.google.com/"

# セレクタ定義: UIが変わった場合はここを修正する
# 複数候補をカンマ区切りで定義し、最初にマッチしたものを使う
SELECTORS = {
    # ログイン判定: NLMメインUI到達の証拠
    "logged_in": 'text="New notebook", button:has-text("New notebook"), [aria-label="Create new notebook"]',
    # ノートブック作成
    "new_notebook_btn": 'button:has-text("New notebook"), [aria-label="Create new notebook"], text="New notebook"',
    # ソース追加
    "add_source_btn": 'button:has-text("Add source"), [aria-label="Add source"], button:has-text("Add")',
    "source_website": 'text="Website", [data-value="website"], button:has-text("Website")',
    "source_text": 'text="Copied text", text="Text", [data-value="text"], button:has-text("Text")',
    "source_file": 'text="Upload", [data-value="upload"], button:has-text("Upload")',
    "url_input": 'input[type="url"], input[placeholder*="URL"], input[placeholder*="url"]',
    "text_input": 'textarea, [contenteditable="true"]',
    "submit_source": 'button:has-text("Insert"), button:has-text("Add"), button:has-text("Submit")',
    # Audio Overview
    "audio_section": 'text="Audio Overview", [data-section="audio"]',
    "generate_btn": 'button:has-text("Generate"), button:has-text("Create")',
    "audio_ready": 'button:has-text("Download"), [aria-label*="Download"], [aria-label*="Play"], button:has-text("Play")',
    "download_btn": 'button:has-text("Download"), [aria-label*="Download"]',
}

# 各操作のデフォルトタイムアウト (ms)
DEFAULT_ACTION_TIMEOUT = 8000
DEFAULT_NAV_TIMEOUT = 15000


class NLMAutomation:
    """NotebookLM Web UIのPlaywright半自動化クラス"""

    def __init__(
        self,
        user_data_dir: Path | str = DEFAULT_USER_DATA_DIR,
        download_dir: Path | str = "data/downloads",
        headless: bool = False,
    ):
        self.user_data_dir = Path(user_data_dir)
        self.download_dir = Path(download_dir)
        self.headless = headless
        self._context = None
        self._page = None
        self._playwright = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "NLMAutomation":
        await self.launch()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def launch(self) -> None:
        """Playwrightブラウザを起動する (persistent context)"""
        from playwright.async_api import async_playwright

        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=self.headless,
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        # 既存のページがあればそれを使う、なければ新しく開く
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

    async def close(self) -> None:
        """ブラウザを閉じる"""
        if self._context:
            await self._context.close()
            self._context = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    @property
    def page(self):
        """現在のページを返す"""
        return self._page

    def _require_page(self) -> None:
        """ページが起動済みであることを確認"""
        if not self._page:
            raise RuntimeError("Browser not launched. Call launch() first.")

    # ------------------------------------------------------------------
    # Navigation & Auth
    # ------------------------------------------------------------------

    async def navigate_to_nlm(self) -> None:
        """NotebookLMのトップページに遷移する"""
        self._require_page()
        await self._page.goto(NLM_BASE_URL, wait_until="networkidle", timeout=DEFAULT_NAV_TIMEOUT)

    async def is_logged_in(self) -> bool:
        """Googleにログイン済みかチェックする"""
        if not self._page:
            return False
        try:
            await self._page.wait_for_selector(
                SELECTORS["logged_in"],
                timeout=5000,
            )
            return True
        except Exception:
            return False

    async def wait_for_login(self, timeout: int = 120000) -> bool:
        """ユーザーが手動ログインするのを待つ

        Args:
            timeout: 待機タイムアウト(ms)。デフォルト2分。

        Returns:
            ログイン成功でTrue
        """
        self._require_page()

        print("Google アカウントでログインしてください...")
        print(f"(タイムアウト: {timeout // 1000}秒)")

        try:
            await self._page.wait_for_selector(
                SELECTORS["logged_in"],
                timeout=timeout,
            )
            print("ログイン確認完了")
            return True
        except Exception:
            print("ログインタイムアウト")
            return False

    # ------------------------------------------------------------------
    # Notebook operations
    # ------------------------------------------------------------------

    async def create_notebook(self, title: str = "") -> Optional[str]:
        """新しいノートブックを作成する

        Args:
            title: ノートブック名 (省略時はNLMデフォルト)

        Returns:
            作成されたノートブックのURL。失敗時はNone。
        """
        self._require_page()

        try:
            btn = self._page.locator(SELECTORS["new_notebook_btn"]).first
            await btn.click(timeout=DEFAULT_ACTION_TIMEOUT)

            # ノートブック画面への遷移を待機
            await self._page.wait_for_url("**/notebook/**", timeout=DEFAULT_NAV_TIMEOUT)

            if title:
                await self._try_set_notebook_title(title)

            current_url = self._page.url
            logger.info("Notebook created: %s", current_url)
            print(f"ノートブック作成完了: {current_url}")
            return current_url

        except Exception as e:
            print(f"ノートブック作成に失敗: {e}")
            print("手動で「New notebook」をクリックしてください。")
            return None

    async def _try_set_notebook_title(self, title: str) -> None:
        """ノートブックタイトルの設定を試みる (失敗しても続行)"""
        try:
            title_el = self._page.locator(
                '[contenteditable="true"], input[aria-label*="title"], '
                'input[placeholder*="Untitled"]'
            ).first
            await title_el.click(timeout=3000)
            await title_el.fill(title)
            # フォーカスを外して確定
            await self._page.keyboard.press("Tab")
        except Exception:
            logger.debug("Notebook title setting skipped (element not found)")

    # ------------------------------------------------------------------
    # Source management
    # ------------------------------------------------------------------

    async def add_source_url(self, url: str) -> bool:
        """ノートブックにURLソースを追加する

        注意: NLM Web UIの構造は頻繁に変更される。
        セレクタが壊れた場合は手動操作にフォールバックすること。

        Args:
            url: 追加するURL

        Returns:
            成功でTrue
        """
        self._require_page()

        try:
            # "Add source" ボタンを探してクリック
            add_btn = self._page.locator(SELECTORS["add_source_btn"]).first
            await add_btn.click(timeout=DEFAULT_ACTION_TIMEOUT)

            # URL入力モードを選択
            url_option = self._page.locator(SELECTORS["source_website"]).first
            await url_option.click(timeout=DEFAULT_ACTION_TIMEOUT)

            # URL入力
            url_input = self._page.locator(SELECTORS["url_input"]).first
            await url_input.fill(url, timeout=DEFAULT_ACTION_TIMEOUT)

            # 追加ボタン
            submit_btn = self._page.locator(SELECTORS["submit_source"]).first
            await submit_btn.click(timeout=DEFAULT_ACTION_TIMEOUT)

            # 処理完了を待つ
            await self._page.wait_for_timeout(3000)
            logger.info("URL source added: %s", url)
            return True

        except Exception as e:
            print(f"URL追加に失敗: {e}")
            print("手動でURLを追加してください。")
            return False

    async def add_source_text(self, text: str, title: str = "") -> bool:
        """ノートブックにテキストソースを追加する

        Args:
            text: 追加するテキスト
            title: ソースタイトル (オプション)

        Returns:
            成功でTrue
        """
        self._require_page()

        try:
            add_btn = self._page.locator(SELECTORS["add_source_btn"]).first
            await add_btn.click(timeout=DEFAULT_ACTION_TIMEOUT)

            # テキスト入力モードを選択
            text_option = self._page.locator(SELECTORS["source_text"]).first
            await text_option.click(timeout=DEFAULT_ACTION_TIMEOUT)

            # テキスト入力欄
            text_input = self._page.locator(SELECTORS["text_input"]).first
            await text_input.fill(text, timeout=DEFAULT_ACTION_TIMEOUT)

            # 追加ボタン
            submit_btn = self._page.locator(SELECTORS["submit_source"]).first
            await submit_btn.click(timeout=DEFAULT_ACTION_TIMEOUT)

            await self._page.wait_for_timeout(3000)
            logger.info("Text source added: %d chars", len(text))
            return True

        except Exception as e:
            print(f"テキスト追加に失敗: {e}")
            print("手動でテキストを追加してください。")
            return False

    async def add_source_file(self, file_path: Path) -> bool:
        """ノートブックにファイルソースをアップロードする

        Args:
            file_path: アップロードするファイルパス (PDF/DOCX/音声等)

        Returns:
            成功でTrue
        """
        self._require_page()
        file_path = Path(file_path)

        if not file_path.exists():
            print(f"ファイルが見つかりません: {file_path}")
            return False

        try:
            add_btn = self._page.locator(SELECTORS["add_source_btn"]).first
            await add_btn.click(timeout=DEFAULT_ACTION_TIMEOUT)

            # ファイルアップロードモードを選択
            file_option = self._page.locator(SELECTORS["source_file"]).first
            await file_option.click(timeout=DEFAULT_ACTION_TIMEOUT)

            # ファイル選択ダイアログ
            async with self._page.expect_file_chooser(timeout=DEFAULT_ACTION_TIMEOUT) as fc_info:
                # アップロードエリアをクリック
                upload_area = self._page.locator(
                    'button:has-text("Browse"), [role="button"]:has-text("Upload"), '
                    'input[type="file"]'
                ).first
                await upload_area.click(timeout=DEFAULT_ACTION_TIMEOUT)

            file_chooser = await fc_info.value
            await file_chooser.set_files(str(file_path))

            # 処理完了を待つ
            await self._page.wait_for_timeout(5000)
            logger.info("File source uploaded: %s", file_path.name)
            return True

        except Exception as e:
            print(f"ファイルアップロードに失敗: {e}")
            print(f"手動で {file_path.name} をアップロードしてください。")
            return False

    # ------------------------------------------------------------------
    # Audio Overview
    # ------------------------------------------------------------------

    async def generate_audio_overview(self) -> bool:
        """Audio Overview生成を開始する

        Returns:
            生成開始に成功でTrue
        """
        self._require_page()

        try:
            # Audio Overviewセクションを探す
            audio_section = self._page.locator(SELECTORS["audio_section"]).first
            await audio_section.scroll_into_view_if_needed()

            # Generateボタンをクリック
            generate_btn = self._page.locator(SELECTORS["generate_btn"]).first
            await generate_btn.click(timeout=DEFAULT_ACTION_TIMEOUT)

            print("Audio Overview生成を開始しました。完了まで数分かかります。")
            return True

        except Exception as e:
            print(f"Audio Overview生成の開始に失敗: {e}")
            print("手動で「Generate」ボタンをクリックしてください。")
            return False

    async def wait_for_audio_ready(self, timeout: int = 600000) -> bool:
        """Audio Overview生成の完了を待つ

        Args:
            timeout: 待機タイムアウト(ms)。デフォルト10分。

        Returns:
            完了でTrue
        """
        self._require_page()

        print(f"Audio Overview生成完了を待機中... (タイムアウト: {timeout // 1000}秒)")

        try:
            await self._page.wait_for_selector(
                SELECTORS["audio_ready"],
                timeout=timeout,
                state="visible",
            )
            print("Audio Overview生成完了")
            return True

        except Exception:
            print("Audio Overview生成のタイムアウトまたはエラー")
            return False

    async def download_audio(self, save_path: Optional[Path] = None) -> Optional[Path]:
        """生成されたAudio Overviewをダウンロードする

        Args:
            save_path: 保存先パス。Noneの場合はdownload_dir内に保存。

        Returns:
            ダウンロードしたファイルパス。失敗時はNone。
        """
        self._require_page()

        try:
            async with self._page.expect_download(timeout=30000) as download_info:
                dl_btn = self._page.locator(SELECTORS["download_btn"]).first
                await dl_btn.click(timeout=DEFAULT_ACTION_TIMEOUT)

            download = await download_info.value

            if save_path:
                target = Path(save_path)
            else:
                target = self.download_dir / (download.suggested_filename or "audio_overview.mp3")

            target.parent.mkdir(parents=True, exist_ok=True)
            await download.save_as(str(target))

            print(f"音声ファイルをダウンロード: {target}")
            return target

        except Exception as e:
            print(f"ダウンロードに失敗: {e}")
            print("手動でダウンロードしてください。")
            return None

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    async def take_screenshot(self, path: str = "nlm_screenshot.png") -> None:
        """デバッグ用スクリーンショット"""
        if self._page:
            await self._page.screenshot(path=path)
            print(f"スクリーンショット保存: {path}")

    async def get_page_info(self) -> dict:
        """現在のページ情報を返す (デバッグ用)"""
        if not self._page:
            return {"error": "no page"}
        return {
            "url": self._page.url,
            "title": await self._page.title(),
        }


# ------------------------------------------------------------------
# Quick session (便利関数)
# ------------------------------------------------------------------

async def quick_session(
    topic_dir: str,
    urls: list[str] | None = None,
) -> Optional[Path]:
    """クイックセッション: NLMを開いてAudio Overviewをダウンロードするまでの一気通貫

    ブラウザを開き、ユーザーの手動操作を待ちながら進める半自動フロー。

    Args:
        topic_dir: トピックディレクトリ (data/topics/{topic_id}/)
        urls: ソースURLリスト

    Returns:
        ダウンロードした音声ファイルのパス
    """
    topic_path = Path(topic_dir)
    audio_dir = topic_path / "audio"

    async with NLMAutomation(download_dir=str(audio_dir)) as nlm:
        await nlm.navigate_to_nlm()

        # ログイン確認
        if not await nlm.is_logged_in():
            logged_in = await nlm.wait_for_login()
            if not logged_in:
                print("ログインに失敗しました。")
                return None

        print("NotebookLMにログイン済み。")

        # ノートブック作成
        nb_url = await nlm.create_notebook()
        if not nb_url:
            print("ノートブック作成に失敗。手動で作成してください。")

        # URL追加を試みる (オプション)
        if urls:
            for url in urls:
                print(f"  URL追加試行: {url}")
                await nlm.add_source_url(url)

        # Audio Overview完了を待つ
        print("\nAudio Overviewの生成完了を待機しています...")
        print("(ブラウザでAudio Overviewを生成してください)")

        if await nlm.wait_for_audio_ready(timeout=900000):  # 15分
            audio_path = await nlm.download_audio()
            return audio_path
        else:
            print("タイムアウトしました。手動でダウンロードしてください。")
            return None
