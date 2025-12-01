#!/usr/bin/env python3
"""長尺音声ファイルを無音区間で自動分割するユーティリティ

- 入力: 単一のWAVファイル (16bit PCM)
- 出力: 無音区間で分割された複数のWAVファイル (001.wav, 002.wav, ...)

主に NotebookLM 等で生成した長尺音声を、CSVタイムライン用の
行ごと音声 (001.wav, 002.wav, ...) に近い形へ分割するための補助ツールです。

Example:
    python scripts/split_audio_by_silence.py \
        --input data/audio/long_episode.wav \
        --out-dir data/audio/episode01_split \
        --min-silence-sec 0.7 \
        --silence-threshold 0.02
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple, Optional
import wave

import numpy as np


def _detect_segments_by_silence(
    samples: np.ndarray,
    framerate: int,
    *,
    min_silence_sec: float = 0.7,
    silence_threshold: float = 0.02,
    window_ms: int = 10,
    min_segment_sec: float = 1.0,
) -> List[Tuple[int, int]]:
    """無音区間に基づいてセグメント境界を検出する

    Args:
        samples: モノラルの int16 サンプル配列
        framerate: サンプリングレート (Hz)
        min_silence_sec: この秒数以上続く無音を分割ポイントとみなす
        silence_threshold: 最大振幅に対する無音判定しきい値 (0.0〜1.0)
        window_ms: 振幅を評価するウィンドウ長 (ミリ秒)
        min_segment_sec: これ未満の短すぎるセグメントは隣接セグメントと結合

    Returns:
        List[Tuple[int, int]]: 各セグメントの (start_frame, end_frame)
    """
    if samples.size == 0:
        return []

    n_frames = samples.shape[0]
    max_amp = int(np.max(np.abs(samples)))
    if max_amp <= 0:
        # 全体が無音の場合は1セグメントとして扱う
        return [(0, n_frames)]

    silence_level = max_amp * float(max(0.0, min(silence_threshold, 1.0)))

    window_size = max(int(framerate * window_ms / 1000.0), 1)
    n_windows = (n_frames + window_size - 1) // window_size

    silent_flags: List[bool] = []
    for w in range(n_windows):
        start = w * window_size
        end = min(start + window_size, n_frames)
        window_max = int(np.max(np.abs(samples[start:end])))
        silent_flags.append(window_max <= silence_level)

    min_silence_windows = max(int(min_silence_sec * 1000.0 / window_ms), 1)

    boundaries: List[int] = [0]
    silent_run_start: Optional[int] = None

    for i, is_silent in enumerate(silent_flags):
        if is_silent:
            if silent_run_start is None:
                silent_run_start = i
        else:
            if silent_run_start is not None:
                run_len = i - silent_run_start
                if run_len >= min_silence_windows:
                    boundary_frame = silent_run_start * window_size
                    # 0 や 末尾と同一でなければ境界として追加
                    if 0 < boundary_frame < n_frames:
                        boundaries.append(boundary_frame)
                silent_run_start = None

    # 最後のフレームを終端に追加
    if boundaries[-1] != n_frames:
        boundaries.append(n_frames)

    # 境界からセグメントに変換
    segments: List[Tuple[int, int]] = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        if end > start:
            segments.append((start, end))

    if not segments:
        return []

    # 短すぎるセグメントは隣接セグメントと結合
    min_segment_frames = int(max(min_segment_sec, 0.0) * framerate)
    if min_segment_frames <= 0:
        return segments

    merged: List[Tuple[int, int]] = []
    cur_start, cur_end = segments[0]
    for start, end in segments[1:]:
        seg_len = cur_end - cur_start
        if seg_len < min_segment_frames:
            # 現在のセグメントが短すぎる場合は次と結合
            cur_end = end
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))

    # それでも短すぎる末尾が残る場合は前と結合
    if len(merged) >= 2:
        last_start, last_end = merged[-1]
        if last_end - last_start < min_segment_frames:
            prev_start, prev_end = merged[-2]
            merged[-2] = (prev_start, last_end)
            merged.pop()

    return merged


def split_audio_by_silence(
    input_path: Path,
    out_dir: Path,
    *,
    min_silence_sec: float = 0.7,
    silence_threshold: float = 0.02,
    min_segment_sec: float = 1.0,
    start_index: int = 1,
    window_ms: int = 10,
    dry_run: bool = False,
) -> List[Path]:
    """WAVファイルを無音区間で分割し、連番WAVとして書き出す

    Returns:
        List[Path]: 生成されたセグメントファイルのパス一覧
    """
    input_path = input_path.expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")

    with wave.open(str(input_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        if sampwidth != 2:
            raise ValueError("16bit PCM WAV のみサポートしています")
        raw = wf.readframes(n_frames)

    if n_frames == 0:
        return []

    samples = np.frombuffer(raw, dtype=np.int16)
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1).astype(np.int16)

    segments = _detect_segments_by_silence(
        samples,
        framerate,
        min_silence_sec=min_silence_sec,
        silence_threshold=silence_threshold,
        window_ms=window_ms,
        min_segment_sec=min_segment_sec,
    )

    if not segments:
        return []

    out_dir = out_dir.expanduser().resolve()
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    bytes_per_frame = n_channels * 2  # 16bit
    current_index = max(start_index, 1)
    output_paths: List[Path] = []

    for start_frame, end_frame in segments:
        if end_frame <= start_frame:
            continue
        segment_duration = (end_frame - start_frame) / float(framerate or 1)
        if segment_duration <= 0:
            continue

        filename = f"{current_index:03d}.wav"
        out_path = out_dir / filename
        output_paths.append(out_path)

        if not dry_run:
            start_byte = start_frame * bytes_per_frame
            end_byte = end_frame * bytes_per_frame
            segment_bytes = raw[start_byte:end_byte]

            with wave.open(str(out_path), "wb") as out_wf:
                out_wf.setnchannels(n_channels)
                out_wf.setsampwidth(2)
                out_wf.setframerate(framerate)
                out_wf.writeframes(segment_bytes)

        current_index += 1

    return output_paths


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="無音区間でWAVファイルを自動分割するツール")
    parser.add_argument("--input", required=True, help="入力WAVファイルパス (16bit PCM)")
    parser.add_argument("--out-dir", required=True, help="分割後のWAVを保存するディレクトリ")
    parser.add_argument(
        "--min-silence-sec",
        type=float,
        default=0.7,
        help="分割ポイントとみなす無音区間の最小長 (秒)",
    )
    parser.add_argument(
        "--silence-threshold",
        type=float,
        default=0.02,
        help="無音判定しきい値 (最大振幅に対する比率 0.0〜1.0)",
    )
    parser.add_argument(
        "--min-segment-sec",
        type=float,
        default=1.0,
        help="これ未満の短いセグメントは隣接セグメントと結合する (秒)",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="出力ファイルの開始インデックス (001.wav の 1 に相当)",
    )
    parser.add_argument(
        "--window-ms",
        type=int,
        default=10,
        help="無音検出に用いるウィンドウ長 (ミリ秒)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ファイルを書き出さず、検出結果の概要のみ表示",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)

    segments = split_audio_by_silence(
        input_path=input_path,
        out_dir=out_dir,
        min_silence_sec=float(args.min_silence_sec),
        silence_threshold=float(args.silence_threshold),
        min_segment_sec=float(args.min_segment_sec),
        start_index=int(args.start_index),
        window_ms=int(args.window_ms),
        dry_run=bool(args.dry_run),
    )

    print("==== split_audio_by_silence ====")
    print(f"Input   : {input_path}")
    print(f"Out dir : {out_dir}")
    print(f"Segments: {len(segments)}")
    if segments:
        print("-- details --")
        for idx, seg_path in enumerate(segments, start=1):
            print(f"  [{idx:02d}] {seg_path}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
