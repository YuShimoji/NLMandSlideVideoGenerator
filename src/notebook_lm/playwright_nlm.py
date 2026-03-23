"""
NotebookLM Web UI の Playwright 半自動化 (SP-053 Phase 3)

制作者がNotebookLMでの操作を半自動化するためのヘルパー。
persistent browser contextでGoogle認証を維持し、
ソース投入→Audio Overview生成→ダウンロードを支援する。

使い方:
  1. 初回: launch_browser() でブラウザを開き、手動でGoogleログイン
  2. 以降: persistent contextが認証を維持
  3. create_notebook() / add_source_url() / generate_audio() などを呼ぶ
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional


# Playwright persistent context 用のデフォルトディレクトリ
DEFAULT_USER_DATA_DIR = Path.home() / ".nlm-playwright" / "browser-data"
NLM_BASE_URL = "https://notebooklm.google.com/"


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
        if hasattr(self, '_playwright') and self._playwright:
            await self._playwright.stop()

    @property
    def page(self):
        """現在のページを返す"""
        return self._page

    async def navigate_to_nlm(self) -> None:
        """NotebookLMのトップページに遷移する"""
        if not self._page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        await self._page.goto(NLM_BASE_URL, wait_until="networkidle")

    async def is_logged_in(self) -> bool:
        """Googleにログイン済みかチェックする"""
        if not self._page:
            return False
        try:
            # NLMのメインUIが表示されているかで判定
            await self._page.wait_for_selector(
                'text="New notebook"',
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
        if not self._page:
            raise RuntimeError("Browser not launched. Call launch() first.")

        print("Google アカウントでログインしてください...")
        print(f"(タイムアウト: {timeout // 1000}秒)")

        try:
            await self._page.wait_for_selector(
                'text="New notebook"',
                timeout=timeout,
            )
            print("ログイン確認完了")
            return True
        except Exception:
            print("ログインタイムアウト")
            return False

    async def add_source_url(self, url: str) -> bool:
        """ノートブックにURLソースを追加する

        注意: NLM Web UIの構造は頻繁に変更される。
        セレクタが壊れた場合は手動操作にフォールバックすること。

        Args:
            url: 追加するURL

        Returns:
            成功でTrue
        """
        if not self._page:
            raise RuntimeError("Browser not launched. Call launch() first.")

        try:
            # "Add source" ボタンを探してクリック
            add_btn = self._page.locator('button:has-text("Add source")').first
            await add_btn.click(timeout=5000)

            # URL入力モードを選択
            url_option = self._page.locator('text="Website"').first
            await url_option.click(timeout=5000)

            # URL入力
            url_input = self._page.locator('input[type="url"], input[placeholder*="URL"]').first
            await url_input.fill(url, timeout=5000)

            # 追加ボタン
            submit_btn = self._page.locator('button:has-text("Insert")').first
            await submit_btn.click(timeout=5000)

            # 処理完了を待つ
            await self._page.wait_for_timeout(2000)
            return True

        except Exception as e:
            print(f"URL追加に失敗: {e}")
            print("手動でURLを追加してください。")
            return False

    async def generate_audio_overview(self) -> bool:
        """Audio Overview生成を開始する

        Returns:
            生成開始に成功でTrue
        """
        if not self._page:
            raise RuntimeError("Browser not launched. Call launch() first.")

        try:
            # Audio Overviewセクションを探す
            audio_section = self._page.locator('text="Audio Overview"').first
            await audio_section.scroll_into_view_if_needed()

            # Generateボタンをクリック
            generate_btn = self._page.locator('button:has-text("Generate")').first
            await generate_btn.click(timeout=5000)

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
        if not self._page:
            raise RuntimeError("Browser not launched. Call launch() first.")

        print(f"Audio Overview生成完了を待機中... (タイムアウト: {timeout // 1000}秒)")

        try:
            # ダウンロードボタンまたは再生ボタンが現れるのを待つ
            await self._page.wait_for_selector(
                'button:has-text("Download"), [aria-label*="Download"], [aria-label*="Play"]',
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
        if not self._page:
            raise RuntimeError("Browser not launched. Call launch() first.")

        try:
            # ダウンロードイベントをキャプチャ
            async with self._page.expect_download(timeout=30000) as download_info:
                # ダウンロードボタンをクリック
                dl_btn = self._page.locator(
                    'button:has-text("Download"), [aria-label*="Download"]'
                ).first
                await dl_btn.click(timeout=5000)

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

    async def take_screenshot(self, path: str = "nlm_screenshot.png") -> None:
        """デバッグ用スクリーンショット"""
        if self._page:
            await self._page.screenshot(path=path)
            print(f"スクリーンショット保存: {path}")


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

    nlm = NLMAutomation(download_dir=str(audio_dir))
    try:
        await nlm.launch()
        await nlm.navigate_to_nlm()

        # ログイン確認
        if not await nlm.is_logged_in():
            logged_in = await nlm.wait_for_login()
            if not logged_in:
                print("ログインに失敗しました。")
                return None

        print("NotebookLMにログイン済み。")
        print("手動でノートブックを作成し、ソースを追加してください。")
        print("Audio Overviewが生成されたら、ダウンロードを自動取得します。")

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

    finally:
        await nlm.close()
