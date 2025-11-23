#!/usr/bin/env python3
"""CSVタイムライン分割の可視化スクリプト

- CSV: A列=話者名, B列=テキスト
- 行ごと音声ファイルから TranscriptInfo を生成し、ContentSplitter でスライド分割。
- CSV行 / TranscriptSegment / スライドの対応をコンソールに出力する。

主に P10 (CSVタイムラインモード) の分割挙動を確認するためのツール。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# プロジェクトルートと src 配下をパスに追加
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from core.utils.logger import logger
from config.settings import settings
from notebook_lm.audio_generator import AudioInfo
from notebook_lm.csv_transcript_loader import CsvTranscriptLoader
from notebook_lm.transcript_processor import TranscriptInfo
from slides.content_splitter import ContentSplitter


def _find_audio_files(audio_dir: Path) -> List[Path]:
    """音声ディレクトリから音声ファイル一覧を取得

    現状は WAV のみを正式サポートとし、その他拡張子は無視します。
    ファイル名順にソートして返します。
    """
    patterns = ["*.wav"]
    files: List[Path] = []
    for pat in patterns:
        files.extend(sorted(audio_dir.glob(pat)))
    # 重複除去 + ソート
    return sorted(set(files))


def _build_audio_segments(audio_files: List[Path]) -> List[AudioInfo]:
    """音声ファイル一覧から AudioInfo リストを生成

    WAV ファイルのメタデータから duration を取得し、AudioInfo(file_path, duration) を構築する。
    それ以外の拡張子の場合は、現在はスキップする。
    """
    import wave

    segments: List[AudioInfo] = []
    for path in audio_files:
        if path.suffix.lower() != ".wav":
            logger.warning(f"WAV 以外の拡張子はスキップします: {path}")
            continue

        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            framerate = wf.getframerate() or 1
            duration = frames / float(framerate)
        segments.append(AudioInfo(file_path=path, duration=duration))
    return segments


def _truncate(text: str, max_len: int = 80) -> str:
    """長いテキストを適度にトリム"""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


async def inspect_timeline(
    csv_path: Path,
    audio_dir: Path,
    max_chars_per_slide: Optional[int] = None,
    max_slides: int = 50,
) -> Dict[str, Any]:
    """CSV + 行ごと音声からタイムライン分割を可視化するメイン処理

    Returns:
        Dict[str, Any]: TranscriptInfo / slide_contents / stats を含むサマリ辞書
    """
    csv_path = csv_path.expanduser().resolve()
    audio_dir = audio_dir.expanduser().resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
    if not audio_dir.exists():
        raise FileNotFoundError(f"音声ディレクトリが見つかりません: {audio_dir}")

    logger.info(f"[inspect] CSV: {csv_path}")
    logger.info(f"[inspect] Audio dir: {audio_dir}")

    audio_files = _find_audio_files(audio_dir)
    if not audio_files:
        raise RuntimeError(f"音声ファイル(WAV)が見つかりません (dir={audio_dir})")

    audio_segments = _build_audio_segments(audio_files)
    loader = CsvTranscriptLoader()
    transcript: TranscriptInfo = await loader.load_from_csv(csv_path, audio_segments=audio_segments)

    # ContentSplitter 用の max_chars_per_slide を一時的に上書き
    original_max_chars = settings.SLIDES_SETTINGS.get("max_chars_per_slide")
    effective_max_chars = original_max_chars
    try:
        if max_chars_per_slide is not None:
            logger.info(
                f"[inspect] max_chars_per_slide を一時的に上書き: {original_max_chars} -> {max_chars_per_slide}"
            )
            settings.SLIDES_SETTINGS["max_chars_per_slide"] = max_chars_per_slide
            effective_max_chars = max_chars_per_slide

        splitter = ContentSplitter()
        slide_contents = await splitter.split_for_slides(transcript, max_slides=max_slides)
    finally:
        # 設定を元に戻す
        settings.SLIDES_SETTINGS["max_chars_per_slide"] = original_max_chars

    # ---- コンソール出力 ----
    print("==== CSV Timeline Inspection ====")
    print(f"CSV: {csv_path}")
    print(f"Audio dir: {audio_dir}")
    print(f"Segments: {len(transcript.segments)}, total_duration≈{transcript.total_duration:.2f}s")
    print(f"Slides (after split): {len(slide_contents)}")
    print(f"max_chars_per_slide (effective): {effective_max_chars}")
    print()

    print("== Transcript Segments (per CSV row) ==")
    for seg in transcript.segments:
        duration = seg.end_time - seg.start_time
        text_preview = _truncate(seg.text, 100)
        print(
            f"- Row {seg.id}: speaker={seg.speaker}, start={seg.start_time:.2f}s, "
            f"end={seg.end_time:.2f}s, dur={duration:.2f}s"
        )
        print(f"    text: {text_preview}")
    print()

    print("== Slide Contents (ContentSplitter result) ==")
    for content in slide_contents:
        text = content.get("text", "") or ""
        speakers = content.get("speakers") or []
        src_segments = content.get("source_segments") or []
        duration = float(content.get("duration", 0.0) or 0.0)
        print(
            f"- Slide {content.get('slide_id')}: "
            f"duration≈{duration:.2f}s, chars={len(text)}, "
            f"segments={src_segments}"
        )
        if speakers:
            print(f"    speakers: {', '.join(speakers)}")
        title = content.get("title") or ""
        if title:
            print(f"    title: {title}")
        print(f"    text: {_truncate(text, 120)}")
    print()

    # max_chars_per_slide の影響に関する簡易サマリ
    if slide_contents:
        lengths = [len((c.get("text") or "")) for c in slide_contents]
        over_threshold = 0
        if effective_max_chars is not None:
            over_threshold = sum(1 for l in lengths if l > effective_max_chars)

        print("== Summary ==")
        print(f"- slides: {len(slide_contents)}")
        print(
            f"- text length per slide: min={min(lengths)}, max={max(lengths)}, "
            f"avg={sum(lengths) / len(lengths):.1f}"
        )
        if effective_max_chars is not None:
            print(f"- slides over max_chars_per_slide({effective_max_chars}): {over_threshold}")
    else:
        print("== Summary ==")
        print("- No slide contents generated.")

    return {
        "transcript": transcript,
        "slide_contents": slide_contents,
        "stats": {
            "num_segments": len(transcript.segments),
            "num_slides": len(slide_contents),
            "max_chars_per_slide": effective_max_chars,
        },
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CSVタイムライン分割の可視化")
    parser.add_argument("--csv", required=True, help="CSVファイルパス (A:話者名, B:テキスト)")
    parser.add_argument("--audio-dir", required=True, help="行ごとの音声ファイル(WAV)があるディレクトリ")
    parser.add_argument(
        "--max-chars-per-slide",
        type=int,
        help="スライド1枚あたりの最大文字数 (一時的に設定を上書き)",
    )
    parser.add_argument(
        "--max-slides",
        type=int,
        default=50,
        help="分割時の最大スライド数 (ContentSplitterに渡す上限)",
    )
    args = parser.parse_args(argv)

    csv_path = Path(args.csv)
    audio_dir = Path(args.audio_dir)
    max_chars = args.max_chars_per_slide
    max_slides = args.max_slides

    try:
        asyncio.run(
            inspect_timeline(
                csv_path=csv_path,
                audio_dir=audio_dir,
                max_chars_per_slide=max_chars,
                max_slides=max_slides,
            )
        )
        return 0
    except Exception as e:
        logger.error(f"CSVタイムライン可視化中にエラーが発生しました: {e}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
