"""
NotebookLM ベースの Script Provider (SP-047 Phase 2 刷新)

IScriptProvider 実装。
notebooklm_client.py + nlm_script_converter.py を組み合わせて
Study Guide → YMM4 CSV 互換 ScriptInfo を生成する。
"""
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from notebook_lm.notebooklm_client import NotebookLMClient, NLMNotebook
from notebook_lm.nlm_script_converter import NlmScriptConverter
from notebook_lm.source_collector import SourceInfo

from ...interfaces import IScriptProvider

logger = logging.getLogger(__name__)


class NotebookLMScriptProvider(IScriptProvider):
    """
    NotebookLM を利用したスクリプト生成プロバイダ (SP-047 Phase 2)

    フロー:
        sources (URLs) → NLM notebook → Study Guide (text)
        → NlmScriptConverter → ScriptInfo (YMM4 CSV 互換)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        llm_provider: Any = None,
        nlm_output_dir: Optional[Path] = None,
        style: str = "default",
    ):
        self.api_key = api_key or ""
        self._nlm_client = NotebookLMClient(output_dir=nlm_output_dir)
        self._converter = NlmScriptConverter(
            api_key=self.api_key,
            llm_provider=llm_provider,
            style=style,
        )

    async def generate_script(
        self,
        topic: str,
        sources: List[SourceInfo],
        mode: str = "auto",
        target_duration: float = 600.0,
        language: str = "ja",
        style: str = "default",
        speaker_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        NotebookLM Study Guide → ScriptInfo → スクリプトバンドルを生成。

        Args:
            topic: 動画のトピック
            sources: ソース情報リスト
            mode: 生成モード (auto/assist/manual)
            target_duration: 目標尺 (秒)
            language: 言語コード
            style: スクリプトスタイルプリセット名
            speaker_mapping: {"a": "ずんだもん", "b": "四国めたん"} 形式

        Returns:
            スクリプトバンドル (既存パイプラインと互換)
        """
        source_urls = [s.url for s in sources if hasattr(s, "url") and s.url]

        speaker_a = (speaker_mapping or {}).get("a", "ずんだもん")
        speaker_b = (speaker_mapping or {}).get("b", "四国めたん")

        async with self._nlm_client as client:
            # 1. NLM ノートブック作成 + ソース追加
            notebook: NLMNotebook = await client.create_notebook(topic, sources=source_urls)
            logger.info("NLM notebook: %s (%d sources)", notebook.notebook_id, len(source_urls))

            # 2. Study Guide 取得
            study_guide = await client.get_study_guide(notebook)
            logger.info("Study Guide 取得: %d chars", len(study_guide.text))

            # 3. Study Guide → ScriptInfo 変換
            script_info = await self._converter.convert(
                study_guide_text=study_guide.text,
                topic=topic,
                target_duration=target_duration,
                language=language,
                speaker_a=speaker_a,
                speaker_b=speaker_b,
            )

            # 4. クリーンアップ
            await client.delete_notebook(notebook)

        # 既存パイプライン互換のバンドル形式に変換
        return {
            "title": script_info.title,
            "topic": topic,
            "source_count": len(source_urls),
            "total_duration_estimate": script_info.total_duration_estimate,
            "quality_score": script_info.quality_score,
            "language": language,
            "generated_at": script_info.created_at.isoformat(),
            "provider": "notebooklm",
            "segments": script_info.segments,
        }
