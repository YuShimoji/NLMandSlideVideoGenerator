"""TranscriptProcessor テスト

テスト対象:
  - TranscriptSegment / TranscriptInfo データクラス
  - TranscriptProcessor.parse_transcript_text() テキストパース
  - TranscriptProcessor.save_transcript() / load_transcript() 保存/読込
  - TranscriptProcessor._seconds_to_srt_time() SRT変換
  - TranscriptProcessor._save_as_srt() SRT保存

削除済みシミュレーションメソッドのテストは撤去:
  _extract_key_points, _generate_slide_suggestion, _generate_title_from_content,
  _check_time_consistency, _calculate_transcript_accuracy, _fix_segment_consistency,
  _structure_transcript, _verify_and_correct_transcript, _correct_low_accuracy_transcript,
  process_audio, process_transcript
"""
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# settings モックを設定してからインポート
_mock_settings = MagicMock()
_mock_settings.TRANSCRIPTS_DIR = MagicMock()

with patch.dict("sys.modules", {
    "config": MagicMock(),
    "config.settings": MagicMock(settings=_mock_settings),
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
        assert TranscriptProcessor._seconds_to_srt_time(0) == "00:00:00,000"

    def test_normal(self):
        assert TranscriptProcessor._seconds_to_srt_time(65.5) == "00:01:05,500"

    def test_hours(self):
        assert TranscriptProcessor._seconds_to_srt_time(3661.0) == "01:01:01,000"

    def test_milliseconds(self):
        assert TranscriptProcessor._seconds_to_srt_time(1.123) == "00:00:01,123"


class TestParseTranscriptText:
    def test_valid_transcript(self):
        proc = TranscriptProcessor(output_dir=Path("/tmp"))
        raw = "[00:00] Speaker1: こんにちは\n[00:15] Speaker2: はい"
        segments = proc.parse_transcript_text(raw)
        assert len(segments) == 2
        assert segments[0].speaker == "Speaker1"
        assert segments[0].start_time == 0
        assert segments[1].start_time == 15

    def test_empty_input(self):
        proc = TranscriptProcessor(output_dir=Path("/tmp"))
        assert proc.parse_transcript_text("") == []

    def test_no_match_lines(self):
        proc = TranscriptProcessor(output_dir=Path("/tmp"))
        assert proc.parse_transcript_text("これはタイムスタンプなし") == []

    def test_end_time_adjusted(self):
        proc = TranscriptProcessor(output_dir=Path("/tmp"))
        raw = "[00:00] A: first\n[00:30] B: second\n[01:00] A: third"
        segments = proc.parse_transcript_text(raw)
        assert segments[0].end_time == 30
        assert segments[1].end_time == 60

    def test_segment_ids_sequential(self):
        proc = TranscriptProcessor(output_dir=Path("/tmp"))
        raw = "[00:00] A: first\n[00:30] B: second"
        segments = proc.parse_transcript_text(raw)
        assert segments[0].id == 1
        assert segments[1].id == 2


class TestSaveAndLoadTranscript:
    @pytest.mark.asyncio
    async def test_save_creates_files(self, tmp_path):
        proc = TranscriptProcessor(output_dir=tmp_path)
        segments = [
            _make_segment(start_time=0, end_time=15, text="テスト1"),
            _make_segment(start_time=15, end_time=30, text="テスト2"),
        ]
        transcript = _make_transcript(segments=segments)
        json_path = await proc.save_transcript(transcript)
        assert json_path.exists()
        srt_files = list(tmp_path.glob("*.srt"))
        assert len(srt_files) == 1

    @pytest.mark.asyncio
    async def test_save_as_srt_format(self, tmp_path):
        proc = TranscriptProcessor(output_dir=tmp_path)
        segments = [
            _make_segment(id=1, start_time=0, end_time=15, text="Line 1"),
            _make_segment(id=2, start_time=15, end_time=30, text="Line 2"),
        ]
        transcript = _make_transcript(segments=segments)
        srt_path = tmp_path / "test.srt"
        proc._save_as_srt(transcript, srt_path)
        content = srt_path.read_text(encoding="utf-8")
        assert "1\n" in content
        assert "00:00:00,000 --> 00:00:15,000" in content
        assert "Line 1" in content

    @pytest.mark.asyncio
    async def test_load_transcript(self, tmp_path):
        proc = TranscriptProcessor(output_dir=tmp_path)
        segments = [
            _make_segment(start_time=0, end_time=15, text="Test"),
        ]
        transcript = _make_transcript(segments=segments)
        json_path = await proc.save_transcript(transcript)
        loaded = await proc.load_transcript(json_path)
        assert loaded.title == "テスト台本"
        assert len(loaded.segments) == 1
        assert loaded.segments[0].text == "Test"
