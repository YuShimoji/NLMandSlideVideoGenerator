"""セグメント粒度制御テスト (SP-044)"""
import pytest

from core.segment_duration_validator import (
    estimate_segment_duration,
    validate_segments,
    _get_segment_range,
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
