#!/usr/bin/env python
"""
E2E Dry-Run: ソース収集 → 台本生成 → 画像収集 → CSV組立

全Python側パイプラインを一気通貫で実行し、成果物を output/e2e_dry_run_{timestamp}/ に集約する。
YMM4以降の工程は手動。

Usage:
    # 実API (GEMINI_API_KEY, BRAVE_SEARCH_API_KEY が .env に設定済み)
    .\\venv\\Scripts\\python.exe scripts\\e2e_dry_run.py --topic "AIと著作権の最新動向"

    # APIキーなし (モックモード: ソース/台本をシミュレーション)
    .\\venv\\Scripts\\python.exe scripts\\e2e_dry_run.py --topic "量子コンピュータ入門" --mock

    # 短尺テスト (5セグメント)
    .\\venv\\Scripts\\python.exe scripts\\e2e_dry_run.py --topic "テスト" --mock --segments 5

環境変数 (実APIモード):
    GEMINI_API_KEY          - Gemini API キー (台本生成)
    BRAVE_SEARCH_API_KEY    - Brave Search API キー (ソース収集)
    PEXELS_API_KEY          - Pexels API キー (画像検索、任意)
    PIXABAY_API_KEY         - Pixabay API キー (画像検索、任意)

成果物フォルダ構成:
    output/e2e_dry_run_{timestamp}/
    ├── manifest.json         # 実行メタデータ + 各成果物パス
    ├── sources.json          # 収集ソース一覧
    ├── script_bundle.json    # 台本 (セグメント群)
    ├── validation.json       # SP-044 セグメント検証結果
    ├── images/               # ダウンロード済み画像
    │   ├── seg_000_wikimedia_12345.jpg
    │   └── ...
    ├── image_credits.txt     # 画像クレジット (YouTube概要欄用)
    └── timeline.csv          # YMM4インポート用CSV
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / "src"
for p in (str(PROJECT_ROOT), str(SRC_PATH)):
    if p not in sys.path:
        sys.path.insert(0, p)

from dotenv import load_dotenv
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

from config.settings import settings
from core.utils.logger import logger


# ---------------------------------------------------------------------------
# Stage definitions
# ---------------------------------------------------------------------------

async def stage_collect_sources(
    topic: str, urls: Optional[List[str]], mock: bool
) -> List[Dict[str, Any]]:
    """Stage 1: ソース収集"""
    if mock:
        logger.info("MOCK: ソースシミュレーション")
        return _mock_sources(topic)

    # SourceCollector (Brave Search) は廃止。手動URLのみ受付
    return [
        {
            "url": url,
            "title": url.split("/")[-1] or url,
            "content_preview": "",
            "relevance_score": 0.5,
            "reliability_score": 0.5,
        }
        for url in (urls or [])
    ]


async def stage_generate_script(
    topic: str, sources: List[Dict[str, Any]], mock: bool, target_segments: int
) -> Dict[str, Any]:
    """Stage 2: 台本生成"""
    if mock:
        logger.info(f"MOCK: 台本シミュレーション ({target_segments} segments)")
        return _mock_script_bundle(topic, target_segments)

    from core.llm_provider import create_llm_provider
    from notebook_lm.gemini_integration import GeminiIntegration

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.warning("GEMINI_API_KEY 未設定 → モック台本にフォールバック")
        return _mock_script_bundle(topic, target_segments)

    llm_provider = create_llm_provider(api_key=api_key)
    gemini = GeminiIntegration(api_key=api_key, llm_provider=llm_provider)
    target_duration = target_segments * 20.0  # ~20秒/seg

    script_info = await gemini.generate_script_from_sources(
        sources=sources,
        topic=topic,
        target_duration=target_duration,
        language=settings.YOUTUBE_SETTINGS.get("default_language", "ja"),
    )

    bundle = _parse_gemini_script(script_info.content, script_info.title)
    return bundle


def _parse_gemini_script(content: str, title: str) -> Dict[str, Any]:
    """Gemini出力をパースしてsegmentsを持つbundleを返す。

    Geminiは```json ... ``` でラップすることがあるため、
    外側のJSONとcontent内の埋め込みJSONの両方を試行する。
    """
    import re

    # まず直接パース
    try:
        bundle = json.loads(content)
        if isinstance(bundle, dict) and bundle.get("segments"):
            return bundle
        # segments が空 → content フィールドにJSON文字列が埋まっている可能性
        inner = bundle.get("content", "")
        if isinstance(inner, str) and inner.strip():
            extracted = _extract_json_from_markdown(inner)
            if extracted and extracted.get("segments"):
                return extracted
    except json.JSONDecodeError:
        pass

    # markdownコードブロック抽出
    extracted = _extract_json_from_markdown(content)
    if extracted and extracted.get("segments"):
        return extracted

    return {"title": title, "content": content, "segments": []}


def _extract_json_from_markdown(text: str) -> Optional[Dict[str, Any]]:
    """```json ... ``` ブロックからJSONを抽出する。"""
    import re
    pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


def stage_validate_segments(
    bundle: Dict[str, Any], target_duration: float
) -> Dict[str, Any]:
    """Stage 2.5: SP-044 セグメント検証"""
    from core.segment_duration_validator import validate_segments

    segments = bundle.get("segments", [])
    if not segments:
        return {"status": "skip", "message": "segments empty", "is_ok": True}

    result = validate_segments(segments, target_duration)
    return {
        "status": result.status,
        "message": result.message,
        "is_ok": result.is_ok,
        "segment_count": len(segments),
    }


def stage_orchestrate_visuals(
    segments: List[Dict[str, Any]], output_dir: Path, topic: str
) -> tuple[List[Dict[str, Any]], str, Any]:
    """Stage 3: Orchestrator統合 (セグメント分類 + 画像収集 + アニメーション割当)

    VisualResourceOrchestratorを使い、セグメントをvisual/textualに分類し、
    visualセグメントにはストック画像、textualにはテキストスライドを割当。
    アニメーションも自動割当される (ken_burns/zoom_in/zoom_out/static等)。

    Returns:
        (image_records, credits, package): 画像メタデータ、クレジット、VisualResourcePackage
    """
    from core.visual.stock_image_client import StockImageClient
    from core.visual.resource_orchestrator import VisualResourceOrchestrator
    from core.visual.segment_classifier import SegmentClassifier

    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    client = StockImageClient(cache_dir=images_dir)
    classifier = SegmentClassifier()

    orchestrator = VisualResourceOrchestrator(
        classifier=classifier,
        stock_client=client,
        topic=topic,
        work_dir=output_dir,
    )

    package = orchestrator.orchestrate(segments)

    # 画像メタデータ収集
    image_records = []
    for i, resource in enumerate(package.resources):
        record = {
            "segment_index": i,
            "source": resource.source,
            "animation": resource.animation_type.value,
            "local_path": str(resource.image_path) if resource.image_path else None,
        }
        image_records.append(record)

    # クレジット生成
    credits = client.get_attribution(orchestrator.last_stock_images) if orchestrator.last_stock_images else ""

    return image_records, credits, package


def stage_collect_images(
    segments: List[Dict[str, Any]], output_dir: Path
) -> tuple[List[Dict[str, Any]], str]:
    """Stage 3 (fallback): StockImageClient直接使用 (Orchestrator未使用時)"""
    from core.visual.stock_image_client import StockImageClient

    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    client = StockImageClient(cache_dir=images_dir)
    images = client.search_for_segments(segments, images_per_segment=1)

    credits = client.get_attribution(images)

    image_records = []
    for i, img in enumerate(images):
        record = {
            "segment_index": i,
            "id": img.id,
            "source": img.source,
            "url": img.url,
            "photographer": img.photographer,
            "local_path": str(img.local_path) if img.local_path else None,
            "width": img.width,
            "height": img.height,
        }
        image_records.append(record)

    return image_records, credits


def stage_assemble_csv(
    segments: List[Dict[str, Any]],
    output_path: Path,
    package: Optional[Any] = None,
    image_records: Optional[List[Dict[str, Any]]] = None,
) -> Path:
    """Stage 4: CSV組立 (Orchestrator package優先、なければimage_recordsから組立)"""
    from core.csv_assembler import CsvAssembler

    assembler = CsvAssembler()

    if package is not None:
        # Orchestratorからのpackageを使用 (アニメーション割当済み)
        return assembler.assemble_from_package(
            script_segments=segments,
            package=package,
            output_path=output_path,
        )

    # フォールバック: image_records から直接組立
    slide_paths: List[Path] = []
    for rec in (image_records or []):
        if rec.get("local_path"):
            slide_paths.append(Path(rec["local_path"]))

    return assembler.assemble(
        script_segments=segments,
        slide_image_paths=slide_paths,
        output_path=output_path,
    )


# ---------------------------------------------------------------------------
# Mock data generators
# ---------------------------------------------------------------------------

def _mock_sources(topic: str) -> List[Dict[str, Any]]:
    return [
        {
            "url": f"https://example.com/{topic.replace(' ', '_')}_{i}",
            "title": f"{topic} - Source {i+1}",
            "content_preview": f"{topic}に関する詳細情報。Section {i+1}の概要。",
            "relevance_score": 0.9 - i * 0.05,
            "reliability_score": 0.85,
        }
        for i in range(5)
    ]


def _mock_script_bundle(topic: str, segment_count: int) -> Dict[str, Any]:
    speakers = ["Host1", "Host2"]
    sections = [
        "Introduction", "Background", "Core Analysis",
        "Case Study", "Data Review", "Technical Detail",
        "Applications", "Future Outlook", "Summary", "Conclusion",
    ]
    segments = []
    for i in range(segment_count):
        section = sections[i % len(sections)]
        speaker = speakers[i % 2]
        segments.append({
            "speaker": speaker,
            "section": section,
            "content": f"{speaker}: {topic}について、{section}の観点から解説します。"
                       f"セグメント{i+1}の内容。キーポイントは重要な発見です。",
            "key_points": [f"{topic} {section}", f"point_{i+1}"],
            "estimated_duration": 20.0,
        })
    return {
        "title": f"{topic} - 解説動画",
        "topic": topic,
        "segments": segments,
        "metadata": {
            "language": "ja",
            "target_duration": segment_count * 20.0,
            "generated_at": datetime.now().isoformat(),
        },
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_e2e_dry_run(
    topic: str,
    urls: Optional[List[str]] = None,
    mock: bool = False,
    target_segments: int = 15,
    output_base: Optional[Path] = None,
) -> Path:
    """E2E dry-run を実行し、成果物フォルダのパスを返す。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_base is None:
        output_base = PROJECT_ROOT / "output"
    output_dir = output_base / f"e2e_dry_run_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest: Dict[str, Any] = {
        "topic": topic,
        "mode": "mock" if mock else "live",
        "target_segments": target_segments,
        "started_at": datetime.now().isoformat(),
        "output_dir": str(output_dir),
        "stages": {},
    }

    print(f"\n{'=' * 60}")
    print(f"  E2E Dry-Run: {topic}")
    print(f"  Mode: {'MOCK' if mock else 'LIVE (API)'}")
    print(f"  Output: {output_dir}")
    print(f"{'=' * 60}\n")

    # --- Stage 1: Sources ---
    print("[1/4] Collecting sources...")
    t0 = time.time()
    sources = await stage_collect_sources(topic, urls, mock)
    elapsed = time.time() - t0

    sources_path = output_dir / "sources.json"
    sources_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["stages"]["sources"] = {
        "status": "ok", "count": len(sources), "elapsed_s": round(elapsed, 2),
        "file": "sources.json",
    }
    print(f"  -> {len(sources)} sources ({elapsed:.1f}s) -> sources.json")

    # --- Stage 2: Script Generation ---
    print("[2/4] Generating script...")
    t0 = time.time()
    bundle = await stage_generate_script(topic, sources, mock, target_segments)
    elapsed = time.time() - t0

    script_path = output_dir / "script_bundle.json"
    script_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    segments = bundle.get("segments", [])
    manifest["stages"]["script"] = {
        "status": "ok", "segment_count": len(segments), "elapsed_s": round(elapsed, 2),
        "file": "script_bundle.json",
    }
    print(f"  -> {len(segments)} segments ({elapsed:.1f}s) -> script_bundle.json")

    # --- Stage 2.5: Validation ---
    validation = stage_validate_segments(bundle, target_segments * 20.0)
    validation_path = output_dir / "validation.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["stages"]["validation"] = validation
    status_label = "PASS" if validation["is_ok"] else "WARN"
    print(f"  -> Validation: [{status_label}] {validation['message']}")

    # --- Stage 3: Visual Orchestration ---
    print("[3/4] Orchestrating visuals (classify + stock + text slides + animation)...")
    t0 = time.time()
    package = None
    if segments:
        try:
            image_records, credits, package = stage_orchestrate_visuals(
                segments, output_dir, topic
            )
            logger.info("Orchestrator統合モード使用")
        except Exception as e:
            logger.warning(f"Orchestrator失敗、フォールバック: {e}")
            image_records, credits = stage_collect_images(segments, output_dir)
    else:
        image_records, credits = [], ""
    elapsed = time.time() - t0

    images_meta_path = output_dir / "images_metadata.json"
    images_meta_path.write_text(json.dumps(image_records, ensure_ascii=False, indent=2), encoding="utf-8")

    if credits:
        credits_path = output_dir / "image_credits.txt"
        credits_path.write_text(credits, encoding="utf-8")

    stock_count = sum(1 for r in image_records if r.get("source") not in ("none", "slide", None))
    slide_count = sum(1 for r in image_records if r.get("source") == "slide")
    anim_types = set(r.get("animation", "static") for r in image_records)
    manifest["stages"]["images"] = {
        "status": "ok", "total": len(image_records),
        "stock_found": stock_count, "text_slides": slide_count,
        "animation_types": sorted(anim_types),
        "elapsed_s": round(elapsed, 2), "file": "images_metadata.json",
    }
    print(f"  -> stock={stock_count}, slides={slide_count}, animations={anim_types} ({elapsed:.1f}s)")

    # --- Stage 4: CSV Assembly ---
    print("[4/4] Assembling CSV for YMM4...")
    t0 = time.time()
    if segments:
        csv_path = stage_assemble_csv(
            segments, output_dir / "timeline.csv",
            package=package, image_records=image_records,
        )
        manifest["stages"]["csv"] = {
            "status": "ok", "rows": len(segments),
            "elapsed_s": round(time.time() - t0, 2),
            "file": "timeline.csv",
        }
        print(f"  -> {len(segments)} rows -> timeline.csv")
    else:
        manifest["stages"]["csv"] = {"status": "skip", "message": "no segments"}
        print("  -> SKIP (no segments)")

    # --- Manifest ---
    manifest["completed_at"] = datetime.now().isoformat()
    total_elapsed = sum(
        s.get("elapsed_s", 0) for s in manifest["stages"].values() if isinstance(s, dict)
    )
    manifest["total_elapsed_s"] = round(total_elapsed, 2)

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"  COMPLETE: {output_dir}")
    print(f"  Total: {total_elapsed:.1f}s")
    print(f"{'=' * 60}")
    print(f"\n  Next steps (manual):")
    print(f"  1. Review script_bundle.json (台本品質確認)")
    print(f"  2. Review images/ (画像品質確認)")
    print(f"  3. Import timeline.csv into YMM4")
    print(f"  4. YMM4 voice synthesis + rendering -> MP4")
    print(f"  5. MP4 quality check (SP-039)")
    print(f"  6. YouTube upload (SP-038)\n")

    return output_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="E2E Dry-Run: Python-side pipeline (source -> script -> images -> CSV)",
    )
    parser.add_argument("--topic", required=True, help="Video topic")
    parser.add_argument("--urls", nargs="*", help="Seed URLs for source collection")
    parser.add_argument("--mock", action="store_true", help="Use mock data (no API calls)")
    parser.add_argument("--segments", type=int, default=15, help="Target segment count (default: 15)")
    parser.add_argument("--output", type=str, default=None, help="Output base directory")

    args = parser.parse_args()
    output_base = Path(args.output) if args.output else None

    result_dir = asyncio.run(
        run_e2e_dry_run(
            topic=args.topic,
            urls=args.urls,
            mock=args.mock,
            target_segments=args.segments,
            output_base=output_base,
        )
    )
    print(f"Artifacts: {result_dir}")


if __name__ == "__main__":
    main()
