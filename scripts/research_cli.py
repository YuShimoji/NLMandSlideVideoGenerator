#!/usr/bin/env python3
"""Research and alignment CLI."""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from config.settings import create_directories, settings
from core.utils.logger import logger
from notebook_lm.research_models import AlignmentReport, ResearchPackage
from notebook_lm.script_alignment import ScriptAlignmentAnalyzer
from notebook_lm.source_collector import SourceCollector


async def run_research(topic: str, urls: list[str] | None = None, max_sources: int | None = None) -> None:
    """Collect sources and persist a ResearchPackage."""
    create_directories()

    collector = SourceCollector()
    collector.max_sources = max_sources or settings.RESEARCH_SETTINGS["max_sources"]

    logger.info(f"Research start: topic='{topic}'")
    sources = await collector.collect_sources(topic, urls)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_id = f"rp_{timestamp}"
    package_dir = settings.RESEARCH_SETTINGS["data_dir"] / package_id
    package_dir.mkdir(parents=True, exist_ok=True)

    package = ResearchPackage(
        package_id=package_id,
        topic=topic,
        created_at=datetime.now().isoformat(),
        sources=sources,
    )

    package_path = package_dir / "package.json"
    with open(package_path, "w", encoding="utf-8") as handle:
        json.dump(package.to_dict(), handle, ensure_ascii=False, indent=2)

    logger.info(f"Research package saved: {package_path}")

    print(f"\nResearch complete: collected {len(sources)} sources")
    print(f"Saved to: {package_dir}")
    for index, source in enumerate(sources, 1):
        print(f"  [{index}] {source.title} ({source.source_type})")
        print(f"      URL: {source.url}")


async def run_alignment(package_path: Path, script_path: Path, output_dir: Path | None = None) -> Path:
    """Load a ResearchPackage and script, then persist an AlignmentReport."""
    create_directories()

    with open(package_path, "r", encoding="utf-8") as handle:
        package_data = json.load(handle)
    package = ResearchPackage.from_dict(package_data)

    analyzer = ScriptAlignmentAnalyzer()
    normalized_script = await analyzer.load_script(script_path)
    report = await analyzer.analyze(package, normalized_script)

    report_dir = output_dir or package_path.parent
    report_path = analyzer.save_report(report, report_dir)

    print("\n=== Alignment Summary ===")
    print(f"Package: {package.package_id}")
    print(f"Script:  {script_path}")
    print(f"Report:  {report_path}")
    print(
        "Counts: "
        f"supported={report.summary.get('supported', 0)}, "
        f"orphaned={report.summary.get('orphaned', 0)}, "
        f"missing={report.summary.get('missing', 0)}, "
        f"conflict={report.summary.get('conflict', 0)}"
    )
    return report_path


async def run_review(
    report_path: Path,
    output_csv: Path | None = None,
    auto_mode: bool = False,
) -> Path:
    """Load an AlignmentReport, interactively review items, and export final CSV."""

    with open(report_path, "r", encoding="utf-8") as handle:
        report = AlignmentReport.from_dict(json.load(handle))

    items_needing_review = [
        item for item in report.analysis
        if item.get("status") in ("orphaned", "conflict", "missing")
    ]
    total = len(report.analysis)
    review_count = len(items_needing_review)

    print(f"\n=== AlignmentReport Review: {report.report_id} ===")
    print(f"Total items: {total}, Needs review: {review_count}\n")

    # Auto-accept supported items
    for item in report.analysis:
        if item.get("status") == "supported":
            item["status"] = "adopted"

    if auto_mode:
        for item in items_needing_review:
            item["status"] = "rejected"
        print(f"Auto mode: {review_count} items rejected, supported items adopted.\n")
    else:
        for idx, item in enumerate(items_needing_review, 1):
            status = item.get("status", "")
            seg_idx = item.get("segment_index")
            text = item.get("text") or ""
            source = item.get("matched_source") or "(none)"
            claim = item.get("matched_claim") or ""
            suggestion = item.get("suggestion") or ""

            seg_label = f"Seg#{seg_idx}" if seg_idx is not None else "N/A"
            print(f"[{idx}/{review_count}] {status.upper():10s} {seg_label}: {text[:80]}")
            if claim:
                print(f"  -> Source claim: {claim[:80]}")
                print(f"  -> URL: {source}")
            if suggestion:
                print(f"  -> Hint: {suggestion}")

            if status == "missing":
                action = _prompt_missing()
            elif status == "conflict":
                action = _prompt_conflict()
            else:
                action = _prompt_orphaned()

            if action in ("accept", "add"):
                item["status"] = "adopted"
            elif action in ("reject", "skip"):
                item["status"] = "rejected"
            elif action == "use_source":
                item["status"] = "adopted"
                if claim:
                    item["text"] = claim
            elif action == "edit":
                new_text = input("  New text: ").strip()
                if new_text:
                    item["text"] = new_text
                item["status"] = "adopted"
            print()

    report.rebuild_summary()

    # Save updated report
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, ensure_ascii=False, indent=2)
    print(f"Report updated: {report_path}")

    # Export CSV
    csv_path = output_csv or report_path.parent / "final.csv"
    analyzer = ScriptAlignmentAnalyzer()
    analyzer.export_to_csv(report.analysis, csv_path)

    adopted_count = sum(1 for item in report.analysis if item.get("status") == "adopted")
    print(f"Exported: {csv_path} ({adopted_count} segments)")
    return csv_path


