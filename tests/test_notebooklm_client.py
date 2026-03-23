#!/usr/bin/env python3
"""
テスト: NotebookLMClient + NlmScriptConverter (SP-047 Phase 2)

notebooklm-py は未インストール環境でも MockNLMClient で動作することを検証する。
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from notebook_lm.notebooklm_client import NotebookLMClient, NLMNotebook, NLMStudyGuide, NLMSlides
from notebook_lm.nlm_script_converter import NlmScriptConverter
from notebook_lm.gemini_integration import ScriptInfo


# =========================================================
# NotebookLMClient (Mock モード)
# =========================================================

class TestNotebookLMClientMock:
    """notebooklm-py 未インストール時のモック動作を検証"""

    @pytest.mark.asyncio
    async def test_create_notebook_returns_mock_notebook(self):
        client = NotebookLMClient()
        async with client:
            notebook = await client.create_notebook("テストトピック", sources=["https://example.com"])
        assert isinstance(notebook, NLMNotebook)
        assert notebook.notebook_id == "mock-nb-001"
        assert notebook.title == "テストトピック"
        assert "https://example.com" in notebook.source_urls

    @pytest.mark.asyncio
    async def test_get_study_guide_returns_text(self):
        client = NotebookLMClient()
        async with client:
            nb = await client.create_notebook("AI最新動向", sources=[])
            guide = await client.get_study_guide(nb)
        assert isinstance(guide, NLMStudyGuide)
        assert len(guide.text) > 50
        assert guide.notebook_id == "mock-nb-001"

    @pytest.mark.asyncio
    async def test_get_slides_returns_path_object(self, tmp_path):
        client = NotebookLMClient(output_dir=tmp_path)
        async with client:
            nb = await client.create_notebook("スライドテスト", sources=[])
            slides = await client.get_slides(nb, output_dir=tmp_path)
        assert isinstance(slides, NLMSlides)
        assert slides.notebook_id == "mock-nb-001"
        assert slides.format in ("pptx", "pdf")

    @pytest.mark.asyncio
    async def test_delete_notebook_does_not_raise(self):
        client = NotebookLMClient()
        async with client:
            nb = NLMNotebook(notebook_id="mock-nb-001", title="テスト")
            await client.delete_notebook(nb)  # エラーが出なければ OK

    @pytest.mark.asyncio
    async def test_context_manager_sets_not_available(self):
        """モードではis_availableがFalseであること"""
        client = NotebookLMClient()
        async with client:
            # notebooklm-py 未インストール → is_available=False
            assert client.is_available is False


# =========================================================
# NlmScriptConverter
# =========================================================

class TestNlmScriptConverter:
    """Study Guide → ScriptInfo 変換のテスト"""

    SAMPLE_STUDY_GUIDE = """
# AI最新動向 — スタディガイド

## 概要
人工知能は急速に発展しており、様々な分野に影響を与えています。

## 主要な概念

### 1. 生成AIの普及
2023年以降、生成AIは一般ユーザーにも広まりました。
代表的なサービスとしてChatGPTやGeminiが挙げられます。

### 2. 企業での活用
多くの企業がAIを業務効率化に活用しています。
生産性向上の効果が報告されています。

