"""セグメント粒度制御テスト (SP-044)"""
import json

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from core.segment_duration_validator import (
    estimate_segment_duration,
    validate_segments,
    adjust_segments,
    _get_segment_range,
    _merge_short_segments,
    _expand_segments,
    SegmentValidationResult,
)


class TestEstimateDuration:
    def test_japanese_text(self) -> None:
        seg = {"content": "これはテスト用の日本語テキストです。"}
        dur = estimate_segment_duration(seg)
        # 16文字 / 4文字/秒 = 4.0秒 + padding 0.5 = 4.5秒
        assert 3.0 < dur < 8.0

    def test_english_text(self) -> None:
        seg = {"content": "This is a test sentence with some words for duration estimation."}
        dur = estimate_segment_duration(seg)
        # 12 words / 2.5 words/sec = 4.8秒 + padding
        assert 3.0 < dur < 10.0

    def test_mixed_text(self) -> None:
        seg = {"content": "AI技術の最新動向 - The latest trends in artificial intelligence"}
        dur = estimate_segment_duration(seg)
        assert dur > 2.0

    def test_empty_text(self) -> None:
        seg = {"content": ""}
        dur = estimate_segment_duration(seg)
        assert dur == 3.0  # デフォルト値

    def test_text_key_fallback(self) -> None:
        seg = {"text": "テストテキスト"}
        dur = estimate_segment_duration(seg)
        assert dur > 1.0

    def test_minimum_duration(self) -> None:
        seg = {"content": "A"}
        dur = estimate_segment_duration(seg)
        assert dur >= 1.5  # min(1.0) + padding(0.5)


class TestGetSegmentRange:
    def test_5min(self) -> None:
        min_s, max_s = _get_segment_range(300)
        assert min_s == 3
        assert max_s == 10

    def test_30min(self) -> None:
        min_s, max_s = _get_segment_range(1800)
        assert min_s >= 10
        assert max_s <= 50

    def test_60min(self) -> None:
        min_s, max_s = _get_segment_range(3600)
        assert min_s >= 20
        assert max_s >= 40

    def test_very_short(self) -> None:
        min_s, max_s = _get_segment_range(60)
        assert min_s >= 1
        assert max_s >= 2

    def test_very_long(self) -> None:
        min_s, max_s = _get_segment_range(7200)
        assert min_s >= 40
        assert max_s >= 80

    def test_zero_duration(self) -> None:
        min_s, max_s = _get_segment_range(0)
        assert min_s == 1
        assert max_s == 10


class TestValidateSegments:
    def _make_segments(self, count: int, chars_per: int = 80) -> list:
        return [
            {"content": "あ" * chars_per, "section": f"section_{i}"}
            for i in range(count)
        ]

    def test_ok_5min(self) -> None:
        # 5セグメント x 80文字 = 5 x (80/4 + 0.5) = 102.5秒, target=300
        # ratio = 102.5/300 = 0.34 → too_short
        # Use 120 chars per seg: 5 x (120/4 + 0.5) = 152.5秒, ratio = 0.51
        segs = self._make_segments(5, chars_per=200)
        result = validate_segments(segs, 300)
        # 5 x (200/4 + 0.5) = 252.5秒, ratio = 0.84
        assert result.is_ok

    def test_too_short(self) -> None:
        segs = self._make_segments(3, chars_per=20)
        result = validate_segments(segs, 1800)
        assert result.status == "too_short"
        assert result.suggestion == "add_segments"

    def test_too_long(self) -> None:
        segs = self._make_segments(50, chars_per=200)
        result = validate_segments(segs, 300)
        assert result.status == "too_long"
        assert result.suggestion == "trim_segments"

    def test_too_few(self) -> None:
        # 2セグメント for 30min target → too_few
        segs = self._make_segments(2, chars_per=1500)
        result = validate_segments(segs, 1800)
        # 推定尺: 2 x (1500/4 + 0.5) = 751秒, ratio = 0.42 → too_short takes priority
        assert result.status in ("too_short", "too_few")

    def test_too_many(self) -> None:
        # 100セグメント for 5min → too_many or too_long
        segs = self._make_segments(100, chars_per=10)
        result = validate_segments(segs, 300)
        assert result.status in ("too_many", "too_long")

    def test_result_has_message(self) -> None:
        segs = self._make_segments(5, chars_per=200)
        result = validate_segments(segs, 300)
        assert result.message != ""

    def test_result_has_ratio(self) -> None:
        segs = self._make_segments(5, chars_per=200)
        result = validate_segments(segs, 300)
        assert 0.0 < result.ratio < 5.0

    def test_empty_segments(self) -> None:
        result = validate_segments([], 300)
        assert result.status == "too_short"
        assert result.estimated_duration == 0.0


