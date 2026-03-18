"""GeminiIntegration 拡張テスト — カバレッジ 54% → 80%+ を目指す。

対象:
  - generate_script_from_sources() (L57-79)
  - _call_llm_provider() (ILLMProvider統合後)
  - _call_gemini_api() mock fallback / quota / ImportError (L192-247)
  - _parse_script_response() exception handling (L307-312)
  - generate_slide_content() (L402-447)
"""
import asyncio
import json
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# notebook_lm の依存をモック
with patch.dict("sys.modules", {
    "config": MagicMock(),
    "config.settings": MagicMock(settings=MagicMock()),
    "notebook_lm.source_collector": MagicMock(),
    "notebook_lm.audio_generator": MagicMock(),
}):
    from notebook_lm.gemini_integration import (
        GeminiIntegration,
        GeminiResponse,
        ScriptInfo,
    )


# ---------------------------------------------------------------------------
# Helper: 有効な JSON レスポンスを返す GeminiResponse を生成
# ---------------------------------------------------------------------------
def _make_valid_script_json() -> str:
    return json.dumps({
        "title": "テストトピック解説",
        "segments": [
            {
                "section": "導入",
                "content": "テスト内容です。" * 10,
                "duration_estimate": 30.0,
                "key_points": ["ポイントA", "ポイントB"],
                "speaker": "Host1",
            },
            {
                "section": "本論",
                "content": "詳細な説明です。" * 10,
                "duration_estimate": 60.0,
                "key_points": ["ポイントC"],
                "speaker": "Host2",
            },
        ],
        "total_duration_estimate": 90.0,
        "language": "ja",
    }, ensure_ascii=False)


def _make_valid_gemini_response(content: str | None = None) -> GeminiResponse:
    return GeminiResponse(
        content=content or _make_valid_script_json(),
        model="gemini-2.5-flash",
        usage_metadata={},
        safety_ratings=[],
        created_at=datetime(2026, 1, 1),
    )


def _make_slide_json() -> str:
    return json.dumps({
        "slides": [
            {
                "slide_number": 1,
                "title": "タイトルスライド",
                "content": "概要",
                "layout": "title_slide",
                "duration": 15.0,
            },
            {
                "slide_number": 2,
                "title": "内容",
                "content": "箇条書き",
                "layout": "content_slide",
                "duration": 20.0,
            },
        ]
    }, ensure_ascii=False)


