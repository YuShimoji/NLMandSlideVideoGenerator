"""ContentSplitter テスト"""
from unittest.mock import patch, MagicMock

import pytest

# TranscriptSegment のモックを先に用意
_mock_segment_cls = MagicMock()


def _make_segment(
    id: int = 0,
    text: str = "テスト",
    speaker: str = "Host1",
    start_time: float = 0.0,
    end_time: float = 5.0,
    key_points: list | None = None,
):
    seg = MagicMock()
    seg.id = id
    seg.text = text
    seg.speaker = speaker
    seg.start_time = start_time
    seg.end_time = end_time
    seg.key_points = key_points or []
    seg.slide_suggestion = None
    return seg


# settings モックを設定してからインポート
_mock_settings = MagicMock()
_mock_settings.SLIDES_SETTINGS = {"max_chars_per_slide": 200}

with patch.dict("sys.modules", {
    "config": MagicMock(),
    "config.settings": MagicMock(settings=_mock_settings),
    "notebook_lm": MagicMock(),
    "notebook_lm.transcript_processor": MagicMock(
        TranscriptInfo=MagicMock,
        TranscriptSegment=MagicMock,
    ),
}):
    from slides.content_splitter import ContentSplitter, SplitContent


class TestContentSplitterInit:
    def test_max_chars_from_settings(self):
        splitter = ContentSplitter()
        assert splitter.max_chars_per_slide == 200


class TestTopicChange:
    def test_no_key_points_no_change(self):
        splitter = ContentSplitter()
        s1 = _make_segment(key_points=[])
        s2 = _make_segment(key_points=[])
        assert splitter._is_topic_change(s1, s2) is False

    def test_same_key_points_no_change(self):
        splitter = ContentSplitter()
        s1 = _make_segment(key_points=["AI", "ML"])
        s2 = _make_segment(key_points=["AI", "ML"])
        assert splitter._is_topic_change(s1, s2) is False

    def test_different_key_points_is_change(self):
        splitter = ContentSplitter()
        s1 = _make_segment(key_points=["AI", "ML"])
        s2 = _make_segment(key_points=["blockchain", "crypto"])
        assert splitter._is_topic_change(s1, s2) is True

    def test_partial_overlap_below_threshold(self):
        splitter = ContentSplitter()
        s1 = _make_segment(key_points=["AI", "ML", "deep"])
        s2 = _make_segment(key_points=["AI", "web", "cloud", "api"])
        # 1 common / 6 total = 0.167 < 0.3 → topic change
        assert splitter._is_topic_change(s1, s2) is True


class TestSpeakerChangeSignificant:
    def test_same_speaker_not_significant(self):
        splitter = ContentSplitter()
        s1 = _make_segment(speaker="Host1", start_time=0.0)
        s2 = _make_segment(speaker="Host1", start_time=10.0)
        assert splitter._is_speaker_change_significant(s1, s2) is False

    def test_different_speaker_short_gap_not_significant(self):
        splitter = ContentSplitter()
        s1 = _make_segment(speaker="Host1", start_time=0.0)
        s2 = _make_segment(speaker="Host2", start_time=10.0)
        assert splitter._is_speaker_change_significant(s1, s2) is False

    def test_different_speaker_long_gap_significant(self):
        splitter = ContentSplitter()
        s1 = _make_segment(speaker="Host1", start_time=0.0)
        s2 = _make_segment(speaker="Host2", start_time=40.0)
        assert splitter._is_speaker_change_significant(s1, s2) is True


class TestTimeGapSignificant:
    def test_small_gap_not_significant(self):
        splitter = ContentSplitter()
        s1 = _make_segment(end_time=10.0)
        s2 = _make_segment(start_time=12.0)
        assert splitter._is_time_gap_significant(s1, s2) is False

    def test_large_gap_significant(self):
        splitter = ContentSplitter()
        s1 = _make_segment(end_time=10.0)
        s2 = _make_segment(start_time=20.0)
        assert splitter._is_time_gap_significant(s1, s2) is True


