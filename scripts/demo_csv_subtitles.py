#!/usr/bin/env python3
"""CSV + 行ごと音声から字幕ファイルを生成するデモスクリプト

- CSV: A列=話者名, B列=テキスト
- 行ごとに分割された音声ファイルを読み込み、各行の duration から
  TranscriptSegment の start/end を決定
- 生成された TranscriptInfo を SubtitleGenerator に渡し、SRT/ASS/VTT を出力

主に P10 (CSVタイムラインモード) の挙動確認用の簡易デモ。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Optional

# プロジェクトルートと src 配下をパスに追加
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from core.utils.logger import logger

# src 配下モジュール
from config.settings import settings
from notebook_lm.audio_generator import AudioInfo
from notebook_lm.csv_transcript_loader import CsvTranscriptLoader
from video_editor.subtitle_generator import SubtitleGenerator


def _find_audio_files(audio_dir: Path) -> List[Path]:
    """音声ディレクトリから音声ファイル一覧を取得

    サポート形式: wav, mp3, m4a, flac, ogg
    ファイル名順にソートして返す。
    """
    patterns = ["*.wav", "*.mp3", "*.m4a", "*.flac", "*.ogg"]
    files: List[Path] = []
    for pat in patterns:
        files.extend(sorted(audio_dir.glob(pat)))
    return sorted(set(files))


def _build_audio_segments(audio_files: List[Path]) -> List[AudioInfo]:
    """音声ファイル一覧から AudioInfo リストを生成

    WAV ファイルのメタデータから duration を取得し、AudioInfo(file_path, duration) を構築する。
    それ以外の拡張子の場合は、現在はサポート外としてエラーにする。
    """
    
    segments: List[AudioInfo] = []
    for path in audio_files:
        if path.suffix.lower() != ".wav":
            raise RuntimeError(f"現在のデモは WAV ファイルのみサポートしています: {path}")

        import wave

        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            framerate = wf.getframerate() or 1
            duration = frames / float(framerate)
        segments.append(AudioInfo(file_path=path, duration=duration))
    return segments


async def run_demo(
    csv_path: Path,
    audio_dir: Path,
    output_dir: Optional[Path] = None,
    style: str = "default",
) -> Path:
    """CSV + 行ごと音声から字幕を生成するメイン処理

    Returns:
        Path: 生成された SRT ファイルパス
    """
    csv_path = csv_path.expanduser().resolve()
    audio_dir = audio_dir.expanduser().resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
    if not audio_dir.exists():
        raise FileNotFoundError(f"音声ディレクトリが見つかりません: {audio_dir}")

    logger.info(f"CSV: {csv_path}")
    logger.info(f"Audio dir: {audio_dir}")

    audio_files = _find_audio_files(audio_dir)
    if not audio_files:
        raise RuntimeError(f"音声ファイルが見つかりません (dir={audio_dir})")

    loader = CsvTranscriptLoader()
    audio_segments = _build_audio_segments(audio_files)

    # TranscriptInfo を生成（行数と音声数が一致しない場合は、
    # CsvTranscriptLoader 側でヒューリスティック配分にフォールバック）
    transcript = await loader.load_from_csv(csv_path, audio_segments=audio_segments)

    # 字幕生成
    subtitle_generator = SubtitleGenerator()
    if output_dir is not None:
        subtitle_generator.output_dir = output_dir
        subtitle_generator.output_dir.mkdir(parents=True, exist_ok=True)

    srt_path = await subtitle_generator.generate_subtitles(transcript, style=style)

    logger.success(f"字幕生成完了: {srt_path}")
    return srt_path


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CSV + 行ごと音声から字幕を生成するデモ")
    parser.add_argument("--csv", required=True, help="CSVファイルパス (A:話者名, B:テキスト)")
    parser.add_argument("--audio-dir", required=True, help="行ごとの音声ファイルがあるディレクトリ")
    parser.add_argument(
        "--output-dir",
        help="字幕ファイルの出力ディレクトリ (省略時は settings.TRANSCRIPTS_DIR)",
    )
    parser.add_argument(
        "--style",
        default="default",
        help="字幕スタイルプリセット名 (SubtitleGeneratorのプリセットを参照)",
    )

    args = parser.parse_args(argv)

    csv_path = Path(args.csv)
    audio_dir = Path(args.audio_dir)
    output_dir = Path(args.output_dir) if args.output_dir else None

    try:
        srt_path = asyncio.run(run_demo(csv_path, audio_dir, output_dir=output_dir, style=args.style))
        print(f"Generated subtitles (SRT): {srt_path}")
        return 0
    except (FileNotFoundError, OSError, ValueError, TypeError, RuntimeError) as e:
        logger.error(f"字幕デモ実行中にエラーが発生しました: {e}")
        return 1
    except Exception as e:
        logger.error(f"字幕デモ実行中にエラーが発生しました: {e}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