class TestMergeShortSegments:
    def test_merge_reduces_count(self) -> None:
        segments = [
            {"content": "A", "speaker": "Host1", "key_points": ["a"]},
            {"content": "B", "speaker": "Host1", "key_points": ["b"]},
            {"content": "C" * 100, "speaker": "Host2", "key_points": ["c"]},
            {"content": "D" * 100, "speaker": "Host2", "key_points": ["d"]},
        ]
        validation = SegmentValidationResult(
            status="too_many", segment_count=4, estimated_duration=100,
            target_duration=300, ratio=0.33, expected_min=1, expected_max=2,
            suggestion="merge_segments",
        )
        result = _merge_short_segments(segments, validation)
        assert len(result) <= 2

    def test_merge_preserves_content(self) -> None:
        segments = [
            {"content": "short", "speaker": "H1", "key_points": ["x"]},
            {"content": "long text " * 20, "speaker": "H2", "key_points": ["y"]},
        ]
        validation = SegmentValidationResult(
            status="too_many", segment_count=2, estimated_duration=100,
            target_duration=300, ratio=0.33, expected_min=1, expected_max=1,
            suggestion="merge_segments",
        )
        result = _merge_short_segments(segments, validation)
        assert len(result) == 1
        assert "short" in result[0]["content"]
        assert "long text" in result[0]["content"]

    def test_no_merge_when_within_range(self) -> None:
        segments = [{"content": "ok", "key_points": []}]
        validation = SegmentValidationResult(
            status="too_many", segment_count=1, estimated_duration=10,
            target_duration=300, ratio=0.03, expected_min=1, expected_max=5,
            suggestion="merge_segments",
        )
        result = _merge_short_segments(segments, validation)
        assert len(result) == 1


