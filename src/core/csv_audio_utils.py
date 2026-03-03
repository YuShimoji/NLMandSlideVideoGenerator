"""CSV パイプライン用音声ユーティリティ

行ごとの WAV ファイルの検索・解析・結合を行う純粋関数群。
pipeline.py の run_csv_timeline() から抽出。
"""
from __future__ import annotations

import wave
from pathlib import Path
from typing import List

from notebook_lm.audio_generator import AudioInfo
from .utils.logger import logger


def wav_sort_key(path: Path) -> tuple[int, int, str]:
    """WAV ファイルを数値優先でソートするキー関数"""
    stem = path.stem
    if stem.isdigit():
        return (0, int(stem), stem)
    head_digits = ""
    for ch in stem:
        if ch.isdigit():
            head_digits += ch
        else:
            break
    if head_digits:
        return (0, int(head_digits), stem)
    return (1, 0, stem)


def find_audio_files(directory: Path) -> List[Path]:
    """WAV ファイルを数値順でソートして返す（001.wav, 002.wav, ... を期待）"""
    files = sorted(directory.glob("*.wav"), key=wav_sort_key)
    logger.info(f"WAV検索結果: {len(files)}個見つかりました (dir={directory})")
    for f in files[:10]:
        logger.info(f"  - {f.name}")
    if len(files) > 10:
        logger.info(f"  ... 他 {len(files) - 10} 個")
    return files


def build_audio_segments(audio_files: List[Path]) -> List[AudioInfo]:
    """WAV ファイル群から AudioInfo リストを構築"""
    segments: List[AudioInfo] = []
    for path in audio_files:
        try:
            with wave.open(str(path), "rb") as wf:
                frames = wf.getnframes()
                framerate = wf.getframerate() or 1
                duration = frames / float(framerate)
            segments.append(AudioInfo(file_path=path, duration=duration))
        except (wave.Error, EOFError, OSError, AttributeError, TypeError, ValueError) as e:
            logger.warning(f"WAV解析に失敗しました: {path} ({e})")
            segments.append(AudioInfo(file_path=path, duration=1.0))
        except Exception as e:
            logger.warning(f"WAV解析に失敗しました: {path} ({e})")
            segments.append(AudioInfo(file_path=path, duration=1.0))
    return segments


def combine_wav_files(input_files: List[Path], output_path: Path) -> float:
    """複数 WAV を結合して1つの WAV を生成し、合計 duration を返す"""
    if not input_files:
        raise ValueError("入力 WAV がありません")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_frames = 0
    params = None

    for path in input_files:
        with wave.open(str(path), "rb") as wf:
            if params is None:
                params = wf.getparams()
            else:
                if wf.getparams()[:3] != params[:3]:
                    raise RuntimeError(f"WAV フォーマットが一致しません: {path}")
            total_frames += wf.getnframes()

    assert params is not None

    with wave.open(str(output_path), "wb") as out_wf:
        out_wf.setparams(params)
        for path in input_files:
            with wave.open(str(path), "rb") as in_wf:
                frames = in_wf.readframes(in_wf.getnframes())
                out_wf.writeframes(frames)

    framerate = params.framerate or 1
    duration = total_frames / float(framerate)
    return duration