## まとめ
AIは今後も発展し続け、社会への影響はさらに大きくなると予想されます。
"""

    @pytest.mark.asyncio
    async def test_convert_returns_script_info_with_mock(self):
        """Gemini API をモック化して変換動作を検証"""
        converter = NlmScriptConverter(api_key="")

        with patch.object(converter._gemini, "_call_gemini_api", new_callable=AsyncMock) as mock_api:
            mock_response = MagicMock()
            mock_response.content = """{
  "title": "AI最新動向 2024",
  "summary": "生成AIの普及と企業活用について解説",
  "segments": [
    {
      "section": "オープニング",
      "speaker_a_text": "今日はAIの最新動向について解説するのだ！",
      "speaker_b_text": "",
      "duration_estimate": 18.0,
      "key_points": ["AI普及"]
    },
    {
      "section": "オープニング",
      "speaker_a_text": "",
      "speaker_b_text": "どんな動向があるの？気になるわね。",
      "duration_estimate": 6.0,
      "key_points": []
    },
    {
      "section": "本編",
      "speaker_a_text": "まず生成AIは2023年以降急速に普及したのだ。ChatGPTが有名だよね。",
      "speaker_b_text": "",
      "duration_estimate": 22.0,
      "key_points": ["ChatGPT", "生成AI普及"]
    },
    {
      "section": "本編",
      "speaker_a_text": "",
      "speaker_b_text": "企業での活用も増えているのよね。",
      "duration_estimate": 8.0,
      "key_points": ["企業活用"]
    },
    {
      "section": "まとめ",
      "speaker_a_text": "今日のまとめなのだ。AIは今後もさらに発展するよ！",
      "speaker_b_text": "",
      "duration_estimate": 20.0,
      "key_points": ["まとめ"]
    }
  ]
}"""
            mock_response.created_at = None
            mock_api.return_value = mock_response

            script_info = await converter.convert(
                study_guide_text=self.SAMPLE_STUDY_GUIDE,
                topic="AI最新動向",
                target_duration=300.0,
            )

        assert isinstance(script_info, ScriptInfo)
        assert script_info.title == "AI最新動向 2024"
        assert len(script_info.segments) == 5
        assert script_info.quality_score > 0.5

    @pytest.mark.asyncio
    async def test_convert_falls_back_to_mock_on_api_failure(self):
        """Gemini API 失敗時にモックスクリプトが返ること"""
        converter = NlmScriptConverter(api_key="")

        with patch.object(converter._gemini, "_call_gemini_api", side_effect=Exception("API error")):
            script_info = await converter.convert(
                study_guide_text=self.SAMPLE_STUDY_GUIDE,
                topic="テストトピック",
                target_duration=300.0,
            )

        assert isinstance(script_info, ScriptInfo)
        assert len(script_info.segments) >= 3
        assert "テストトピック" in script_info.title

    def test_score_returns_high_for_good_segments(self):
        """品質基準を満たすセグメントに高スコアが付くこと"""
        segments = [
            {"content": "これは50文字前後の発話テキストです。テスト用に作成しました。", "duration_estimate": 20.0}
            for _ in range(6)
        ]
        score = NlmScriptConverter._score(segments, {"title": "テスト"})
        assert score >= 0.75

    def test_score_returns_low_for_bad_segments(self):
        """セグメント数不足・発話長不適切の場合に低スコアになること"""
        segments = [
            {"content": "短い", "duration_estimate": 5.0}
        ]
        score = NlmScriptConverter._score(segments, {})
        assert score < 0.5


# =========================================================
# NotebookLMScriptProvider (統合)
# =========================================================

class TestNotebookLMScriptProvider:
    """NotebookLMScriptProvider の統合動作テスト"""

    @pytest.mark.asyncio
    async def test_generate_script_returns_bundle(self):
        """generate_script がスクリプトバンドルを返すこと"""
        from core.providers.script.notebook_lm_provider import NotebookLMScriptProvider
        from notebook_lm.research_models import SourceInfo
        from notebook_lm.audio_generator import AudioInfo
        from notebook_lm.transcript_processor import TranscriptInfo, TranscriptSegment
        from datetime import datetime
        from pathlib import Path

        provider = NotebookLMScriptProvider(api_key="")

        mock_source = MagicMock(spec=SourceInfo)
        mock_source.url = "https://example.com/article"

        mock_audio = AudioInfo(
            file_path=Path("/tmp/test.wav"),
            duration=20.0,
            language="ja",
            sample_rate=44100,
        )
        mock_transcript = TranscriptInfo(
            title="テスト動画",
            total_duration=20.0,
            segments=[
                TranscriptSegment(
                    id=1, start_time=0.0, end_time=20.0,
                    speaker="ずんだもん", text="テスト発話テキストです。",
                    key_points=[], slide_suggestion="", confidence_score=0.9,
                )
            ],
            accuracy_score=0.9,
            created_at=datetime.now(),
            source_audio_path="/tmp/test.wav",
        )

        with patch.object(provider.audio_generator, "generate_audio", new_callable=AsyncMock, return_value=mock_audio), \
             patch.object(provider.transcript_processor, "process_audio", new_callable=AsyncMock, return_value=mock_transcript), \
             patch.object(provider, "_save_script", return_value=Path("/tmp/script.json")):
            bundle = await provider.generate_script(
                topic="テストトピック",
                sources=[mock_source],
            )

        assert bundle["title"] == "テスト動画"
        assert bundle["topic"] == "テストトピック"
        assert len(bundle["segments"]) == 1
        assert bundle["segments"][0]["speaker"] == "ずんだもん"
