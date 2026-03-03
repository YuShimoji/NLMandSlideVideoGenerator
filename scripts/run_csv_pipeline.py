#!/usr/bin/env python3
"""CSVタイムライン(P10)モードで本番パイプラインを実行するCLI

- A列=話者, B列=テキスト の CSV
- 行ごとの WAV が格納されたディレクトリ

を入力として、ModularVideoPipeline.run_csv_timeline() を呼び出し、
スライド生成・動画合成・(オプションで)アップロードまでを実行する薄いラッパーです。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

# プロジェクトルートと src をパスに追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from config.settings import settings, create_directories  # noqa: E402
from core.helpers import build_default_pipeline  # noqa: E402
from core.utils.logger import logger  # noqa: E402
from notebook_lm.script_alignment import ScriptAlignmentAnalyzer  # noqa: E402
from notebook_lm.research_models import ResearchPackage  # noqa: E402
import json  # noqa: E402



import csv  # noqa: E402


async def _generate_tts_audio(
    csv_path: Path,
    audio_dir: Path,
    tts_engine: str,
    speaker_id: Optional[int] = None,
) -> int:
    """CSVテキストからTTSで音声ファイルを生成する。

    既存のWAVファイルがある行はスキップする。
    """
    # CSV読み込み: A列=話者, B列=テキスト
    rows: list[tuple[str, str]] = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and row[1].strip():
                    rows.append((row[0].strip(), row[1].strip()))
    except Exception as e:
        logger.error(f"CSV読み込み失敗: {e}")
        return 1

    if not rows:
        logger.error("CSVにテキスト行がありません")
        return 1

    # 既存WAVファイルをチェック
    existing_wavs = {p.name for p in audio_dir.glob("*.wav")}
    lines_to_generate: list[tuple[int, str, str]] = []
    for i, (speaker, text) in enumerate(rows):
        wav_name = f"{i + 1:03d}.wav"
        if wav_name not in existing_wavs:
            lines_to_generate.append((i, speaker, text))

    if not lines_to_generate:
        logger.info("全ての音声ファイルが既に存在します。TTS生成をスキップします。")
        return 0

    logger.info(
        f"TTS音声生成を開始します: engine={tts_engine}, "
        f"生成対象={len(lines_to_generate)}/{len(rows)}行"
    )

    if tts_engine == "voicevox":
        return await _tts_voicevox(audio_dir, lines_to_generate, speaker_id)
    else:
        logger.error(f"未対応のTTSエンジン: {tts_engine} (対応: voicevox)")
        return 1


async def _tts_voicevox(
    audio_dir: Path,
    lines: list[tuple[int, str, str]],
    speaker_id: Optional[int] = None,
) -> int:
    """VOICEVOXエンジンでWAVファイルを生成（非同期並行・部分失敗許容）"""
    try:
        from audio.voicevox_client import VoicevoxClient, VoicevoxAudioParams
    except ImportError:
        logger.error("voicevox_client のインポートに失敗しました")
        return 1

    voicevox_settings = settings.TTS_SETTINGS.get("voicevox", {})
    engine_url = voicevox_settings.get("engine_url", "http://localhost:50021")
    sid = speaker_id or int(voicevox_settings.get("speaker_id", 3))
    params = VoicevoxAudioParams(
        speed_scale=float(voicevox_settings.get("speed", 1.0)),
        pitch_scale=float(voicevox_settings.get("pitch", 0.0)),
        intonation_scale=float(voicevox_settings.get("intonation", 1.0)),
    )

    client = VoicevoxClient(engine_url=engine_url, timeout=30)

    if not client.is_available():
        logger.error(
            f"VOICEVOX Engine ({engine_url}) に接続できません。\n"
            "VOICEVOX Engine を起動してから再実行してください。\n"
            "ダウンロード: https://voicevox.hiroshiba.jp/"
        )
        return 1

    logger.info(f"VOICEVOX Engine 接続確認: {engine_url} (speaker_id={sid})")

    # 非同期並行処理（Engine過負荷防止: 最大3並行）
    semaphore = asyncio.Semaphore(3)
    generated = 0
    failures: list[tuple[str, str]] = []

    async def _synthesize_one(idx: int, text: str) -> bool:
        nonlocal generated
        wav_name = f"{idx + 1:03d}.wav"
        output_path = audio_dir / wav_name
        async with semaphore:
            try:
                await client.synthesize_to_file_async(
                    text=text,
                    output_path=output_path,
                    speaker_id=sid,
                    params=params,
                )
                file_size = output_path.stat().st_size
                generated += 1
                label = text if len(text) <= 30 else text[:30] + "..."
                logger.info(
                    f"  [{generated}/{len(lines)}] {wav_name} "
                    f"({file_size:,} bytes) - {label}"
                )
                return True
            except Exception as e:
                failures.append((wav_name, str(e)))
                logger.warning(f"VOICEVOX合成失敗 ({wav_name}): {e}")
                return False

    tasks = [_synthesize_one(idx, text) for idx, _speaker, text in lines]
    await asyncio.gather(*tasks)

    if failures:
        logger.error(
            f"TTS音声生成: {generated}/{len(lines)} 成功, "
            f"{len(failures)} 失敗"
        )
        for wav_name, err in failures:
            logger.error(f"  失敗: {wav_name} - {err}")
        return 1

    logger.info(f"TTS音声生成完了: {generated}ファイル生成")
    return 0

async def _run(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv).expanduser().resolve()
    audio_dir = Path(args.audio_dir).expanduser().resolve()

    if not csv_path.exists():
        logger.error(f"CSVファイルが見つかりません: {csv_path}")
        return 1

    # audio_dir が存在しない場合は作成（TTS生成先として使用）
    if not audio_dir.exists():
        if args.tts:
            audio_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"音声ディレクトリを作成しました: {audio_dir}")
        else:
            logger.error(f"音声ディレクトリが見つかりません: {audio_dir}")
            return 1
    if not audio_dir.is_dir():
        logger.error(f"音声ディレクトリではありません: {audio_dir}")
        return 1

    create_directories()

    # TTS による音声自動生成
    if args.tts:
        tts_result = await _generate_tts_audio(
            csv_path=csv_path,
            audio_dir=audio_dir,
            tts_engine=args.tts,
            speaker_id=args.tts_speaker_id,
        )
        if tts_result != 0:
            return tts_result

    # audio_dir 内の WAV ファイル存在確認
    wav_files = sorted(audio_dir.glob("*.wav"))
    if not wav_files:
        logger.error(
            f"音声ディレクトリにWAVファイルがありません: {audio_dir}\n"
            "ヒント: --tts voicevox オプションでテキストから音声を自動生成できます"
        )
        return 1

    # スライド1枚あたりの最大文字数をオプションで上書き
    if args.max_chars_per_slide is not None:
        try:
            value = int(args.max_chars_per_slide)
            if value > 0:
                settings.SLIDES_SETTINGS["max_chars_per_slide"] = value
                logger.info(f"SLIDES_SETTINGS.max_chars_per_slide を {value} に上書きしました")
        except (TypeError, ValueError) as e:  # pragma: no cover
            logger.warning(f"max_chars_per_slide オプションの解釈に失敗しました: {e}")
        except Exception as e:  # pragma: no cover
            logger.warning(f"max_chars_per_slide オプションの解釈に失敗しました: {e}")

    topic: Optional[str] = args.topic or csv_path.stem
    quality: str = args.video_quality
    private_upload: bool = not args.public_upload
    upload: bool = args.upload
    export_ymm4: bool = args.export_ymm4

    logger.info(
        f"CSVタイムラインパイプラインを実行します: topic={topic}, csv={csv_path}, "
        f"audio_dir={audio_dir}, quality={quality}, upload={upload}, "
        f"private_upload={private_upload}, export_ymm4={export_ymm4}"
    )

    original_backend = settings.PIPELINE_COMPONENTS.get("editing_backend", "moviepy")
    if export_ymm4:
        settings.PIPELINE_COMPONENTS["editing_backend"] = "ymm4"
        logger.info("YMM4エクスポートを有効化: editing_backend=ymm4")

    # アライメント事前検証
    if args.package:
        package_path = Path(args.package).expanduser().resolve()
        if not package_path.exists():
            logger.error(f"Packageファイルが見つかりません: {package_path}")
            return 1
        
        logger.info(f"アライメント事前検証を開始します: {package_path}")
        try:
            with open(package_path, "r", encoding="utf-8") as handle:
                package_data = json.load(handle)
            package = ResearchPackage.from_dict(package_data)

            analyzer = ScriptAlignmentAnalyzer()
            normalized_script = await analyzer.load_script(csv_path)
            report = await analyzer.analyze(package, normalized_script)
            
            supported = report.summary.get('supported', 0)
            orphaned = report.summary.get('orphaned', 0)
            missing = report.summary.get('missing', 0)
            conflict = report.summary.get('conflict', 0)
            
            logger.info("=== アライメント事前検証 結果 ===")
            logger.info(f"Supported: {supported}, Orphaned: {orphaned}, Missing: {missing}, Conflict: {conflict}")
            
            if missing > 0:
                logger.warning(f"アライメント警告: 根拠のない文(missing)が {missing} 件存在します。")
                if args.strict_alignment:
                    logger.error("--strict-alignment が指定されているため、パイプラインの実行を中断します。")
                    return 1
            else:
                logger.info("アライメントに重大な問題は検出されませんでした。")

        except Exception as e:
            logger.error(f"アライメント事前検証中にエラーが発生しました: {e}")
            return 1

    try:
        pipeline = build_default_pipeline()

        result = await pipeline.run_csv_timeline(
            csv_path=csv_path,
            audio_dir=audio_dir,
            topic=topic,
            quality=quality,
            private_upload=private_upload,
            upload=upload,
            stage_modes=settings.PIPELINE_STAGE_MODES,
            user_preferences={},
            progress_callback=None,
        )
    finally:
        settings.PIPELINE_COMPONENTS["editing_backend"] = original_backend

    artifacts = result.get("artifacts")
    video_path = getattr(artifacts.video, "file_path", None) if artifacts else None

    if video_path:
        print(f"Generated video: {video_path}")
    else:
        print("Pipeline finished, but video path was not available in artifacts.")

    editing_outputs = getattr(artifacts, "editing_outputs", None) if artifacts else None
    if editing_outputs and "ymm4" in editing_outputs:
        ymm4_info = editing_outputs["ymm4"]
        print("\nYMM4 export artifacts:")
        for key, value in ymm4_info.items():
            print(f"  - {key}: {value}")

    if result.get("youtube_url"):
        print(f"YouTube URL: {result['youtube_url']}")

    return 0 if result.get("success") else 1


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CSVタイムラインモードで動画生成パイプラインを実行")
    parser.add_argument("--csv", required=True, help="タイムラインCSVファイルパス (A:話者, B:テキスト)")
    parser.add_argument("--audio-dir", required=True, help="行ごとの音声ファイル(WAV)ディレクトリ")
    parser.add_argument("--topic", help="任意のトピック名 (省略時はCSVファイル名)")
    parser.add_argument(
        "--video-quality",
        choices=["1080p", "720p", "480p"],
        default="1080p",
        help="動画品質",
    )
    parser.add_argument(
        "--max-chars-per-slide",
        type=int,
        default=None,
        help="1スライドあたりの最大文字数 (省略時は設定ファイルの値を使用)",
    )
    parser.add_argument(
        "--tts",
        choices=["voicevox"],
        default=None,
        help="TTSエンジンでCSVテキストからWAV音声を自動生成 (対応: voicevox)",
    )
    parser.add_argument(
        "--tts-speaker-id",
        type=int,
        default=None,
        help="TTSスピーカーID (VOICEVOX: 3=ずんだもん, 2=四国めたん, 8=春日部つむぎ)",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        default=False,
        help="YouTube 等へのアップロードを有効化",
    )
    parser.add_argument(
        "--public-upload",
        action="store_true",
        default=False,
        help="アップロード時に公開ステータスを使用 (指定しない場合は非公開)",
    )
    parser.add_argument(
        "--export-ymm4",
        action="store_true",
        default=False,
        help="YMM4 編集プロジェクトを書き出し (editing_backend=YMM4 を強制)",
    )
    parser.add_argument(
        "--package",
        help="事前にResearch CLIで収集した package.json へのパス (指定時、アライメント検証を実施)",
    )
    parser.add_argument(
        "--strict-alignment",
        action="store_true",
        default=False,
        help="アライメントで missing が1件以上あった場合、動画生成せずに異常終了する",
    )

    args = parser.parse_args(argv)

    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        logger.warning("CSVタイムラインパイプラインがユーザーにより中断されました")
        return 130
    except (OSError, ValueError, TypeError, RuntimeError) as e:  # pragma: no cover
        logger.error(f"CSVタイムラインCLI実行中にエラーが発生しました: {e}")
        return 1
    except Exception as e:  # pragma: no cover
        import traceback
        traceback.print_exc()
        logger.error(f"CSVタイムラインCLI実行中にエラーが発生しました: {e}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