async def run_pipeline(
    topic: str,
    urls: list[str] | None = None,
    max_sources: int | None = None,
    auto_review: bool = False,
    slides_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    speaker_mapping: Optional[dict[str, str]] = None,
) -> Path:
    """collect → script gen → align → review → CSV の一気通貫実行。

    Returns:
        最終出力CSVのパス。
    """
    create_directories()

    # --- Step 1: collect ---
    print("\n=== Step 1: Source Collection ===")
    collector = SourceCollector()
    collector.max_sources = max_sources or settings.RESEARCH_SETTINGS["max_sources"]
    sources = await collector.collect_sources(topic, urls)
    print(f"Collected {len(sources)} sources")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_id = f"rp_{timestamp}"
    work_dir = output_dir or (settings.RESEARCH_SETTINGS["data_dir"] / package_id)
    work_dir.mkdir(parents=True, exist_ok=True)

    package = ResearchPackage(
        package_id=package_id,
        topic=topic,
        created_at=datetime.now().isoformat(),
        sources=sources,
    )
    package_path = work_dir / "package.json"
    with open(package_path, "w", encoding="utf-8") as handle:
        json.dump(package.to_dict(), handle, ensure_ascii=False, indent=2)

    # --- Step 2: script generation ---
    print("\n=== Step 2: Script Generation (Gemini) ===")
    from core.providers.script.gemini_provider import GeminiScriptProvider

    provider = GeminiScriptProvider()
    script_bundle = await provider.generate_script(topic, sources)
    segments = script_bundle.get("segments", [])
    print(f"Generated script: {len(segments)} segments")

    # Save script for alignment
    script_path = work_dir / "generated_script.json"
    with open(script_path, "w", encoding="utf-8") as handle:
        json.dump(script_bundle, handle, ensure_ascii=False, indent=2)

    # --- Step 3: align ---
    print("\n=== Step 3: Alignment Analysis ===")
    analyzer = ScriptAlignmentAnalyzer()
    normalized = await analyzer.load_script(script_path)
    report = await analyzer.analyze(package, normalized)
    report_path = analyzer.save_report(report, work_dir)
    print(
        f"Alignment: "
        f"supported={report.summary.get('supported', 0)}, "
        f"orphaned={report.summary.get('orphaned', 0)}, "
        f"conflict={report.summary.get('conflict', 0)}"
    )

    # --- Step 4: review ---
    print("\n=== Step 4: Review ===")
    reviewed_csv = await run_review(report_path, auto_mode=auto_review)

    # --- Step 5: CsvAssembler (if slides available) ---
    slide_paths: list[Path] = []
    if slides_dir and slides_dir.exists():
        slide_paths = sorted(slides_dir.glob("*.png"))

    if slide_paths:
        print(f"\n=== Step 5: CsvAssembler ({len(slide_paths)} slides) ===")
        from core.csv_assembler import CsvAssembler

        assembler = CsvAssembler()
        # reviewed CSV の内容を読み直してセグメント化
        import csv as csv_mod

        assembled_segments: list[dict[str, str]] = []
        with open(reviewed_csv, "r", encoding="utf-8") as f:
            for row in csv_mod.reader(f):
                if len(row) >= 2:
                    assembled_segments.append({"speaker": row[0], "text": row[1]})

        if assembled_segments:
            timeline_csv = work_dir / "timeline.csv"
            assembler.assemble(
                script_segments=assembled_segments,
                slide_image_paths=slide_paths,
                output_path=timeline_csv,
                speaker_mapping=speaker_mapping,
            )
            print(f"Timeline CSV: {timeline_csv}")
            reviewed_csv = timeline_csv

    print(f"\n=== Pipeline Complete ===")
    print(f"Output: {reviewed_csv}")
    print(f"Work dir: {work_dir}")
    return reviewed_csv


