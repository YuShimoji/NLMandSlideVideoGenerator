"""GeminiIntegration テスト (非APIロジック)"""
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

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


class TestGeminiResponseDataclass:
    def test_creation(self):
        resp = GeminiResponse(
            content="test", model="gemini-2.5-flash",
            usage_metadata={}, safety_ratings=[],
            created_at=datetime(2026, 1, 1),
        )
        assert resp.content == "test"
        assert resp.model == "gemini-2.5-flash"


class TestScriptInfoDataclass:
    def test_creation(self):
        info = ScriptInfo(
            title="T", content="C", segments=[],
            total_duration_estimate=100.0, language="ja",
            quality_score=0.8, created_at=datetime(2026, 1, 1),
        )
        assert info.title == "T"
        assert info.quality_score == 0.8


class TestGeminiIntegrationInit:
    def test_default_model(self):
        g = GeminiIntegration(api_key="test-key")
        assert g.model_name == "gemini-2.5-flash"
        assert g.api_key == "test-key"
        assert g.request_count == 0

    def test_custom_model(self):
        g = GeminiIntegration(api_key="key", model_name="gemini-2.0-flash")
        assert g.model_name == "gemini-2.0-flash"

    @patch.dict("os.environ", {"GEMINI_MODEL": "custom-model"})
    def test_model_from_env(self):
        g = GeminiIntegration(api_key="key")
        assert g.model_name == "custom-model"

    def test_fallback_models_exclude_primary(self):
        g = GeminiIntegration(api_key="key", model_name="gemini-2.5-flash")
        assert "gemini-2.5-flash" not in g.fallback_models
        # gemini-2.5-flash 単一モデル構成ではフォールバックは空
        assert g.fallback_models == []


class TestBuildScriptPrompt:
    def test_basic_prompt(self):
        g = GeminiIntegration(api_key="key")
        sources = [
            {"title": "Source1", "url": "http://example.com",
             "content_preview": "preview", "relevance_score": 0.9,
             "reliability_score": 0.8},
        ]
        prompt = g._build_script_prompt(sources, "AIの最新動向", 300.0, "ja")
        assert "AIの最新動向" in prompt
        assert "5.0分" in prompt
        assert "Source1" in prompt
        assert "日本語" in prompt

    def test_english_prompt(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "AI trends", 600.0, "en")
        assert "英語" in prompt

    def test_segment_count_hint_short(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "topic", 200.0, "ja")
        assert "5-7" in prompt

    def test_segment_count_hint_medium(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "topic", 600.0, "ja")
        assert "10-15" in prompt

    def test_segment_count_hint_long(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "topic", 1200.0, "ja")
        assert "20-30" in prompt

    def test_segment_count_hint_very_long(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "topic", 3600.0, "ja")
        assert "30-45" in prompt

    def test_empty_sources(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "topic", 300.0, "ja")
        assert "topic" in prompt


class TestExtractJsonFromResponse:
    def test_plain_json(self):
        text = '{"title": "test"}'
        result = GeminiIntegration._extract_json_from_response(text)
        assert result == '{"title": "test"}'

    def test_code_block_json(self):
        text = '```json\n{"title": "test"}\n```'
        result = GeminiIntegration._extract_json_from_response(text)
        assert '"title"' in result
        parsed = json.loads(result)
        assert parsed["title"] == "test"

    def test_code_block_no_language(self):
        text = '```\n{"key": "value"}\n```'
        result = GeminiIntegration._extract_json_from_response(text)
        parsed = json.loads(result)
        assert parsed["key"] == "value"

    def test_whitespace_handling(self):
        text = '  \n {"title": "test"} \n  '
        result = GeminiIntegration._extract_json_from_response(text)
        assert json.loads(result)["title"] == "test"


class TestBuildMockContent:
    def test_structure(self):
        content = GeminiIntegration._build_mock_content("AI技術")
        assert content["title"] == "AI技術 - 完全解説"
        assert len(content["segments"]) == 5
        assert content["language"] == "ja"

    def test_topic_in_content(self):
        content = GeminiIntegration._build_mock_content("量子コンピュータ")
        for seg in content["segments"]:
            assert "量子コンピュータ" in seg["content"]

    def test_segments_have_speakers(self):
        content = GeminiIntegration._build_mock_content("test")
        speakers = {seg["speaker"] for seg in content["segments"]}
        assert "Host1" in speakers
        assert "Host2" in speakers

    def test_segments_have_key_points(self):
        content = GeminiIntegration._build_mock_content("test")
        for seg in content["segments"]:
            assert len(seg["key_points"]) >= 1

    def test_segments_have_duration(self):
        content = GeminiIntegration._build_mock_content("test")
        total = sum(seg["duration_estimate"] for seg in content["segments"])
        assert total == content["total_duration_estimate"]


