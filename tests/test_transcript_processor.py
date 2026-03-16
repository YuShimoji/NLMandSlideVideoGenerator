"""TranscriptProcessor テスト"""
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

# settings / audio_generator モックを設定してからインポート
_mock_settings = MagicMock()
_mock_settings.NOTEBOOK_LM_SETTINGS = {"transcript_accuracy_threshold": 0.8}
_mock_settings.TRANSCRIPTS_DIR = MagicMock()

with patch.dict("sys.modules", {
    "config": MagicMock(),
    "config.settings": MagicMock(settings=_mock_settings),
    "notebook_lm.source_collector": MagicMock(),
    "notebook_lm.audio_generator": MagicMock(AudioInfo=MagicMock),
}):
    from notebook_lm.transcript_processor import (
        TranscriptSegment,
        TranscriptInfo,
        TranscriptProcessor,
    )


def _make_segment(
    id: int = 1,
    start_time: float = 0.0,
    end_time: float = 15.0,
    speaker: str = "Host1",
    text: str = "テストテキスト",
    key_points: list | None = None,
    slide_suggestion: str = "",
    confidence_score: float = 0.95,
) -> TranscriptSegment:
    return TranscriptSegment(
        id=id,
        start_time=start_time,
        end_time=end_time,
        speaker=speaker,
        text=text,
        key_points=key_points or [],
        slide_suggestion=slide_suggestion,
        confidence_score=confidence_score,
    )


def _make_transcript(segments=None, accuracy=0.95) -> TranscriptInfo:
    return TranscriptInfo(
        title="テスト台本",
        total_duration=300.0,
        segments=segments or [],
        accuracy_score=accuracy,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        source_audio_path="/tmp/test.wav",
    )


class TestTranscriptSegmentDataclass:
    def test_creation(self):
        seg = _make_segment(id=1, text="hello")
        assert seg.id == 1
        assert seg.text == "hello"

    def test_key_points_default(self):
        seg = _make_segment()
        assert seg.key_points == []


class TestTranscriptInfoDataclass:
    def test_creation(self):
        t = _make_transcript()
        assert t.title == "テスト台本"
        assert t.total_duration == 300.0

    def test_with_segments(self):
        segs = [_make_segment(id=1), _make_segment(id=2)]
        t = _make_transcript(segments=segs)
        assert len(t.segments) == 2


