"""
NotebookLM クライアントラッパー (SP-047 Phase 2)

notebooklm-py ライブラリの非同期 API をラップし、
Study Guide (テキスト) とスライド (PPTX/PDF) を取得するインターフェースを提供する。

notebooklm-py が未インストール / 未ログインの場合は MockNLMClient にフォールバック。
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# notebooklm-py の存在確認
try:
    from notebooklm import NotebookLMClient as _NLMLib  # type: ignore
    _NLM_AVAILABLE = True
except ImportError:
    _NLM_AVAILABLE = False
    logger.warning("notebooklm-py が未インストールです。MockNLMClient を使用します。")


@dataclass
class NLMStudyGuide:
    """Study Guide の取得結果"""
    text: str
    notebook_id: str
    source_count: int


@dataclass
class NLMSlides:
    """スライド生成の取得結果"""
    file_path: Path
    format: str  # "pptx" or "pdf"
    notebook_id: str


@dataclass
class NLMNotebook:
    """ノートブック情報"""
    notebook_id: str
    title: str
    source_urls: list[str] = field(default_factory=list)


class NotebookLMClient:
    """
    notebooklm-py ラッパー。

    使用例:
        client = NotebookLMClient()
        async with client:
            notebook = await client.create_notebook("AIニュース", sources=["https://..."])
            guide = await client.get_study_guide(notebook)
            slides = await client.get_slides(notebook, output_dir=Path("output"))
            await client.delete_notebook(notebook)
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self._output_dir = output_dir or Path("temp_nlm")
        self._client: Optional[object] = None

    async def __aenter__(self) -> "NotebookLMClient":
        if _NLM_AVAILABLE:
            self._client = await _NLMLib.from_storage().__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client is not None:
            await self._client.__aexit__(*args)
            self._client = None

    @property
    def is_available(self) -> bool:
        return _NLM_AVAILABLE and self._client is not None

    async def create_notebook(
        self, title: str, sources: list[str]
    ) -> NLMNotebook:
        """
        ノートブックを作成し、URL ソースを追加する。

        Args:
            title: ノートブック名
            sources: URL のリスト (最大 50 件推奨)

        Returns:
            NLMNotebook
        """
        if not self.is_available:
            logger.info("[MockNLM] create_notebook: %s (%d sources)", title, len(sources))
            return NLMNotebook(notebook_id="mock-nb-001", title=title, source_urls=sources)

        nb = await self._client.notebooks.create(title)
        for url in sources:
            try:
                await self._client.sources.add_url(nb.id, url, wait=True)
            except Exception as exc:
                logger.warning("ソース追加失敗 (%s): %s", url, exc)

        return NLMNotebook(notebook_id=nb.id, title=title, source_urls=sources)

    async def get_study_guide(self, notebook: NLMNotebook) -> NLMStudyGuide:
        """
        Study Guide をテキストとして取得する。

        notebooklm-py のレポート生成 (generate_report) を使用し、
        "study_guide" フォーマットで Markdown テキストを返す。

        Returns:
            NLMStudyGuide (text フィールドに Markdown)
        """
        if not self.is_available:
            mock_text = self._mock_study_guide(notebook.title)
            logger.info("[MockNLM] get_study_guide: %s (%d chars)", notebook.title, len(mock_text))
            return NLMStudyGuide(
                text=mock_text,
                notebook_id=notebook.notebook_id,
                source_count=len(notebook.source_urls),
            )

        # notebooklm-py: generate_report は "briefing_doc" / "study_guide" / "blog_post" を選択可
        try:
            status = await self._client.artifacts.generate_report(
                notebook.notebook_id, format="study_guide"
            )
            await self._client.artifacts.wait_for_completion(
                notebook.notebook_id, status.task_id
            )
            # テキストとして取得 (download_report は Markdown を返す想定)
            text = await self._client.artifacts.download_report(
                notebook.notebook_id, output_format="markdown"
            )
        except AttributeError:
            # API メソッド名が異なる場合のフォールバック: chat で要約取得
            logger.warning("generate_report が未実装。chat.ask でフォールバック取得します。")
            result = await self._client.chat.ask(
                notebook.notebook_id,
                "このノートブックの内容をスタディガイド形式でMarkdownにまとめてください。"
                "主要な概念、重要な事実、関連性を含めてください。",
            )
            text = result.answer

        return NLMStudyGuide(
            text=text,
            notebook_id=notebook.notebook_id,
            source_count=len(notebook.source_urls),
        )

    async def get_slides(
        self,
        notebook: NLMNotebook,
        output_dir: Optional[Path] = None,
        fmt: str = "pptx",
    ) -> NLMSlides:
        """
        スライドデッキを生成してローカルに保存する。

        Args:
            notebook: 対象ノートブック
            output_dir: 保存先ディレクトリ
            fmt: "pptx" または "pdf"

        Returns:
            NLMSlides (file_path に保存済みファイルパス)
        """
        out_dir = output_dir or self._output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{notebook.notebook_id}_slides.{fmt}"

        if not self.is_available:
            logger.info("[MockNLM] get_slides: %s → %s (mock, not created)", notebook.title, out_path)
            return NLMSlides(file_path=out_path, format=fmt, notebook_id=notebook.notebook_id)

        try:
            status = await self._client.artifacts.generate_slide_deck(notebook.notebook_id)
            await self._client.artifacts.wait_for_completion(
                notebook.notebook_id, status.task_id
            )
            await self._client.artifacts.download_slide_deck(
                notebook.notebook_id, str(out_path), output_format=fmt
            )
        except AttributeError as exc:
            logger.warning("generate_slide_deck が未実装: %s", exc)
            # スライド未取得の場合は空ファイルパスを返す
            return NLMSlides(file_path=Path(""), format=fmt, notebook_id=notebook.notebook_id)

        return NLMSlides(file_path=out_path, format=fmt, notebook_id=notebook.notebook_id)

    async def delete_notebook(self, notebook: NLMNotebook) -> None:
        """ノートブックを削除してリソースを解放する。"""
        if not self.is_available:
            logger.info("[MockNLM] delete_notebook: %s", notebook.notebook_id)
            return
        try:
            await self._client.notebooks.delete(notebook.notebook_id)
        except Exception as exc:
            logger.warning("ノートブック削除失敗 (%s): %s", notebook.notebook_id, exc)

    # ------------------------------------------------------------------
    # Mock helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mock_study_guide(title: str) -> str:
        """テスト用モック Study Guide テキストを返す。"""
        return f"""# {title} — スタディガイド (Mock)

## 概要

このトピックは現代社会において重要な意味を持ちます。
関連する複数のソースから得られた知識を統合して解説します。

## 主要な概念

### 1. 背景と経緯

近年、この分野では急速な変化が起きています。
専門家たちは新しいアプローチを模索しており、様々な観点からの分析が必要です。

### 2. 現状の課題

主な課題として以下の点が挙げられます:
- 技術的な制約と可能性のバランス
- 社会的影響と倫理的考慮
- 経済的インパクトと持続可能性

### 3. 今後の展望

専門家の多くは楽観的な見通しを持っており、
適切な対策によって課題の大部分は解決可能と考えられています。

## まとめ

このトピックを理解するためには複合的な視点が必要です。
引き続き最新情報を追いながら、批判的思考で分析することが重要です。
"""


def create_client(output_dir: Optional[Path] = None) -> NotebookLMClient:
    """NotebookLMClient のファクトリ関数。"""
    return NotebookLMClient(output_dir=output_dir)
