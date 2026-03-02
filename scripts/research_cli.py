#!/usr/bin/env python3
"""Research and alignment CLI."""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from config.settings import create_directories, settings
from core.utils.logger import logger
from notebook_lm.research_models import ResearchPackage
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


def main() -> None:
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0] not in {"collect", "align"}:
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

    args = parser.parse_args(raw_args)

    if args.command == "collect":
        asyncio.run(run_research(args.topic, args.urls, args.max))
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