class TestCalculateQualityScore:
    def test_empty_segments(self):
        g = GeminiIntegration(api_key="key")
        score = g._calculate_quality_score([], {})
        # 0 >= 0 (key_points condition) → 0.2
        assert score == pytest.approx(0.2)

    def test_high_quality(self):
        g = GeminiIntegration(api_key="key")
        segments = [
            {"content": "x" * 100, "key_points": ["a", "b"]},
            {"content": "y" * 100, "key_points": ["c"]},
            {"content": "z" * 100, "key_points": ["d"]},
        ]
        content_data = {"title": "良質なタイトル"}
        score = g._calculate_quality_score(segments, content_data)
        assert score >= 0.8

    def test_low_quality(self):
        g = GeminiIntegration(api_key="key")
        segments = [{"content": "x", "key_points": []}]
        score = g._calculate_quality_score(segments, {})
        assert score < 0.5

    def test_max_capped_at_1(self):
        g = GeminiIntegration(api_key="key")
        segments = [
            {"content": "x" * 100, "key_points": ["a", "b"]}
            for _ in range(10)
        ]
        score = g._calculate_quality_score(segments, {"title": "long title here"})
        assert score <= 1.0

    def test_few_segments_lower_score(self):
        g = GeminiIntegration(api_key="key")
        few = [{"content": "x" * 100, "key_points": ["a"]}]
        many = [{"content": "x" * 100, "key_points": ["a"]} for _ in range(5)]
        score_few = g._calculate_quality_score(few, {"title": "test title"})
        score_many = g._calculate_quality_score(many, {"title": "test title"})
        assert score_many >= score_few


class TestGetUsageStats:
    def test_initial_stats(self):
        g = GeminiIntegration(api_key="key")
        stats = g.get_usage_stats()
        assert stats["request_count"] == 0
        assert stats["remaining_requests"] == 60
        assert stats["model_name"] == "gemini-2.5-flash"

    def test_after_requests(self):
        g = GeminiIntegration(api_key="key")
        g.request_count = 5
        stats = g.get_usage_stats()
        assert stats["request_count"] == 5
        assert stats["remaining_requests"] == 55


class TestCheckRateLimit:
    @pytest.mark.asyncio
    async def test_under_limit(self):
        g = GeminiIntegration(api_key="key")
        g.request_count = 10
        await g._check_rate_limit()
        assert g.request_count == 10  # 変更なし

    @pytest.mark.asyncio
    async def test_at_limit_resets(self):
        g = GeminiIntegration(api_key="key")
        g.request_count = 60
        g.max_requests_per_minute = 60
        # sleep(60) を避けるためモック
        with patch("asyncio.sleep", return_value=None):
            await g._check_rate_limit()
        assert g.request_count == 0


class TestParseScriptResponse:
    @pytest.mark.asyncio
    async def test_valid_json(self):
        g = GeminiIntegration(api_key="key")
        content = json.dumps({
            "title": "テスト",
            "segments": [
                {"section": "導入", "content": "内容", "duration_estimate": 30.0, "key_points": ["kp"]},
            ],
        })
        resp = GeminiResponse(
            content=content, model="m", usage_metadata={},
            safety_ratings=[], created_at=datetime(2026, 1, 1),
        )
        info = await g._parse_script_response(resp, "topic", "ja")
        assert info.title == "テスト"
        assert len(info.segments) == 1
        assert info.total_duration_estimate == 30.0

    @pytest.mark.asyncio
    async def test_code_block_json(self):
        g = GeminiIntegration(api_key="key")
        inner = json.dumps({
            "title": "T", "segments": [
                {"section": "S", "content": "C", "duration_estimate": 10.0, "key_points": []},
            ],
        })
        content = f"```json\n{inner}\n```"
        resp = GeminiResponse(
            content=content, model="m", usage_metadata={},
            safety_ratings=[], created_at=datetime(2026, 1, 1),
        )
        info = await g._parse_script_response(resp, "topic", "ja")
        assert info.title == "T"

    @pytest.mark.asyncio
    async def test_invalid_json_raises(self):
        g = GeminiIntegration(api_key="key")
        resp = GeminiResponse(
            content="not json", model="m", usage_metadata={},
            safety_ratings=[], created_at=datetime(2026, 1, 1),
        )
        with pytest.raises(json.JSONDecodeError):
            await g._parse_script_response(resp, "topic", "ja")

    @pytest.mark.asyncio
    async def test_missing_segments_defaults(self):
        g = GeminiIntegration(api_key="key")
        content = json.dumps({"title": "T"})
        resp = GeminiResponse(
            content=content, model="m", usage_metadata={},
            safety_ratings=[], created_at=datetime(2026, 1, 1),
        )
        info = await g._parse_script_response(resp, "topic", "ja")
        assert info.segments == []
        assert info.total_duration_estimate == 0.0