class TestSecondsToSrtTime:
    def test_zero(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        assert proc._seconds_to_srt_time(0) == "00:00:00,000"

    def test_normal(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        assert proc._seconds_to_srt_time(65.5) == "00:01:05,500"

    def test_hours(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        assert proc._seconds_to_srt_time(3661.0) == "01:01:01,000"

    def test_milliseconds(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        assert proc._seconds_to_srt_time(1.123) == "00:00:01,123"


class TestExtractKeyPoints:
    def test_tech_terms(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        result = proc._extract_key_points("AI技術とデータ分析について")
        assert any("AI" in k for k in result)

    def test_no_match(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        result = proc._extract_key_points("今日の天気は晴れです")
        assert result == []

    def test_max_3(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        result = proc._extract_key_points(
            "AI人工知能の機械学習データアルゴリズムモデル学習技術システムプラットフォームツール"
        )
        assert len(result) <= 3

    def test_deduplication(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        result = proc._extract_key_points("AIとAIとAIの技術")
        # "AI"は重複除去される
        assert result.count("AI") <= 1


class TestGenerateSlideSuggestion:
    def test_with_key_points(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        result = proc._generate_slide_suggestion("テキスト", ["AI", "ML"])
        assert "AI" in result
        assert "ML" in result

    def test_no_key_points_short(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        result = proc._generate_slide_suggestion("短いテキスト", [])
        assert result == "短いテキスト"

    def test_no_key_points_long(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        long_text = "あ" * 150
        result = proc._generate_slide_suggestion(long_text, [])
        assert result.endswith("...")
        assert len(result) <= 104  # 100 + "..."


class TestGenerateTitleFromContent:
    def test_empty_segments(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        assert proc._generate_title_from_content([]) == "解説動画"

    def test_with_key_points(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        segments = [
            _make_segment(key_points=["AI"]),
            _make_segment(key_points=["AI", "ML"]),
        ]
        title = proc._generate_title_from_content(segments)
        assert "AI" in title
        assert "解説" in title

    def test_no_key_points(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        segments = [_make_segment(key_points=[])]
        title = proc._generate_title_from_content(segments)
        assert title == "解説動画"


class TestParseTranscriptSegments:
    def test_valid_transcript(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        raw = "[00:00] Speaker1: こんにちは\n[00:15] Speaker2: はい"
        segments = proc._parse_transcript_segments(raw)
        assert len(segments) == 2
        assert segments[0].speaker == "Speaker1"
        assert segments[0].start_time == 0
        assert segments[1].start_time == 15

    def test_empty_input(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        assert proc._parse_transcript_segments("") == []

    def test_no_match_lines(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        assert proc._parse_transcript_segments("これはタイムスタンプなし") == []

    def test_end_time_adjusted(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        raw = "[00:00] A: first\n[00:30] B: second\n[01:00] A: third"
        segments = proc._parse_transcript_segments(raw)
        # 最初のセグメントのend_timeは次のstart_timeに調整
        assert segments[0].end_time == 30
        assert segments[1].end_time == 60

    def test_segment_ids_sequential(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        raw = "[00:00] A: first\n[00:30] B: second"
        segments = proc._parse_transcript_segments(raw)
        assert segments[0].id == 1
        assert segments[1].id == 2

    def test_key_points_extracted(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        raw = "[00:00] A: AI技術とデータの解説"
        segments = proc._parse_transcript_segments(raw)
        assert len(segments) == 1
        assert len(segments[0].key_points) > 0


class TestCheckTimeConsistency:
    def test_single_segment(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        assert proc._check_time_consistency([_make_segment()]) == 1.0

    def test_consistent_segments(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        segments = [
            _make_segment(start_time=0, end_time=15),
            _make_segment(start_time=15, end_time=30),
            _make_segment(start_time=30, end_time=45),
        ]
        assert proc._check_time_consistency(segments) == 1.0

    def test_inconsistent_segments(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        segments = [
            _make_segment(start_time=0, end_time=10),
            _make_segment(start_time=20, end_time=30),  # gap of 10s
        ]
        assert proc._check_time_consistency(segments) == 0.0

    def test_within_tolerance(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        segments = [
            _make_segment(start_time=0, end_time=15),
            _make_segment(start_time=15.5, end_time=30),  # 0.5s gap
        ]
        assert proc._check_time_consistency(segments) == 1.0


class TestCalculateTranscriptAccuracy:
    def test_empty_segments(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        transcript = _make_transcript(segments=[])
        assert proc._calculate_transcript_accuracy(transcript) == 0.0

    def test_perfect_score(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        segments = [
            _make_segment(start_time=0, end_time=15, confidence_score=1.0),
            _make_segment(start_time=15, end_time=30, confidence_score=1.0),
        ]
        transcript = _make_transcript(segments=segments)
        accuracy = proc._calculate_transcript_accuracy(transcript)
        assert accuracy == 1.0

    def test_mixed_scores(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        segments = [
            _make_segment(start_time=0, end_time=15, confidence_score=0.9),
            _make_segment(start_time=15, end_time=30, confidence_score=0.7),
        ]
        transcript = _make_transcript(segments=segments)
        accuracy = proc._calculate_transcript_accuracy(transcript)
        # avg_confidence = 0.8, time_consistency = 1.0 → (0.8+1.0)/2 = 0.9
        assert accuracy == pytest.approx(0.9)


class TestFixSegmentConsistency:
    def test_no_overlap(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        segments = [
            _make_segment(start_time=0, end_time=15),
            _make_segment(start_time=15, end_time=30),
        ]
        transcript = _make_transcript(segments=segments)
        result = proc._fix_segment_consistency(transcript)
        assert result.segments[0].end_time == 15
        assert result.segments[1].start_time == 15

    def test_overlap_fixed(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        segments = [
            _make_segment(start_time=0, end_time=20),
            _make_segment(start_time=10, end_time=30),
        ]
        transcript = _make_transcript(segments=segments)
        result = proc._fix_segment_consistency(transcript)
        # mid_time = (0 + 30) / 2 = 15
        assert result.segments[0].end_time == 15
        assert result.segments[1].start_time == 15

    def test_empty_segments(self):
        proc = TranscriptProcessor.__new__(TranscriptProcessor)
        transcript = _make_transcript(segments=[])
        result = proc._fix_segment_consistency(transcript)
        assert result.segments == []