class TestGroupSegmentsLogically:
    def test_empty_segments(self):
        splitter = ContentSplitter()
        result = splitter._group_segments_logically([])
        assert result == []

    def test_single_segment(self):
        splitter = ContentSplitter()
        s = _make_segment(id=1)
        result = splitter._group_segments_logically([s])
        assert len(result) == 1
        assert result[0] == [s]

    def test_continuous_segments_grouped(self):
        splitter = ContentSplitter()
        segments = [
            _make_segment(id=i, start_time=i * 3.0, end_time=(i + 1) * 3.0,
                          speaker="Host1", key_points=["AI"])
            for i in range(3)
        ]
        result = splitter._group_segments_logically(segments)
        assert len(result) == 1


class TestGenerateSlideTitle:
    def test_title_from_key_points(self):
        splitter = ContentSplitter()
        s = _make_segment(text="some text")
        title = splitter._generate_slide_title([s], ["Important Point"])
        assert title == "Important Point"

    def test_title_from_text_no_key_points(self):
        splitter = ContentSplitter()
        s = _make_segment(text="短い文。")
        title = splitter._generate_slide_title([s], [])
        assert title == "短い文"

    def test_title_truncation(self):
        splitter = ContentSplitter()
        long_text = "あ" * 100
        s = _make_segment(text=long_text)
        title = splitter._generate_slide_title([s], [])
        assert len(title) <= 40  # 30 + "..."


class TestExtractConcreteTerms:
    def test_katakana_extraction(self):
        splitter = ContentSplitter()
        terms = splitter._extract_concrete_terms("テクノロジーの発展")
        assert any("テクノロジー" in t for t in terms)

    def test_english_proper_nouns(self):
        splitter = ContentSplitter()
        terms = splitter._extract_concrete_terms("Google Chrome is popular")
        assert any("Google" in t for t in terms)

    def test_empty_text(self):
        splitter = ContentSplitter()
        terms = splitter._extract_concrete_terms("")
        assert terms == []


class TestCalculateContentImportance:
    def test_no_key_points_low_score(self):
        splitter = ContentSplitter()
        content = SplitContent(
            slide_id=1, title="T", text="short", key_points=[],
            duration=5.0, source_segments=[0], image_suggestions=[], speakers=["A"],
        )
        score = splitter._calculate_content_importance(content)
        assert score >= 0

    def test_rich_content_higher_score(self):
        splitter = ContentSplitter()
        poor = SplitContent(
            slide_id=1, title="T", text="x", key_points=[],
            duration=5.0, source_segments=[0], image_suggestions=[], speakers=["A"],
        )
        rich = SplitContent(
            slide_id=2, title="T", text="x" * 100, key_points=["a", "b", "c"],
            duration=15.0, source_segments=[0, 1], image_suggestions=[], speakers=["A"],
        )
        assert splitter._calculate_content_importance(rich) > splitter._calculate_content_importance(poor)


class TestConvertToSlideFormat:
    def test_dict_keys(self):
        splitter = ContentSplitter()
        content = SplitContent(
            slide_id=1, title="Title", text="Text", key_points=["kp"],
            duration=10.0, source_segments=[0], image_suggestions=["img"], speakers=["Host1"],
        )
        result = splitter._convert_to_slide_format([content])
        assert len(result) == 1
        d = result[0]
        assert d["slide_id"] == 1
        assert d["title"] == "Title"
        assert d["text"] == "Text"
        assert d["key_points"] == ["kp"]
        assert d["duration"] == 10.0
        assert d["speakers"] == ["Host1"]


class TestReduceToMaxSlides:
    def test_already_under_limit(self):
        splitter = ContentSplitter()
        contents = [
            SplitContent(slide_id=i, title=f"T{i}", text="text", key_points=[],
                         duration=5.0, source_segments=[i], image_suggestions=[], speakers=["A"])
            for i in range(3)
        ]
        result = splitter._reduce_to_max_slides(contents, 5)
        assert len(result) == 3

    def test_reduces_to_limit(self):
        splitter = ContentSplitter()
        contents = [
            SplitContent(slide_id=i, title=f"T{i}", text="text" * 30, key_points=["a"] * i,
                         duration=15.0, source_segments=[i], image_suggestions=[], speakers=["A"])
            for i in range(5)
        ]
        result = splitter._reduce_to_max_slides(contents, 3)
        assert len(result) == 3
