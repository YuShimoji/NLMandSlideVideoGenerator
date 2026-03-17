#!/usr/bin/env python3
"""CSV台本ローダーのテスト"""

import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from notebook_lm.csv_transcript_loader import CsvTranscriptLoader
from notebook_lm.audio_generator import AudioInfo


@pytest.mark.asyncio
async def test_load_from_csv_with_audio_segments(tmp_path):
    """行ごとの AudioInfo がある場合、duration に基づき連続したタイミングが付与される"""
    csv_path = tmp_path / "test_timeline.csv"
    csv_path.write_text(
        "Speaker1,こんにちは\nSpeaker2,世界\n",
        encoding="utf-8",
    )

    loader = CsvTranscriptLoader()

    audio_segments = [
        AudioInfo(file_path=tmp_path / "a1.wav", duration=2.0),
        AudioInfo(file_path=tmp_path / "a2.wav", duration=3.0),
    ]

    transcript = await loader.load_from_csv(csv_path, audio_segments=audio_segments)

    assert len(transcript.segments) == 2
    assert transcript.total_duration == pytest.approx(5.0, rel=1e-3)

    first, second = transcript.segments
    assert first.speaker == "Speaker1"
    assert first.text == "こんにちは"
    assert first.start_time == pytest.approx(0.0, rel=1e-3)
    assert first.end_time == pytest.approx(2.0, rel=1e-3)

    assert second.speaker == "Speaker2"
    assert second.text == "世界"
    assert second.start_time == pytest.approx(2.0, rel=1e-3)
    assert second.end_time == pytest.approx(5.0, rel=1e-3)


@pytest.mark.asyncio
async def test_load_from_csv_with_duration_heuristics(tmp_path):
    """AudioInfo がなくてもテキスト長に基づき時間が自動配分される"""
    csv_path = tmp_path / "test_timeline2.csv"
    csv_path.write_text(
        "A,短い\nB,とてもとても長いテキストです\n",
        encoding="utf-8",
    )

    loader = CsvTranscriptLoader()

    # total_audio を与えておくと、その duration を全体時間として利用
    dummy_audio = AudioInfo(file_path=tmp_path / "total.wav", duration=12.0)

    transcript = await loader.load_from_csv(csv_path, total_audio=dummy_audio)

    assert len(transcript.segments) == 2
    assert transcript.total_duration == pytest.approx(12.0, rel=1e-3)

    first, second = transcript.segments
    # 1本目より2本目の方が長いテキストなので、表示時間も長いはず
    assert (second.end_time - second.start_time) > (first.end_time - first.start_time)


@pytest.mark.asyncio
async def test_empty_csv_returns_empty_transcript(tmp_path):
    """空CSVの場合、セグメントなしのTranscriptInfoが返る。"""
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")

    loader = CsvTranscriptLoader()
    transcript = await loader.load_from_csv(csv_path, title="empty test")

    assert len(transcript.segments) == 0
    assert transcript.title == "empty test"
    assert transcript.total_duration == 0.0


@pytest.mark.asyncio
async def test_skip_rows_with_insufficient_columns(tmp_path):
    """列数不足の行はスキップされる。"""
    csv_path = tmp_path / "bad_cols.csv"
    csv_path.write_text(
        "OnlyOneColumn\nSpeaker1,Valid text\n",
        encoding="utf-8",
    )

    loader = CsvTranscriptLoader()
    transcript = await loader.load_from_csv(csv_path)

    assert len(transcript.segments) == 1
    assert transcript.segments[0].text == "Valid text"


@pytest.mark.asyncio
async def test_skip_empty_text_rows(tmp_path):
    """テキスト列が空の行はスキップされる。"""
    csv_path = tmp_path / "empty_text.csv"
    csv_path.write_text(
        "Speaker1,\nSpeaker2,有効なテキスト\n",
        encoding="utf-8",
    )

    loader = CsvTranscriptLoader()
    transcript = await loader.load_from_csv(csv_path)

    assert len(transcript.segments) == 1
    assert transcript.segments[0].text == "有効なテキスト"


@pytest.mark.asyncio
async def test_skip_blank_rows(tmp_path):
    """完全空行はスキップされる。"""
    csv_path = tmp_path / "blank_rows.csv"
    csv_path.write_text(
        "Speaker1,テスト1\n\n  ,  \nSpeaker2,テスト2\n",
        encoding="utf-8",
    )

    loader = CsvTranscriptLoader()
    transcript = await loader.load_from_csv(csv_path)

    assert len(transcript.segments) == 2


@pytest.mark.asyncio
async def test_audio_segment_with_zero_duration(tmp_path):
    """audio_segment の duration が 0 の場合、テキスト長から推定する。"""
    csv_path = tmp_path / "zero_dur.csv"
    csv_path.write_text(
        "Speaker1,こんにちは世界\n",
        encoding="utf-8",
    )

    loader = CsvTranscriptLoader()
    audio_segments = [AudioInfo(file_path=tmp_path / "a.wav", duration=0.0)]

    transcript = await loader.load_from_csv(csv_path, audio_segments=audio_segments)

    assert len(transcript.segments) == 1
    # duration 0 なのでテキスト長ベースの推定が使われる
    seg = transcript.segments[0]
    assert seg.end_time > seg.start_time


@pytest.mark.asyncio
async def test_heuristic_no_total_audio(tmp_path):
    """total_audio なしの場合、テキスト長から全体時間を推定する。"""
    csv_path = tmp_path / "no_audio.csv"
    csv_path.write_text(
        "A,短い\nB,少し長いテキスト\n",
        encoding="utf-8",
    )

    loader = CsvTranscriptLoader()
    transcript = await loader.load_from_csv(csv_path)

    assert len(transcript.segments) == 2
    assert transcript.total_duration > 0


@pytest.mark.asyncio
async def test_heuristic_total_audio_no_duration(tmp_path):
    """total_audio はあるが duration が None の場合。"""
    csv_path = tmp_path / "no_dur.csv"
    csv_path.write_text(
        "A,テキスト1\nB,テキスト2\n",
        encoding="utf-8",
    )

    loader = CsvTranscriptLoader()
    dummy = AudioInfo(file_path=tmp_path / "x.wav", duration=None)  # type: ignore[arg-type]

    transcript = await loader.load_from_csv(csv_path, total_audio=dummy)

    assert len(transcript.segments) == 2
    assert transcript.total_duration > 0