class TestAdjustSegments:
    @pytest.mark.asyncio
    async def test_ok_returns_unchanged(self) -> None:
        segs = [{"content": "test", "key_points": []}]
        validation = SegmentValidationResult(
            status="ok", segment_count=1, estimated_duration=10,
            target_duration=300, ratio=0.8, expected_min=1, expected_max=5,
            suggestion="",
        )
        result = await adjust_segments(segs, validation)
        assert result is segs

    @pytest.mark.asyncio
    async def test_too_long_merges(self) -> None:
        segs = [
            {"content": "A", "speaker": "H1", "key_points": []},
            {"content": "B", "speaker": "H1", "key_points": []},
            {"content": "C" * 100, "speaker": "H2", "key_points": []},
        ]
        validation = SegmentValidationResult(
            status="too_many", segment_count=3, estimated_duration=500,
            target_duration=300, ratio=1.67, expected_min=1, expected_max=2,
            suggestion="merge_segments",
        )
        result = await adjust_segments(segs, validation)
        assert len(result) <= 2

    @pytest.mark.asyncio
    async def test_add_segments_with_mock_llm(self) -> None:
        """LLMプロバイダー成功時: 追加セグメントが結合される。"""
        segs = [
            {"content": "導入部分のテキスト" * 5, "speaker": "Host1", "section": "intro", "key_points": ["導入"]},
        ]
        validation = SegmentValidationResult(
            status="too_short", segment_count=1, estimated_duration=30,
            target_duration=300, ratio=0.1, expected_min=3, expected_max=10,
            suggestion="add_segments",
        )

        mock_provider = AsyncMock()
        mock_provider.generate_text.return_value = json.dumps([
            {"speaker": "Host1", "content": "追加セグメント1の内容テキスト", "section": "補足", "key_points": ["追加1"]},
            {"speaker": "Host2", "content": "追加セグメント2の内容テキスト", "section": "補足", "key_points": ["追加2"]},
        ])

        with patch("core.llm_provider.create_llm_provider", return_value=mock_provider):
            result = await _expand_segments(segs, validation, "テストトピック", None)

        assert len(result) == 3  # 元1 + 追加2
        assert result[0]["content"] == segs[0]["content"]
        assert "追加セグメント1" in result[1]["content"]
        assert "追加セグメント2" in result[2]["content"]

    @pytest.mark.asyncio
    async def test_add_segments_llm_failure_graceful(self) -> None:
        """LLMプロバイダー取得失敗時: 元のセグメントが返される (graceful degradation)。"""
        segs = [{"content": "テスト", "key_points": []}]
        validation = SegmentValidationResult(
            status="too_short", segment_count=1, estimated_duration=10,
            target_duration=300, ratio=0.03, expected_min=3, expected_max=10,
            suggestion="add_segments",
        )

        with patch("core.llm_provider.create_llm_provider", side_effect=ImportError("no provider")):
            result = await _expand_segments(segs, validation, "topic", None)

        assert result is segs

    @pytest.mark.asyncio
    async def test_add_segments_llm_bad_json(self) -> None:
        """LLMが不正なJSONを返した場合: 元のセグメントが返される。"""
        segs = [{"content": "テスト", "key_points": []}]
        validation = SegmentValidationResult(
            status="too_short", segment_count=1, estimated_duration=10,
            target_duration=300, ratio=0.03, expected_min=3, expected_max=10,
            suggestion="add_segments",
        )

        mock_provider = AsyncMock()
        mock_provider.generate_text.return_value = "not valid json at all"

        with patch("core.llm_provider.create_llm_provider", return_value=mock_provider):
            result = await _expand_segments(segs, validation, "topic", None)

        assert result is segs

    @pytest.mark.asyncio
    async def test_add_segments_llm_returns_non_list(self) -> None:
        """LLMがオブジェクトを返した場合: 元のセグメントが返される。"""
        segs = [{"content": "テスト", "key_points": []}]
        validation = SegmentValidationResult(
            status="too_short", segment_count=1, estimated_duration=10,
            target_duration=300, ratio=0.03, expected_min=3, expected_max=10,
            suggestion="add_segments",
        )

        mock_provider = AsyncMock()
        mock_provider.generate_text.return_value = '{"not": "a list"}'

        with patch("core.llm_provider.create_llm_provider", return_value=mock_provider):
            result = await _expand_segments(segs, validation, "topic", None)

        assert result is segs

    @pytest.mark.asyncio
    async def test_trim_suggestion_routes_to_merge(self) -> None:
        """trim_segments suggestion が _merge_short_segments にルーティングされる。"""
        segs = [
            {"content": "短い", "speaker": "H1", "key_points": []},
            {"content": "テスト" * 50, "speaker": "H2", "key_points": ["a"]},
            {"content": "テスト" * 50, "speaker": "H1", "key_points": ["b"]},
        ]
        validation = SegmentValidationResult(
            status="too_long", segment_count=3, estimated_duration=600,
            target_duration=300, ratio=2.0, expected_min=1, expected_max=2,
            suggestion="trim_segments",
        )
        result = await adjust_segments(segs, validation)
        assert len(result) <= 2
