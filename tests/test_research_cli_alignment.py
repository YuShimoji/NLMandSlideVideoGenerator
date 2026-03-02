import json
from pathlib import Path

import pytest

from scripts.research_cli import run_alignment


@pytest.mark.asyncio
async def test_run_alignment_saves_alignment_report(tmp_path: Path):
    package_dir = tmp_path / "rp_test"
    package_dir.mkdir()
    package_path = package_dir / "package.json"
    package_path.write_text(
        json.dumps(
            {
                "package_id": "rp_test",
                "topic": "AIの将来",
                "created_at": "2026-02-28T18:00:00+09:00",
                "sources": [
                    {
                        "url": "https://example.com/source1",
                        "title": "AIの将来",
                        "content_preview": "AI導入率は2026年に42%へ上昇した。",
                        "relevance_score": 0.9,
                        "reliability_score": 0.9,
                        "source_type": "article",
                        "adoption_status": "pending",
                        "adoption_reason": "",
                        "key_claims": ["AI導入率は2026年に42%へ上昇した"],
                    }
                ],
                "summary": "",
                "review_status": "pending",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    script_path = tmp_path / "script.txt"
    script_path.write_text("AI導入率は2026年に42%へ上昇した。", encoding="utf-8")

    report_path = await run_alignment(package_path, script_path)

    assert report_path.exists()
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["summary"]["supported"] == 1