# ===================================================================
# 1. generate_script_from_sources()  (L57-79)
# ===================================================================
class TestGenerateScriptFromSources:
    """generate_script_from_sources の正常系・例外系。"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        """_call_gemini_api → _parse_script_response を経由して ScriptInfo を返す。"""
        g = GeminiIntegration(api_key="test-key")
        mock_resp = _make_valid_gemini_response()

        with patch.object(g, "_call_gemini_api", new_callable=AsyncMock, return_value=mock_resp):
            result = await g.generate_script_from_sources(
                sources=[{"title": "S1", "url": "http://x", "content_preview": "p",
                          "relevance_score": 0.9, "reliability_score": 0.8}],
                topic="テストトピック",
                target_duration=300.0,
                language="ja",
            )

        assert isinstance(result, ScriptInfo)
        assert result.title == "テストトピック解説"
        assert len(result.segments) == 2
        assert result.total_duration_estimate == 90.0

    @pytest.mark.asyncio
    async def test_api_call_raises_value_error(self):
        """_call_gemini_api が ValueError を投げた場合、そのまま伝播する。"""
        g = GeminiIntegration(api_key="test-key")

        with patch.object(g, "_call_gemini_api", new_callable=AsyncMock,
                          side_effect=ValueError("bad value")):
            with pytest.raises(ValueError, match="bad value"):
                await g.generate_script_from_sources([], "topic")

    @pytest.mark.asyncio
    async def test_api_call_raises_runtime_error(self):
        """RuntimeError も except ブロックで捕捉・再送される。"""
        g = GeminiIntegration(api_key="test-key")

        with patch.object(g, "_call_gemini_api", new_callable=AsyncMock,
                          side_effect=RuntimeError("runtime")):
            with pytest.raises(RuntimeError, match="runtime"):
                await g.generate_script_from_sources([], "topic")

    @pytest.mark.asyncio
    async def test_generic_exception_is_reraised(self):
        """未分類の Exception も catch → reraise される (L77-79)。"""
        g = GeminiIntegration(api_key="test-key")

        class CustomError(Exception):
            pass

        with patch.object(g, "_call_gemini_api", new_callable=AsyncMock,
                          side_effect=CustomError("custom")):
            with pytest.raises(CustomError, match="custom"):
                await g.generate_script_from_sources([], "topic")

    @pytest.mark.asyncio
    async def test_cancelled_error_propagates(self):
        """asyncio.CancelledError はそのまま再送 (L72-73)。"""
        g = GeminiIntegration(api_key="test-key")

        with patch.object(g, "_call_gemini_api", new_callable=AsyncMock,
                          side_effect=asyncio.CancelledError()):
            with pytest.raises(asyncio.CancelledError):
                await g.generate_script_from_sources([], "topic")

    @pytest.mark.asyncio
    async def test_parse_failure_propagates(self):
        """_parse_script_response が失敗する場合 (L74-76)。"""
        g = GeminiIntegration(api_key="test-key")
        bad_resp = GeminiResponse(
            content="not json at all",
            model="m", usage_metadata={}, safety_ratings=[],
            created_at=datetime(2026, 1, 1),
        )

        with patch.object(g, "_call_gemini_api", new_callable=AsyncMock,
                          return_value=bad_resp):
            with pytest.raises(json.JSONDecodeError):
                await g.generate_script_from_sources([], "topic")


# ===================================================================
# 2. _call_llm_provider() (旧 _try_model — ILLMProvider統合後)
# ===================================================================
class TestCallLLMProvider:
    """_call_llm_provider のモック付きテスト (SP-043 Phase 2)。"""

    @pytest.mark.asyncio
    async def test_happy_path_via_provider(self):
        """ILLMProvider経由で正常にレスポンスが返る。"""
        mock_provider = AsyncMock()
        mock_provider.model_name = "gpt-4o-mini"
        mock_provider.generate_text.return_value = _make_valid_script_json()

        g = GeminiIntegration(api_key="test-key", llm_provider=mock_provider)
        result = await g._call_gemini_api("test prompt")

        assert isinstance(result, GeminiResponse)
        assert result.model == "gpt-4o-mini"
        assert "テストトピック解説" in result.content
        assert g.request_count == 1
        assert g.fallback_used is False

    @pytest.mark.asyncio
    async def test_provider_failure_falls_back_to_mock(self):
        """ILLMProvider失敗時にモックフォールバックが使われる。"""
        mock_provider = AsyncMock()
        mock_provider.model_name = "gpt-4o-mini"
        mock_provider.generate_text.side_effect = RuntimeError("API error")

        g = GeminiIntegration(api_key="test-key", llm_provider=mock_provider)
        result = await g._call_gemini_api("【トピック】\nテスト\n本文")

        assert isinstance(result, GeminiResponse)
        assert g.fallback_used is True
        assert g.actual_provider == "mock"

    @pytest.mark.asyncio
    async def test_provider_quota_falls_back_to_mock(self):
        """クォータ超過(429)時にモックフォールバック。"""
        mock_provider = AsyncMock()
        mock_provider.model_name = "gemini-2.5-flash"
        mock_provider.generate_text.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED")

        g = GeminiIntegration(api_key="test-key", llm_provider=mock_provider)
        result = await g._call_gemini_api("【トピック】\nテスト\n本文")

        assert isinstance(result, GeminiResponse)
        assert g.fallback_used is True


# ===================================================================
# 3. _call_gemini_api()  (L190-247)
# ===================================================================
class TestCallGeminiApi:
    """_call_gemini_api のフォールバックパス各種。"""

    @pytest.mark.asyncio
    async def test_mock_fallback_when_api_key_empty(self):
        """api_key が空文字 → API 試行をスキップし、モックに直行する。"""
        g = GeminiIntegration(api_key="")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await g._call_gemini_api(
                "テスト\n【トピック】\nテストトピック\n残り"
            )

        assert isinstance(result, GeminiResponse)
        parsed = json.loads(result.content)
        # モック台本が返る
        assert "テストトピック" in parsed["title"]
        assert len(parsed["segments"]) == 5

    @pytest.mark.asyncio
    async def test_mock_fallback_topic_extraction(self):
        """モックフォールバック時、プロンプトからトピック名を正しく抽出する。"""
        g = GeminiIntegration(api_key="")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await g._call_gemini_api(
                "前文\n【トピック】\n量子コンピュータの未来\n後文"
            )

        parsed = json.loads(result.content)
        assert "量子コンピュータの未来" in parsed["title"]

    @pytest.mark.asyncio
    async def test_mock_fallback_default_topic(self):
        """プロンプトにトピックパターンがない場合、デフォルトトピックが使われる。"""
        g = GeminiIntegration(api_key="")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await g._call_gemini_api("no topic marker here")

        parsed = json.loads(result.content)
        assert "最新技術動向" in parsed["title"]

    @pytest.mark.asyncio
    async def test_import_error_falls_to_mock(self):
        """LLM SDK未インストール → ImportError → モックフォールバック。"""
        mock_provider = AsyncMock()
        mock_provider.model_name = "gpt-4o-mini"
        mock_provider.generate_text.side_effect = ImportError("No module named 'openai'")

        g = GeminiIntegration(api_key="real-key", llm_provider=mock_provider)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await g._call_gemini_api(
                "前文\n【トピック】\nSDK不在テスト\n後文"
            )

        parsed = json.loads(result.content)
        assert len(parsed["segments"]) == 5
        assert g.fallback_used is True

    @pytest.mark.asyncio
    async def test_quota_error_falls_to_mock(self):
        """429クォータエラー → モックにフォールバック。"""
        mock_provider = AsyncMock()
        mock_provider.model_name = "gemini-2.5-flash"
        mock_provider.generate_text.side_effect = Exception("429 Resource has been exhausted")

        g = GeminiIntegration(api_key="real-key", llm_provider=mock_provider)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await g._call_gemini_api(
                "前文\n【トピック】\nクォータテスト\n後文"
            )

        parsed = json.loads(result.content)
        assert len(parsed["segments"]) == 5
        assert g.fallback_used is True
        assert g.actual_provider == "mock"

    @pytest.mark.asyncio
    async def test_non_quota_error_falls_to_mock(self):
        """認証失敗等 → モックフォールバック。"""
        mock_provider = AsyncMock()
        mock_provider.model_name = "gpt-4o-mini"
        mock_provider.generate_text.side_effect = Exception("403 Permission denied")

        g = GeminiIntegration(api_key="real-key", llm_provider=mock_provider)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await g._call_gemini_api(
                "前文\n【トピック】\n認証失敗テスト\n後文"
            )

        parsed = json.loads(result.content)
        assert len(parsed["segments"]) == 5
        assert g.fallback_used is True

    @pytest.mark.asyncio
    async def test_cancelled_error_propagates(self):
        """_call_gemini_api 内の CancelledError は再送される (L240-241)。"""
        g = GeminiIntegration(api_key="")

        with patch("asyncio.sleep", new_callable=AsyncMock,
                   side_effect=asyncio.CancelledError()):
            with pytest.raises(asyncio.CancelledError):
                await g._call_gemini_api("prompt")

    @pytest.mark.asyncio
    async def test_request_count_incremented_on_mock(self):
        """モックフォールバック時もリクエストカウントが増加する。"""
        g = GeminiIntegration(api_key="")
        initial_count = g.request_count

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await g._call_gemini_api("前文\n【トピック】\nカウントテスト\n")

        assert g.request_count == initial_count + 1

    @pytest.mark.asyncio
    async def test_primary_model_success_no_fallback(self):
        """ILLMProvider経由で成功する場合、フォールバックは使われない。"""
        mock_provider = AsyncMock()
        mock_provider.model_name = "gpt-4o-mini"
        mock_provider.generate_text.return_value = _make_valid_script_json()

        g = GeminiIntegration(api_key="real-key", llm_provider=mock_provider)
        result = await g._call_gemini_api("test prompt")

        assert isinstance(result, GeminiResponse)
        assert result.model == "gpt-4o-mini"
        assert g.fallback_used is False


# ===================================================================
# 4. _parse_script_response() exception handling  (L307-312)
# ===================================================================
class TestParseScriptResponseExceptions:
    """_parse_script_response の例外ハンドリングパス。"""

    @pytest.mark.asyncio
    async def test_key_error_propagates(self):
        """セグメントデータ処理中の KeyError が捕捉・再送される (L307-309)。"""
        g = GeminiIntegration(api_key="key")

        # _calculate_quality_score をわざと KeyError にする
        with patch.object(g, "_calculate_quality_score", side_effect=KeyError("missing_key")):
            content = json.dumps({
                "title": "T",
                "segments": [{"section": "S", "content": "C", "duration_estimate": 10.0, "key_points": []}],
            })
            resp = GeminiResponse(
                content=content, model="m", usage_metadata={},
                safety_ratings=[], created_at=datetime(2026, 1, 1),
            )
            with pytest.raises(KeyError, match="missing_key"):
                await g._parse_script_response(resp, "topic", "ja")

    @pytest.mark.asyncio
    async def test_type_error_propagates(self):
        """TypeError が捕捉・再送される (L307-309)。"""
        g = GeminiIntegration(api_key="key")

        with patch.object(g, "_calculate_quality_score", side_effect=TypeError("bad type")):
            content = json.dumps({
                "title": "T",
                "segments": [{"section": "S", "content": "C", "duration_estimate": 10.0, "key_points": []}],
            })
            resp = GeminiResponse(
                content=content, model="m", usage_metadata={},
                safety_ratings=[], created_at=datetime(2026, 1, 1),
            )
            with pytest.raises(TypeError, match="bad type"):
                await g._parse_script_response(resp, "topic", "ja")

    @pytest.mark.asyncio
    async def test_generic_exception_propagates(self):
        """未分類 Exception が捕捉・再送される (L310-312)。"""
        g = GeminiIntegration(api_key="key")

        class WeirdError(Exception):
            pass

        with patch.object(g, "_calculate_quality_score", side_effect=WeirdError("weird")):
            content = json.dumps({
                "title": "T",
                "segments": [{"section": "S", "content": "C", "duration_estimate": 10.0, "key_points": []}],
            })
            resp = GeminiResponse(
                content=content, model="m", usage_metadata={},
                safety_ratings=[], created_at=datetime(2026, 1, 1),
            )
            with pytest.raises(WeirdError, match="weird"):
                await g._parse_script_response(resp, "topic", "ja")

    @pytest.mark.asyncio
    async def test_attribute_error_propagates(self):
        """AttributeError (L307-309)。"""
        g = GeminiIntegration(api_key="key")

        with patch.object(g, "_calculate_quality_score", side_effect=AttributeError("no attr")):
            content = json.dumps({"title": "T", "segments": []})
            resp = GeminiResponse(
                content=content, model="m", usage_metadata={},
                safety_ratings=[], created_at=datetime(2026, 1, 1),
            )
            with pytest.raises(AttributeError, match="no attr"):
                await g._parse_script_response(resp, "topic", "ja")


# ===================================================================
# 5. generate_slide_content()  (L396-447)
# ===================================================================
class TestGenerateSlideContent:
    """generate_slide_content の正常系・例外系。"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        """正常系: _call_gemini_api が有効な JSON を返す。"""
        g = GeminiIntegration(api_key="test-key")

        slide_resp = GeminiResponse(
            content=_make_slide_json(),
            model="gemini-2.5-flash",
            usage_metadata={}, safety_ratings=[],
            created_at=datetime(2026, 1, 1),
        )

        script = ScriptInfo(
            title="T", content="スクリプト内容", segments=[],
            total_duration_estimate=100.0, language="ja",
            quality_score=0.8, created_at=datetime(2026, 1, 1),
        )

        with patch.object(g, "_call_gemini_api", new_callable=AsyncMock,
                          return_value=slide_resp):
            result = await g.generate_slide_content(script, max_slides=5)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["title"] == "タイトルスライド"
        assert result[1]["layout"] == "content_slide"

    @pytest.mark.asyncio
    async def test_json_decode_error_propagates(self):
        """_call_gemini_api が非 JSON を返した場合、JSONDecodeError (L442-444)。"""
        g = GeminiIntegration(api_key="test-key")

        bad_resp = GeminiResponse(
            content="this is not json",
            model="m", usage_metadata={}, safety_ratings=[],
            created_at=datetime(2026, 1, 1),
        )

        script = ScriptInfo(
            title="T", content="C", segments=[],
            total_duration_estimate=100.0, language="ja",
            quality_score=0.8, created_at=datetime(2026, 1, 1),
        )

        with patch.object(g, "_call_gemini_api", new_callable=AsyncMock,
                          return_value=bad_resp):
            with pytest.raises(json.JSONDecodeError):
                await g.generate_slide_content(script)

    @pytest.mark.asyncio
    async def test_value_error_propagates(self):
        """_call_gemini_api が ValueError を投げた場合 (L442-444)。"""
        g = GeminiIntegration(api_key="test-key")

        script = ScriptInfo(
            title="T", content="C", segments=[],
            total_duration_estimate=100.0, language="ja",
            quality_score=0.8, created_at=datetime(2026, 1, 1),
        )

        with patch.object(g, "_call_gemini_api", new_callable=AsyncMock,
                          side_effect=ValueError("val error")):
            with pytest.raises(ValueError, match="val error"):
                await g.generate_slide_content(script)

    @pytest.mark.asyncio
    async def test_generic_exception_propagates(self):
        """未分類 Exception が捕捉・再送される (L445-447)。"""
        g = GeminiIntegration(api_key="test-key")

        class SlideError(Exception):
            pass

        script = ScriptInfo(
            title="T", content="C", segments=[],
            total_duration_estimate=100.0, language="ja",
            quality_score=0.8, created_at=datetime(2026, 1, 1),
        )

        with patch.object(g, "_call_gemini_api", new_callable=AsyncMock,
                          side_effect=SlideError("slide fail")):
            with pytest.raises(SlideError, match="slide fail"):
                await g.generate_slide_content(script)

    @pytest.mark.asyncio
    async def test_cancelled_error_propagates(self):
        """CancelledError は再送される (L440-441)。"""
        g = GeminiIntegration(api_key="test-key")

        script = ScriptInfo(
            title="T", content="C", segments=[],
            total_duration_estimate=100.0, language="ja",
            quality_score=0.8, created_at=datetime(2026, 1, 1),
        )

        with patch.object(g, "_call_gemini_api", new_callable=AsyncMock,
                          side_effect=asyncio.CancelledError()):
            with pytest.raises(asyncio.CancelledError):
                await g.generate_slide_content(script)

    @pytest.mark.asyncio
    async def test_empty_slides_array(self):
        """slides が空配列の場合、空リストが返る。"""
        g = GeminiIntegration(api_key="test-key")

        empty_resp = GeminiResponse(
            content=json.dumps({"slides": []}),
            model="m", usage_metadata={}, safety_ratings=[],
            created_at=datetime(2026, 1, 1),
        )

        script = ScriptInfo(
            title="T", content="C", segments=[],
            total_duration_estimate=100.0, language="ja",
            quality_score=0.8, created_at=datetime(2026, 1, 1),
        )

        with patch.object(g, "_call_gemini_api", new_callable=AsyncMock,
                          return_value=empty_resp):
            result = await g.generate_slide_content(script)

        assert result == []

    @pytest.mark.asyncio
    async def test_missing_slides_key(self):
        """slides キーが無い JSON の場合、空リストが返る。"""
        g = GeminiIntegration(api_key="test-key")

        no_slides_resp = GeminiResponse(
            content=json.dumps({"other": "data"}),
            model="m", usage_metadata={}, safety_ratings=[],
            created_at=datetime(2026, 1, 1),
        )

        script = ScriptInfo(
            title="T", content="C", segments=[],
            total_duration_estimate=100.0, language="ja",
            quality_score=0.8, created_at=datetime(2026, 1, 1),
        )

        with patch.object(g, "_call_gemini_api", new_callable=AsyncMock,
                          return_value=no_slides_resp):
            result = await g.generate_slide_content(script)

        assert result == []
