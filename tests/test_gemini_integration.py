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
        assert "12-20" in prompt

    def test_segment_count_hint_medium(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "topic", 600.0, "ja")
        assert "36-60" in prompt

    def test_segment_count_hint_long(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "topic", 1200.0, "ja")
        assert "72-120" in prompt

    def test_segment_count_hint_very_long(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "topic", 3600.0, "ja")
        assert "144-240" in prompt

    def test_empty_sources(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "topic", 300.0, "ja")
        assert "topic" in prompt

    def test_prompt_includes_short_utterance_instruction(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "topic", 300.0, "ja")
        assert "50-150文字" in prompt

    def test_prompt_includes_hook_instruction(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "topic", 300.0, "ja")
        assert "フック" in prompt

    def test_prompt_includes_natural_citation_instruction(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "topic", 300.0, "ja")
        assert "自然な言い回し" in prompt

    def test_prompt_no_long_monologue_instruction(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_script_prompt([], "topic", 300.0, "ja")
        assert "200-400文字" not in prompt


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


class TestBuildStructurePrompt:
    """_build_structure_prompt (トランスクリプト構造化) のテスト"""

    def test_basic_structure_prompt(self):
        g = GeminiIntegration(api_key="key")
        transcript = "Host1: こんにちは。今日はAIについて話しましょう。\nHost2: はい、最近の進展は目覚ましいですね。"
        prompt = g._build_structure_prompt(transcript, "AI最新動向", 300.0, "ja")
        assert "構造化" in prompt
        assert "AI最新動向" in prompt
        assert transcript in prompt
        assert "日本語" in prompt
        # 「生成」ではなく「構造化」タスクであることを明示
        assert "生成」ではなく「構造化」" in prompt

    def test_english_structure_prompt(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_structure_prompt("text", "topic", 300.0, "en")
        assert "英語" in prompt

    def test_speaker_mapping_applied(self):
        g = GeminiIntegration(api_key="key")
        # デフォルトプリセットの話者名は ["Host"] (1名)
        prompt = g._build_structure_prompt(
            "text", "topic", 300.0, "ja",
            speaker_mapping={"Host": "れいむ"},
        )
        assert "れいむ" in prompt

    def test_json_output_format_specified(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_structure_prompt("text", "topic", 300.0, "ja")
        assert '"segments"' in prompt
        assert '"speaker"' in prompt
        assert '"key_points"' in prompt

    def test_preserves_original_content_instruction(self):
        g = GeminiIntegration(api_key="key")
        prompt = g._build_structure_prompt("text", "topic", 300.0, "ja")
        assert "維持" in prompt
        assert "捏造" in prompt


class TestStructureTranscript:
    """structure_transcript (E2E mock) のテスト"""

    @pytest.mark.asyncio
    async def test_structure_transcript_mock_fallback(self):
        """API未設定時にモックフォールバックで構造化が完了すること"""
        g = GeminiIntegration(api_key="key")
        # _llm_provider なし → モックフォールバック
        # MIN_TRANSCRIPT_LENGTH以上のテキストが必要
        transcript = "Host1: AIの最新動向について解説します。最近の技術革新は目覚ましいものがあります。\nHost2: はい、特に注目すべき分野がいくつかありますね。機械学習の進歩は著しいです。"
        info = await g.structure_transcript(
            transcript_text=transcript,
            topic="AI最新動向",
            target_duration=300.0,
        )
        assert isinstance(info, ScriptInfo)
        assert len(info.segments) > 0
        assert info.language == "ja"
        assert info.title  # タイトルが生成されていること

    @pytest.mark.asyncio
    async def test_empty_transcript_raises(self):
        """空文字列でValueErrorが発生すること"""
        g = GeminiIntegration(api_key="key")
        with pytest.raises(ValueError, match="空です"):
            await g.structure_transcript(
                transcript_text="",
                topic="test",
            )

    @pytest.mark.asyncio
    async def test_whitespace_only_transcript_raises(self):
        """空白のみでValueErrorが発生すること"""
        g = GeminiIntegration(api_key="key")
        with pytest.raises(ValueError, match="空です"):
            await g.structure_transcript(
                transcript_text="   \n\t  ",
                topic="test",
            )

    @pytest.mark.asyncio
    async def test_too_short_transcript_raises(self):
        """短すぎるテキストでValueErrorが発生すること"""
        g = GeminiIntegration(api_key="key")
        with pytest.raises(ValueError, match="短すぎます"):
            await g.structure_transcript(
                transcript_text="短い",
                topic="test",
            )

    @pytest.mark.asyncio
    async def test_min_length_transcript_accepted(self):
        """最低文字数ちょうどのテキストが受け入れられること"""
        g = GeminiIntegration(api_key="key")
        text = "あ" * GeminiIntegration.MIN_TRANSCRIPT_LENGTH
        info = await g.structure_transcript(
            transcript_text=text,
            topic="test",
        )
        assert isinstance(info, ScriptInfo)

    @pytest.mark.asyncio
    async def test_very_long_transcript_truncated(self):
        """MAX_TRANSCRIPT_LENGTH超のテキストが切り詰められること（エラーにならない）"""
        g = GeminiIntegration(api_key="key")
        text = "あ" * (GeminiIntegration.MAX_TRANSCRIPT_LENGTH + 1000)
        # 切り詰め警告が出るがエラーにはならない
        info = await g.structure_transcript(
            transcript_text=text,
            topic="test",
        )
        assert isinstance(info, ScriptInfo)

    @pytest.mark.asyncio
    async def test_structure_transcript_with_speaker_mapping(self):
        """speaker_mappingが構造化に渡されること"""
        g = GeminiIntegration(api_key="key")
        transcript = "Host1: こんにちは。" * 10  # MIN_TRANSCRIPT_LENGTH以上
        info = await g.structure_transcript(
            transcript_text=transcript,
            topic="テスト",
            speaker_mapping={"Host1": "れいむ", "Host2": "まりさ"},
        )
        assert isinstance(info, ScriptInfo)

    def test_constants_defined(self):
        """バリデーション定数が妥当な値であること"""
        assert GeminiIntegration.MIN_TRANSCRIPT_LENGTH > 0
        assert GeminiIntegration.MAX_TRANSCRIPT_LENGTH > GeminiIntegration.MIN_TRANSCRIPT_LENGTH
        assert GeminiIntegration.MAX_TRANSCRIPT_LENGTH <= 1_000_000


class TestGenerateThumbnailCopy:
    """generate_thumbnail_copy (SP-037 Phase 4) のテスト"""

    @pytest.mark.asyncio
    async def test_mock_fallback_returns_valid_structure(self):
        """API未設定時にモックフォールバックで有効な構造が返ること"""
        g = GeminiIntegration(api_key="key")
        script_info = ScriptInfo(
            title="AIの衝撃的な進化",
            content="",
            segments=[
                {"speaker": "Host1", "content": "AIの最新動向を解説します。"},
                {"speaker": "Host2", "content": "最近の進歩は驚くべきものがあります。"},
                {"speaker": "Host1", "content": "特に注目すべき分野を見ていきましょう。"},
            ],
            total_duration_estimate=300.0,
            language="ja",
            quality_score=0.8,
            created_at=datetime(2026, 1, 1),
        )
        result = await g.generate_thumbnail_copy(script_info)

        assert "main_text" in result
        assert "sub_text" in result
        assert "label" in result
        assert "suggested_pattern" in result
        assert "suggested_color" in result
        assert result["suggested_pattern"] in {"A", "B", "C", "D", "E"}
        assert result["suggested_color"] in {
            "dark_red", "dark_yellow", "map_white", "high_contrast", "warm_alert",
        }

    @pytest.mark.asyncio
    async def test_json_parse_failure_returns_defaults(self):
        """JSON解析失敗時にデフォルト値が返ること"""
        g = GeminiIntegration(api_key="key")

        # _call_gemini_api を無効なJSONを返すようにモック
        async def mock_api(prompt):
            return GeminiResponse(
                content="not valid json at all",
                model="test", usage_metadata={},
                safety_ratings=[], created_at=datetime(2026, 1, 1),
            )

        g._call_gemini_api = mock_api
        script_info = ScriptInfo(
            title="テスト題名", content="", segments=[],
            total_duration_estimate=300.0, language="ja",
            quality_score=0.5, created_at=datetime(2026, 1, 1),
        )
        result = await g.generate_thumbnail_copy(script_info)
        assert result["main_text"] == "テスト題名"
        assert result["suggested_pattern"] == "A"
        assert result["suggested_color"] == "dark_red"

    @pytest.mark.asyncio
    async def test_missing_keys_补完(self):
        """レスポンスに不足キーがある場合にデフォルト値で補完されること"""
        g = GeminiIntegration(api_key="key")

        async def mock_api(prompt):
            return GeminiResponse(
                content=json.dumps({"main_text": "なぜAIは", "sub_text": "その理由とは"}),
                model="test", usage_metadata={},
                safety_ratings=[], created_at=datetime(2026, 1, 1),
            )

        g._call_gemini_api = mock_api
        script_info = ScriptInfo(
            title="AI", content="", segments=[],
            total_duration_estimate=300.0, language="ja",
            quality_score=0.5, created_at=datetime(2026, 1, 1),
        )
        result = await g.generate_thumbnail_copy(script_info)
        assert result["main_text"] == "なぜAIは"
        assert result["sub_text"] == "その理由とは"
        assert "label" in result
        assert "suggested_pattern" in result
        assert "suggested_color" in result

    @pytest.mark.asyncio
    async def test_invalid_pattern_normalized(self):
        """無効なパターン値がAにフォールバックされること"""
        g = GeminiIntegration(api_key="key")

        async def mock_api(prompt):
            return GeminiResponse(
                content=json.dumps({
                    "main_text": "test", "sub_text": "sub",
                    "label": "解説", "suggested_pattern": "Z",
                    "suggested_color": "invalid_color",
                }),
                model="test", usage_metadata={},
                safety_ratings=[], created_at=datetime(2026, 1, 1),
            )

        g._call_gemini_api = mock_api
        script_info = ScriptInfo(
            title="T", content="", segments=[],
            total_duration_estimate=300.0, language="ja",
            quality_score=0.5, created_at=datetime(2026, 1, 1),
        )
        result = await g.generate_thumbnail_copy(script_info)
        assert result["suggested_pattern"] == "A"
        assert result["suggested_color"] == "dark_red"

    @pytest.mark.asyncio
    async def test_valid_api_response_parsed(self):
        """正常なAPIレスポンスが正しく解析されること"""
        g = GeminiIntegration(api_key="key")

        expected = {
            "main_text": "なぜ日本は",
            "sub_text": "知られざる理由を徹底解説",
            "label": "ゆっくり解説",
            "suggested_pattern": "C",
            "suggested_color": "map_white",
        }

        async def mock_api(prompt):
            return GeminiResponse(
                content=json.dumps(expected),
                model="test", usage_metadata={},
                safety_ratings=[], created_at=datetime(2026, 1, 1),
            )

        g._call_gemini_api = mock_api
        script_info = ScriptInfo(
            title="日本の地理", content="", segments=[],
            total_duration_estimate=300.0, language="ja",
            quality_score=0.5, created_at=datetime(2026, 1, 1),
        )
        result = await g.generate_thumbnail_copy(script_info)
        assert result == expected
