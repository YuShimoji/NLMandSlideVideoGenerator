#!/usr/bin/env python3
"""SofTalk / AquesTalk ローカル TTS バッチスクリプト

- タイムライン CSV (A列=話者, B列=テキスト) を読み込み
- 各データ行ごとに 1 音声ファイル (001.wav, 002.wav, ...) を生成するための
  コマンドライン呼び出しを行う補助ツール。

現時点では、実際の TTS 実行は環境依存となるため、
- `--dry-run` でコマンドラインのみを確認しつつ、
- 実行環境では環境変数 `SOFTALK_EXE` / `AQUESTALK_EXE` で実行ファイルパスを指定する
ことを前提とするテンプレート実装です。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# プロジェクトルートと src 配下をパスに追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.utils.logger import logger  # noqa: E402


def _load_timeline_rows(csv_path: Path, text_encoding: str = "utf-8") -> List[Tuple[str, str]]:
    """タイムライン CSV から (speaker, text) のタプル一覧を取得

    - 先頭行がヘッダと思われる場合 ("Speaker","Text" 等) はスキップする。
    - それ以外は全行をデータ行として扱い、空行もインデックスを維持したまま
      `(speaker, text)` を返す。
    """

    csv_path = csv_path.expanduser().resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")

    rows: List[List[str]] = []
    with csv_path.open("r", encoding=text_encoding, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        return []

    def _normalize_cell(cell: str) -> str:
        return (cell or "").strip().lower()

    first = rows[0] if rows else []
    first_norm = [_normalize_cell(c) for c in first[:2]]
    header_speaker = {"speaker", "話者"}
    header_text = {"text", "テキスト", "content"}
    has_header = len(first_norm) >= 2 and first_norm[0] in header_speaker and first_norm[1] in header_text

    data_rows = rows[1:] if has_header else rows

    result: List[Tuple[str, str]] = []
    for raw in data_rows:
        if not raw:
            result.append(("", ""))
            continue
        speaker = (raw[0] or "").strip()
        text = (raw[1] or "").strip() if len(raw) > 1 else ""
        result.append((speaker, text))
    return result


def _build_output_path(out_dir: Path, index: int) -> Path:
    """行番号から 3 桁ゼロ埋めの WAV ファイルパスを生成"""
    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{index:03d}.wav"
    return out_dir / file_name


def _load_speaker_voice_map(path: Path) -> Dict[str, Any]:
    """話者名 -> 声プリセットマップを JSON から読み込む

    JSON フォーマット例:

    {
      "Speaker1": {"softalk": "preset1", "aquestalk": "presetA"},
      "Speaker2": "common_preset",
      "*": {"softalk": "default_softalk"}
    }
    """

    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"speaker-map JSON が見つかりません: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("speaker-map JSON の最上位はオブジェクトである必要があります")

    return data


def _select_voice_preset(
    *,
    engine: str,
    speaker: str,
    default_preset: Optional[str],
    speaker_voice_map: Dict[str, Any],
) -> Optional[str]:
    """エンジン名と話者名から適用する声プリセットを選択"""

    if not speaker_voice_map:
        return default_preset

    speaker_key = (speaker or "").strip()
    entry = speaker_voice_map.get(speaker_key)
    if entry is None:
        entry = speaker_voice_map.get("*")

    if entry is None:
        return default_preset

    if isinstance(entry, str):
        return entry

    if isinstance(entry, dict):
        engine_value = entry.get(engine)
        if engine_value is not None:
            return engine_value
        fallback = entry.get("default")
        if isinstance(fallback, str):
            return fallback

    return default_preset


def _get_engine_executable(engine: str) -> Path:
    """エンジンごとの実行ファイルパスを環境変数から取得

    - softalk:   `SOFTALK_EXE`
    - aquestalk: `AQUESTALK_EXE`
    """

    if engine == "softalk":
        env_name = "SOFTALK_EXE"
    elif engine == "aquestalk":
        env_name = "AQUESTALK_EXE"
    else:
        raise ValueError(f"Unsupported engine: {engine}")

    exe = os.getenv(env_name)
    if not exe:
        raise RuntimeError(f"環境変数 {env_name} が設定されていません。実行ファイルパスを指定してください。")

    exe_path = Path(exe)
    if not exe_path.exists():
        raise FileNotFoundError(f"TTS 実行ファイルが見つかりません: {exe_path}")

    return exe_path


def _build_command(
    *,
    engine: str,
    exe_path: Path,
    text: str,
    output_path: Path,
    voice_preset: Optional[str] = None,
) -> List[str]:
    """エンジンごとのコマンドラインを構築

    実際のオプション体系は環境依存のため、ここでは簡易なテンプレートのみ提供する。
    必要に応じてプロジェクトローカルで調整することを前提とする。
    """

    text = text or ""

    if engine == "softalk":
        # SofTalk 想定の簡易テンプレート
        cmd: List[str] = [str(exe_path)]
        if voice_preset:
            cmd.append(f"/T:{voice_preset}")
        cmd.append(f"/R:{str(output_path)}")
        cmd.append(f"/W:{text}")
        return cmd

    if engine == "aquestalk":
        # AquesTalk 想定の簡易テンプレート
        cmd = [str(exe_path)]
        cmd.extend(["/t", text, "/o", str(output_path)])
        if voice_preset:
            cmd.extend(["/v", voice_preset])
        return cmd

    raise ValueError(f"Unsupported engine: {engine}")


def run_batch(
    *,
    csv_path: Path,
    out_dir: Path,
    engine: str,
    voice_preset: Optional[str] = None,
    text_encoding: str = "utf-8",
    dry_run: bool = False,
    speaker_map_path: Optional[Path] = None,
) -> int:
    """タイムライン CSV から行ごと TTS を実行するメイン処理

    Returns:
        int: 0=success, 非0=エラー
    """

    rows = _load_timeline_rows(csv_path, text_encoding=text_encoding)
    if not rows:
        logger.warning(f"CSV にデータ行がありませんでした: {csv_path}")
        return 0

    speaker_voice_map: Dict[str, Any] = {}
    if speaker_map_path is not None:
        try:
            speaker_voice_map = _load_speaker_voice_map(speaker_map_path)
        except Exception as e:
            logger.error(f"話者マッピング JSON の読み込みに失敗しました: {e}")
            return 1

    try:
        exe_path = _get_engine_executable(engine)
    except Exception as e:
        logger.error(f"TTS 実行ファイルの取得に失敗しました: {e}")
        return 1

    for index, (speaker, text) in enumerate(rows, start=1):
        output_path = _build_output_path(out_dir, index)

        if not text:
            logger.info(f"行 {index} はテキストが空のためスキップします: speaker={speaker}")
            continue

        row_voice_preset = _select_voice_preset(
            engine=engine,
            speaker=speaker,
            default_preset=voice_preset,
            speaker_voice_map=speaker_voice_map,
        )

        cmd = _build_command(
            engine=engine,
            exe_path=exe_path,
            text=text,
            output_path=output_path,
            voice_preset=row_voice_preset,
        )

        if dry_run:
            logger.info(f"[dry-run] TTS コマンド: {' '.join(cmd)}")
            continue

        logger.info(f"[TTS] 行 {index} を合成: speaker={speaker}, out={output_path}")
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"TTS 実行に失敗しました (row={index}): {e}")
            return 1

    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="SofTalk / AquesTalk ローカル TTS バッチ")
    parser.add_argument("--engine", choices=["softalk", "aquestalk"], required=True, help="使用する TTS エンジン")
    parser.add_argument("--csv", required=True, help="タイムライン CSV ファイルパス (A:話者, B:テキスト)")
    parser.add_argument("--out-dir", required=True, help="生成した WAV を出力するディレクトリ")
    parser.add_argument("--voice-preset", help="エンジン側の声質/話者プリセット名", default=None)
    parser.add_argument(
        "--text-encoding",
        help="CSV のテキストエンコーディング",
        default="utf-8",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="実際には TTS を実行せず、生成されるコマンドだけをログに出力",
    )
    parser.add_argument(
        "--speaker-map",
        help="Speaker 列から声プリセットを解決する JSON マップのパス",
        default=None,
    )

    args = parser.parse_args(argv)

    csv_path = Path(args.csv)
    out_dir = Path(args.out_dir)
    speaker_map_path = Path(args.speaker_map) if args.speaker_map else None

    try:
        return run_batch(
            csv_path=csv_path,
            out_dir=out_dir,
            engine=args.engine,
            voice_preset=args.voice_preset,
            text_encoding=args.text_encoding,
            dry_run=args.dry_run,
            speaker_map_path=speaker_map_path,
        )
    except Exception as e:  # pragma: no cover
        logger.error(f"TTS バッチ実行中に予期せぬエラーが発生しました: {e}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
