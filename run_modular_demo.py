#!/usr/bin/env python3
"""
モジュラーパイプラインのデモ実行
"""
import sys
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import asyncio
from pathlib import Path
import argparse

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from core.pipeline import ModularVideoPipeline  # noqa: E402
from config.settings import create_directories  # noqa: E402


async def main_async(topic: str, urls: list[str] | None, quality: str, upload: bool, private: bool):
    create_directories()
    pipeline = ModularVideoPipeline()
    result = await pipeline.run(
        topic=topic,
        urls=urls,
        quality=quality,
        private_upload=private,
        upload=upload,
    )

    print("\n=== モジュラーパイプライン結果 ===")
    print(f"成功: {result['success']}")
    if result.get("youtube_url"):
        print(f"YouTube URL: {result['youtube_url']}")

    artifacts = result["artifacts"]
    print("\n[生成アーティファクト]")
    print(f"  音声: {artifacts.audio.file_path}")
    print(f"  スライド: {artifacts.slides.file_path} ({artifacts.slides.total_slides}枚)")
    print(f"  動画: {artifacts.video.file_path}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="モジュラーパイプライン デモ")
    parser.add_argument("--topic", required=False, default="AI技術の最新動向", help="トピック")
    parser.add_argument("--urls", nargs="*", help="ソースURL")
    parser.add_argument("--quality", choices=["720p", "1080p", "4k"], default="1080p")
    parser.add_argument("--upload", action="store_true", help="YouTubeへアップロードする")
    parser.add_argument("--public", action="store_true", help="公開アップロード (デフォルトは非公開)")

    args = parser.parse_args()

    return asyncio.run(
        main_async(
            topic=args.topic,
            urls=list(args.urls) if args.urls else None,
            quality=args.quality,
            upload=bool(args.upload),
            private=not bool(args.public),
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
