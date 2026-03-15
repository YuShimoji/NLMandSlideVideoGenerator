"""slide_builder テスト — 純粋関数群の単体テスト"""
from types import SimpleNamespace

import pytest

from core.slide_builder import (
    allocate_subslide_durations,
    build_slide_dict,
    expand_segment_into_slides,
    find_split_index,
    split_text_for_subslides,
)


# ---------------------------------------------------------------------------
# find_split_index
# ---------------------------------------------------------------------------
class TestFindSplitIndex:
    def test_short_text_returns_length(self):
        """テキストが preferred_length 以下なら全長を返す"""
        assert find_split_index("短い", 10) == 2

    def test_splits_at_period(self):
        """句点で分割"""
        text = "これはテスト文です。ここから次の文が始まります。"
        idx = find_split_index(text, 10)
        assert text[idx - 1] == "。"

    def test_splits_at_comma_if_no_period(self):
        """読点で分割（句点なし）"""
        text = "aaaa、bbbb、ccccddddeeee"
        idx = find_split_index(text, 5)
        assert text[idx - 1] == "、"

    def test_fallback_to_preferred_length(self):
        """句読点なしの場合は preferred_length で切る"""
        text = "a" * 100
        assert find_split_index(text, 30) == 30

    def test_ignores_early_punctuation(self):
        """preferred_length の 60% 未満の句読点は無視"""
        text = "a。" + "b" * 100
        idx = find_split_index(text, 50)
        # 位置 1 は 50*0.6=30 未満なので無視される
        assert idx == 50


# ---------------------------------------------------------------------------
# split_text_for_subslides
# ---------------------------------------------------------------------------
class TestSplitTextForSubslides:
    def test_empty_text(self):
        assert split_text_for_subslides("", 10, 3) == [""]

    def test_short_text_no_split(self):
        """しきい値未満なら分割しない"""
        assert split_text_for_subslides("短いテキスト", 100, 3) == ["短いテキスト"]

    def test_splits_long_text(self):
        text = "a" * 30 + "。" + "b" * 30 + "。" + "c" * 30
        chunks = split_text_for_subslides(text, 35, 5)
        assert len(chunks) >= 2
        joined = "".join(chunks)
        # 全文字が保存されている（空白除去あり）
        assert joined.replace(" ", "") == text.replace(" ", "")

    def test_max_subslides_limit(self):
        """max_subslides を超えない"""
        text = "a" * 200
        chunks = split_text_for_subslides(text, 10, 3)
        assert len(chunks) <= 3


# ---------------------------------------------------------------------------
# allocate_subslide_durations
# ---------------------------------------------------------------------------
class TestAllocateSubslideDurations:
    def test_single_chunk(self):
        durations = allocate_subslide_durations(10.0, ["hello"], 0.5)
        assert len(durations) == 1
        assert durations[0] == pytest.approx(10.0)

    def test_total_matches(self):
        chunks = ["aaaa", "bb", "cccccc"]
        durations = allocate_subslide_durations(12.0, chunks, 0.5)
        assert sum(durations) == pytest.approx(12.0)
        assert len(durations) == 3

    def test_proportional_allocation(self):
        """文字数に比例して配分"""
        chunks = ["a" * 10, "b" * 10]
        durations = allocate_subslide_durations(10.0, chunks, 0.5)
        assert durations[0] == pytest.approx(durations[1], abs=0.1)

    def test_min_duration_enforced(self):
        """最小デュレーションが保証される"""
        chunks = ["a", "b" * 100]
        durations = allocate_subslide_durations(2.0, chunks, 0.5)
        assert all(d >= 0.5 for d in durations)

    def test_zero_total_duration(self):
        """total_duration <= 0 の場合でも正の値を返す"""
        durations = allocate_subslide_durations(0.0, ["a", "b"], 0.5)
        assert all(d > 0 for d in durations)

    def test_many_chunks_total_preserved(self):
        chunks = [f"chunk{i}" * 5 for i in range(10)]
        durations = allocate_subslide_durations(30.0, chunks, 0.5)
        assert sum(durations) == pytest.approx(30.0)
        assert len(durations) == 10


# ---------------------------------------------------------------------------
# build_slide_dict
# ---------------------------------------------------------------------------
class TestBuildSlideDict:
    def _segment(self, **overrides):
        defaults = {"id": 1, "text": "テスト文章です", "speaker": "Host1"}
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def test_basic_fields(self):
        seg = self._segment()
        result = build_slide_dict(seg, slide_id=5, text="出力テキスト", duration=3.0, sub_index=0, sub_total=1)
        assert result["slide_id"] == 5
        assert result["text"] == "出力テキスト"
        assert result["duration"] == 3.0
        assert result["source_segments"] == [1]
        assert result["speakers"] == ["Host1"]
        assert result["is_continued"] is False

    def test_continued_slide(self):
        seg = self._segment()
        result = build_slide_dict(seg, slide_id=7, text="続き", duration=2.0, sub_index=1, sub_total=3)
        assert result["is_continued"] is True
        assert "続き" in result["title"]
        assert "2/3" in result["title"]

    def test_no_speaker(self):
        seg = self._segment(speaker=None)
        result = build_slide_dict(seg, slide_id=1, text="t", duration=1.0, sub_index=0, sub_total=1)
        assert result["speakers"] == []

    def test_slide_suggestion_used_as_title(self):
        seg = self._segment(slide_suggestion="カスタムタイトル")
        result = build_slide_dict(seg, slide_id=1, text="t", duration=1.0, sub_index=0, sub_total=1)
        assert result["title"] == "カスタムタイトル"

    def test_min_duration_clamped(self):
        seg = self._segment()
        result = build_slide_dict(seg, slide_id=1, text="t", duration=0.01, sub_index=0, sub_total=1)
        assert result["duration"] >= 0.1


# ---------------------------------------------------------------------------
# expand_segment_into_slides (統合テスト — settings依存)
# ---------------------------------------------------------------------------
class TestExpandSegmentIntoSlides:
    def _segment(self, text="短いテキスト", start=0.0, end=5.0, **kw):
        defaults = {"id": 1, "text": text, "start_time": start, "end_time": end, "speaker": "Host1"}
        defaults.update(kw)
        return SimpleNamespace(**defaults)

    def test_short_text_single_slide(self):
        seg = self._segment(text="短い", start=0.0, end=3.0)
        slides = expand_segment_into_slides(seg, start_slide_id=0)
        assert len(slides) == 1
        assert slides[0]["slide_id"] == 0

    def test_long_text_may_split(self):
        """settings の auto_split=True + threshold 超えで複数スライド"""
        long_text = "あ" * 200
        seg = self._segment(text=long_text, start=0.0, end=10.0)
        slides = expand_segment_into_slides(seg, start_slide_id=10)
        # デフォルト settings: threshold=120, target=60, max=3 → 分割されるはず
        assert len(slides) >= 2
        assert slides[0]["slide_id"] == 10

    def test_slide_ids_sequential(self):
        long_text = "い" * 200
        seg = self._segment(text=long_text, start=0.0, end=10.0)
        slides = expand_segment_into_slides(seg, start_slide_id=5)
        ids = [s["slide_id"] for s in slides]
        assert ids == list(range(5, 5 + len(slides)))

    def test_duration_sum_matches_segment(self):
        long_text = "う" * 200
        seg = self._segment(text=long_text, start=1.0, end=11.0)
        slides = expand_segment_into_slides(seg, start_slide_id=0)
        total = sum(s["duration"] for s in slides)
        assert total == pytest.approx(10.0, abs=0.5)
