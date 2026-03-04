import wave
from pathlib import Path
from typing import List, Tuple, Optional
from .logger import logger
from notebook_lm.audio_generator import AudioInfo

def wav_sort_key(path: Path) -> Tuple[int, int, str]:
    """WAVファイルのソートキー (001.wav, 002.wav... を正しく並べる)"""
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
    """ディレクトリ内のWAVファイルを検索しソートして返す"""
    files = sorted(directory.glob("*.wav"), key=wav_sort_key)
    logger.info(f"WAV検索結果: {len(files)}個見つかりました (dir={directory})")
    for f in files[:10]:
        logger.info(f"  - {f.name}")
    if len(files) > 10:
        logger.info(f"  ... 他 {len(files) - 10} 個")
    return files

def build_audio_segments(audio_files: List[Path]) -> List[AudioInfo]:
    """WAVファイル群からAudioInfoのリストを構築する"""
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
    """複数のWAVファイルを1つに結合する"""
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
