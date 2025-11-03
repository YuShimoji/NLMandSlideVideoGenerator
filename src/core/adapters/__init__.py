"""
コンテンツアダプター
NotebookLM DeepDive などの固有フォーマットを内部スキーマへ変換
"""
from typing import Dict, Any
from pathlib import Path
import json
import logging

from ..interfaces import IContentAdapter

logger = logging.getLogger(__name__)


class NotebookLMContentAdapter(IContentAdapter):
    """NotebookLM DeepDive フォーマットを内部スキーマに変換"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def normalize_script(self, raw_script: Dict[str, Any]) -> Dict[str, Any]:
        """
        NotebookLM DeepDive フォーマットを正規化

        Args:
            raw_script: 元のスクリプトデータ

        Returns:
            Dict[str, Any]: 正規化されたスクリプト
        """
        # DeepDive 特有の構造を検出
        if self._is_deep_dive_format(raw_script):
            return self._normalize_deep_dive(raw_script)
        else:
            # 既に正規化されている場合や他のフォーマット
            return self._normalize_generic_script(raw_script)

    def _is_deep_dive_format(self, script: Dict[str, Any]) -> bool:
        """DeepDive フォーマットかどうかを判定"""
        # DeepDive の特徴的な構造をチェック
        indicators = [
            "deep_dive" in script.get("type", "").lower(),
            "chapters" in script and isinstance(script["chapters"], list),
            "summary" in script and "key_insights" in script,
            "sources" in script and isinstance(script["sources"], list)
        ]
        return any(indicators)

    def _normalize_deep_dive(self, deep_dive: Dict[str, Any]) -> Dict[str, Any]:
        """DeepDive フォーマットを正規化"""
        normalized = {
            "title": deep_dive.get("title", "NotebookLM DeepDive"),
            "topic": deep_dive.get("topic", ""),
            "summary": deep_dive.get("summary", ""),
            "source_count": len(deep_dive.get("sources", [])),
            "generated_at": deep_dive.get("generated_at", ""),
            "segments": []
        }

        # Chapters を segments に変換
        chapters = deep_dive.get("chapters", [])
        current_time = 0.0

        for i, chapter in enumerate(chapters):
            chapter_title = chapter.get("title", f"Chapter {i+1}")
            chapter_content = chapter.get("content", "")
            chapter_insights = chapter.get("insights", [])

            # 推定時間配分 (章の内容長に基づく)
            estimated_duration = max(10.0, len(chapter_content) / 50)  # 50文字/秒で推定

            segment = {
                "id": f"chapter_{i+1}",
                "start_time": current_time,
                "end_time": current_time + estimated_duration,
                "content": f"{chapter_title}\n\n{chapter_content}",
                "chapter_title": chapter_title,
                "insights": chapter_insights,
                "confidence": 1.0
            }

            normalized["segments"].append(segment)
            current_time += estimated_duration

        # Key insights をメタデータに追加
        normalized["key_insights"] = deep_dive.get("key_insights", [])
        normalized["total_duration"] = current_time

        self.logger.info(f"DeepDive を正規化: {len(normalized['segments'])} セグメント")
        return normalized

    def _normalize_generic_script(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """一般的なスクリプトフォーマットを正規化"""
        # 既に正規化されている場合のフォールバック
        if "segments" in script:
            return script

        # シンプルなテキストの場合
        if isinstance(script.get("content"), str):
            content = script["content"]
            # 段落単位に分割
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

            segments = []
            current_time = 0.0

            for i, para in enumerate(paragraphs):
                duration = max(5.0, len(para) / 50)  # 50文字/秒
                segment = {
                    "id": f"para_{i+1}",
                    "start_time": current_time,
                    "end_time": current_time + duration,
                    "content": para,
                    "confidence": 1.0
                }
                segments.append(segment)
                current_time += duration

            return {
                "title": script.get("title", "Generated Script"),
                "topic": script.get("topic", ""),
                "segments": segments,
                "total_duration": current_time
            }

        # その他のケース
        return script


class ContentAdapterManager:
    """コンテンツアダプターのマネージャー"""

    def __init__(self):
        self.adapters = {
            "notebooklm": NotebookLMContentAdapter(),
            "default": NotebookLMContentAdapter()  # デフォルトは NotebookLM アダプター
        }

    async def normalize_script(self, raw_script: Dict[str, Any], adapter_type: str = "default") -> Dict[str, Any]:
        """指定されたアダプターでスクリプトを正規化"""
        adapter = self.adapters.get(adapter_type, self.adapters["default"])
        return await adapter.normalize_script(raw_script)
