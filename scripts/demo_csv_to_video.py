#!/usr/bin/env python3
"""CSV + 行ごと音声から動画まで生成するデモスクリプト

- CSV: A列=話者名, B列=テキスト
- 行ごとの WAV 音声を結合して1本の音声にし、TranscriptInfo のタイミングと同期
- SlideGenerator / VideoComposer を使って簡易動画を生成

P10 (CSVタイムラインモード) のエンドツーエンド確認用のモック寄りデモです。
本番運用前の接着テスト・ワークフロー検証に利用してください。
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
from config.settings import settings, create_directories
from notebook_lm.audio_generator import AudioInfo
from notebook_lm.csv_transcript_loader import CsvTranscriptLoader
from slides.slide_generator import SlideGenerator
from video_editor.video_composer import VideoComposer


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

    wave モジュールを用いて duration を取得し、AudioInfo(file_path, duration) を構築する。
    すべてのファイルは同一フォーマット（チャンネル数・サンプルレート等）である前提です。
    """
    import wave

    segments: List[AudioInfo] = []
    for path in audio_files:
        if path.suffix.lower() != ".wav":
            # 将来的に拡張する余地を残しつつ、現段階では明示的に制限
            logger.warning(f"WAV 以外の拡張子はスキップします: {path}")
            continue

        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            framerate = wf.getframerate() or 1
            duration = frames / float(framerate)
        segments.append(AudioInfo(file_path=path, duration=duration))
    return segments


def _combine_wav_files(input_files: List[Path], output_path: Path) -> float:
    """複数の WAV を結合して1本にする

    すべて同一フォーマット（チャンネル数・サンプルレート・サンプル幅）が前提。

    Returns:
        float: 結合後の総再生時間(秒)
    """
    import wave

    if not input_files:
        raise ValueError("入力 WAV がありません")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_frames = 0
    params = None

    # まず形式チェック + 総フレーム数計算
    for path in input_files:
        with wave.open(str(path), "rb") as wf:
            if params is None:
                params = wf.getparams()
            else:
                if wf.getparams()[:3] != params[:3]:  # nchannels, sampwidth, framerate
                    raise RuntimeError(f"WAV フォーマットが一致しません: {path}")
            total_frames += wf.getnframes()

    assert params is not None

    # 実際に書き出し
    with wave.open(str(output_path), "wb") as out_wf:
        out_wf.setparams(params)
        for path in input_files:
            with wave.open(str(path), "rb") as in_wf:
                frames = in_wf.readframes(in_wf.getnframes())
                out_wf.writeframes(frames)

    framerate = params.framerate or 1
    duration = total_frames / float(framerate)
    return duration


async def run_demo(
    csv_path: Path,
    audio_dir: Path,
    video_quality: str = "1080p",
    max_slides: int = 20,
) -> Path:
    """CSV + 行ごと WAV から動画を生成するメイン処理

    Returns:
        Path: 生成された動画ファイルパス
    """
    csv_path = csv_path.expanduser().resolve()
    audio_dir = audio_dir.expanduser().resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
    if not audio_dir.exists():
        raise FileNotFoundError(f"音声ディレクトリが見つかりません: {audio_dir}")

    logger.info(f"CSV: {csv_path}")
    logger.info(f"Audio dir: {audio_dir}")

    # 必要ディレクトリを作成
    create_directories()

    # 行ごとの WAV を読み込み
    audio_files = _find_audio_files(audio_dir)
    if not audio_files:
        raise RuntimeError(f"音声ファイル(WAV)が見つかりません (dir={audio_dir})")

    audio_segments = _build_audio_segments(audio_files)

    # TranscriptInfo を生成
    loader = CsvTranscriptLoader()
    transcript = await loader.load_from_csv(csv_path, audio_segments=audio_segments)

    # WAV を結合して1本の AudioInfo を作成
    combined_audio_path = settings.AUDIO_DIR / f"{csv_path.stem}_combined.wav"
    total_duration = _combine_wav_files(audio_files, combined_audio_path)
    audio_info = AudioInfo(
        file_path=combined_audio_path,
        duration=total_duration,
        quality_score=1.0,
        sample_rate=44100,
        file_size=combined_audio_path.stat().st_size if combined_audio_path.exists() else 0,
        language=settings.YOUTUBE_SETTINGS.get("default_audio_language", "ja"),
        channels=2,
    )

    # スライド生成
    slide_generator = SlideGenerator()
    slides_pkg = await slide_generator.generate_slides(transcript, max_slides=max_slides)

    # 動画合成
    video_composer = VideoComposer()
    video_info = await video_composer.compose_video(
        audio_file=audio_info,
        slides_file=slides_pkg,
        transcript=transcript,
        quality=video_quality,
    )

    logger.success(f"動画生成完了: {video_info.file_path}")
    return video_info.file_path


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CSV + 行ごと音声から動画を生成するデモ")
    parser.add_argument("--csv", required=True, help="CSVファイルパス (A:話者名, B:テキスト)")
    parser.add_argument("--audio-dir", required=True, help="行ごとの音声ファイル(WAV)があるディレクトリ")
    parser.add_argument(
        "--video-quality",
        choices=["1080p", "720p", "480p"],
        default="1080p",
        help="動画品質",
    )
    parser.add_argument(
        "--max-slides",
        type=int,
        default=20,
        help="最大スライド数",
    )

    args = parser.parse_args(argv)

    csv_path = Path(args.csv)
    audio_dir = Path(args.audio_dir)

    try:
        video_path = asyncio.run(
            run_demo(
                csv_path=csv_path,
                audio_dir=audio_dir,
                video_quality=args.video_quality,
                max_slides=args.max_slides,
            )
        )
        print(f"Generated video: {video_path}")
        return 0
    except (FileNotFoundError, OSError, ValueError, TypeError, RuntimeError) as e:
        logger.error(f"CSV→動画デモ実行中にエラーが発生しました: {e}")
        return 1
    except Exception as e:
        logger.error(f"CSV→動画デモ実行中にエラーが発生しました: {e}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
