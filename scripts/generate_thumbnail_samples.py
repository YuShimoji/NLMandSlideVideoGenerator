#!/usr/bin/env python3
"""
サムネイルサンプル生成スクリプト
全4スタイル + generate_from_script の出力を data/thumbnails/samples/ に保存する。
人間による視覚確認用。
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock

# プロジェクトルートとsrcをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from core.thumbnails import AIThumbnailGenerator, TemplateThumbnailGenerator
from video_editor.models import VideoInfo
from slides.slide_generator import SlidesPackage


SAMPLE_DIR = project_root / "data" / "thumbnails" / "samples"

MOCK_VIDEO = VideoInfo(
    file_path=Path("sample_video.mp4"),
    duration=1200.0,
    resolution=(1920, 1080),
    fps=30,
    file_size=500_000_000,
    has_subtitles=True,
    has_effects=True,
    created_at=datetime.now(),
)

MOCK_SCRIPT = {
    "title": "AI技術の最新動向 2026年版",
    "content": "人工知能の進化について詳しく解説します。機械学習、深層学習の最前線。",
    "segments": [
        {"text": "AIの基礎から最前線まで", "content": "AIの基礎から最前線まで", "duration": 30, "segment_id": "seg_1"},
        {"text": "将来展望と社会への影響", "content": "将来展望と社会への影響", "duration": 45, "segment_id": "seg_2"},
    ],
}

MOCK_SLIDES = SlidesPackage(
    presentation_id="sample_presentation",
    slides=[
        Mock(title="タイトルスライド", content="AI技術の最新動向"),
        Mock(title="内容スライド", content="技術の進化について"),
    ],
    total_slides=2,
)


async def main():
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {SAMPLE_DIR}")
    print()

    # --- AIThumbnailGenerator ---
    ai_gen = AIThumbnailGenerator()
    styles = ["modern", "classic", "gaming", "educational"]

    print("=== AIThumbnailGenerator (generate) ===")
    for style in styles:
        result = await ai_gen.generate(
            video=MOCK_VIDEO, script=MOCK_SCRIPT, slides=MOCK_SLIDES, style=style
        )
        # 出力をサンプルディレクトリにコピー
        dest = SAMPLE_DIR / f"ai_{style}.png"
        import shutil
        shutil.copy2(result.file_path, dest)
        size_kb = dest.stat().st_size / 1024
        print(f"  [{style:12s}] {dest.name}  ({size_kb:.1f} KB)")

    print()
    print("=== AIThumbnailGenerator (generate_from_script) ===")
    for style in styles:
        path = await ai_gen.generate_from_script(
            script=MOCK_SCRIPT, output_dir=SAMPLE_DIR, style=style
        )
        dest = SAMPLE_DIR / f"ai_from_script_{style}.png"
        if path != dest:
            import shutil
            shutil.copy2(path, dest)
            path.unlink(missing_ok=True)
        size_kb = dest.stat().st_size / 1024
        print(f"  [{style:12s}] {dest.name}  ({size_kb:.1f} KB)")

    print()
    print("=== TemplateThumbnailGenerator ===")
    tmpl_gen = TemplateThumbnailGenerator()
    for style in styles:
        result = await tmpl_gen.generate(
            video=MOCK_VIDEO, script=MOCK_SCRIPT, slides=MOCK_SLIDES, style=style
        )
        dest = SAMPLE_DIR / f"template_{style}.png"
        import shutil
        shutil.copy2(result.file_path, dest)
        size_kb = dest.stat().st_size / 1024
        print(f"  [{style:12s}] {dest.name}  ({size_kb:.1f} KB)")

    print()
    print(f"Done. {len(list(SAMPLE_DIR.glob('*.png')))} samples in {SAMPLE_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
