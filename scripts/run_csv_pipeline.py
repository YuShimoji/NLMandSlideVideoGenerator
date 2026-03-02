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


async def _run(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv).expanduser().resolve()
    audio_dir = Path(args.audio_dir).expanduser().resolve()

    if not csv_path.exists():
        logger.error(f"CSVファイルが見つかりません: {csv_path}")
        return 1
    if not audio_dir.exists():
        logger.error(f"音声ディレクトリが見つかりません: {audio_dir}")
        return 1
    if not audio_dir.is_dir():
        logger.error(f"音声ディレクトリではありません: {audio_dir}")
        return 1

    create_directories()

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
