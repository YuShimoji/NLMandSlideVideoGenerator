"""Simple doc lint for removed command references."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"

# Command patterns that should not appear as runnable instructions.
BANNED_PATTERNS = [
    "python scripts/run_csv_pipeline.py",
    "run_csv_pipeline.py --",
]

EXCLUDE_DIRS = {
    DOCS_DIR / "archive",
    DOCS_DIR / "reports",
    DOCS_DIR / "inbox",
}


def is_excluded(path: Path) -> bool:
    return any(parent in EXCLUDE_DIRS for parent in [path, *path.parents])


def iter_doc_files() -> list[Path]:
    files: list[Path] = []
    for path in DOCS_DIR.rglob("*.md"):
        if is_excluded(path):
            continue
        files.append(path)
    return files


def main() -> int:
    violations: list[tuple[Path, int, str]] = []

    for file_path in iter_doc_files():
        text = file_path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern in BANNED_PATTERNS:
                if pattern not in line:
                    continue

                # Allow historical/deprecation statements.
                if any(token in line for token in ("削除済み", "廃止", "DEPRECATED")):
                    continue

                violations.append((file_path, line_no, pattern))

    if not violations:
        print("[doc-lint] OK: removed command references were not found.")
        return 0

    print("[doc-lint] NG: removed command references found:")
    for file_path, line_no, pattern in violations:
        rel = file_path.relative_to(ROOT)
        print(f"  - {rel}:{line_no} -> {pattern}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())