def _prompt_orphaned() -> str:
    choice = input("  [a]ccept / [r]eject / [e]dit / [s]kip ? ").strip().lower()
    return {"a": "accept", "r": "reject", "e": "edit", "s": "skip"}.get(choice, "skip")


def _prompt_conflict() -> str:
    choice = input("  [u]se source / [k]eep script / [e]dit / [s]kip ? ").strip().lower()
    return {
        "u": "use_source", "k": "accept", "e": "edit", "s": "skip",
    }.get(choice, "skip")


def _prompt_missing() -> str:
    choice = input("  [a]dd to script / [s]kip ? ").strip().lower()
    return {"a": "add", "s": "skip"}.get(choice, "skip")


def main() -> None:
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0] not in {"collect", "align", "review", "pipeline"}:
        raw_args = ["collect", *raw_args]

    parser = argparse.ArgumentParser(description="Research and alignment CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Collect web sources and persist a package")
    collect_parser.add_argument("--topic", required=True, help="Research topic")
    collect_parser.add_argument("--urls", nargs="*", help="Optional seed URLs")
    collect_parser.add_argument("--max", type=int, help="Maximum number of sources")

    align_parser = subparsers.add_parser("align", help="Analyze a package against a draft script")
    align_parser.add_argument("--package", required=True, help="Path to package.json")
    align_parser.add_argument("--script", required=True, help="Path to draft script (.txt/.csv/.json)")
    align_parser.add_argument("--out-dir", help="Optional output directory")

    review_parser = subparsers.add_parser("review", help="Interactively review an AlignmentReport and export CSV")
    review_parser.add_argument("--report", required=True, help="Path to alignment_report.json")
    review_parser.add_argument("--output", help="Output CSV path (default: final.csv in report dir)")
    review_parser.add_argument("--auto", action="store_true", help="Auto mode: adopt supported, reject others")

    pipe_parser = subparsers.add_parser("pipeline", help="End-to-end: collect → script → align → review → CSV")
    pipe_parser.add_argument("--topic", required=True, help="Research topic")
    pipe_parser.add_argument("--urls", nargs="*", help="Optional seed URLs")
    pipe_parser.add_argument("--max", type=int, help="Maximum number of sources")
    pipe_parser.add_argument("--auto-review", action="store_true", help="Auto-review (adopt supported, reject others)")
    pipe_parser.add_argument("--slides-dir", help="Directory containing slide PNG images")
    pipe_parser.add_argument("--output-dir", help="Output directory for all artifacts")
    pipe_parser.add_argument("--speaker-map", help='Speaker mapping JSON (e.g. \'{"Host1":"れいむ"}\')')

    args = parser.parse_args(raw_args)

    if args.command == "collect":
        asyncio.run(run_research(args.topic, args.urls, args.max))
        return

    if args.command == "review":
        asyncio.run(
            run_review(
                Path(args.report),
                Path(args.output) if args.output else None,
                args.auto,
            )
        )
        return

    if args.command == "pipeline":
        speaker_map = None
        if args.speaker_map:
            speaker_map = json.loads(args.speaker_map)
        asyncio.run(
            run_pipeline(
                topic=args.topic,
                urls=args.urls,
                max_sources=args.max,
                auto_review=args.auto_review,
                slides_dir=Path(args.slides_dir) if args.slides_dir else None,
                output_dir=Path(args.output_dir) if args.output_dir else None,
                speaker_mapping=speaker_map,
            )
        )
        return

    asyncio.run(
        run_alignment(
            Path(args.package),
            Path(args.script),
            Path(args.out_dir) if args.out_dir else None,
        )
    )


if __name__ == "__main__":
    main()
