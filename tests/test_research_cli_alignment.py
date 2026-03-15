import json
from pathlib import Path

import pytest

from scripts.research_cli import run_alignment, run_review


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


def _make_report_json(tmp_path: Path) -> Path:
    """テスト用のAlignmentReport JSONを作成する。"""
    report_data = {
        "report_id": "ar_rp_test",
        "package_id": "rp_test",
        "analysis": [
            {
                "segment_index": 1,
                "text": "AI導入率は2026年に42%へ上昇した。",
                "status": "supported",
                "matched_source": "https://example.com/source1",
                "matched_claim": "AI導入率は2026年に42%へ上昇した",
                "suggestion": None,
                "speaker": "Host1",
            },
            {
                "segment_index": 2,
                "text": "Googleも同じ技術を使っています。",
                "status": "orphaned",
                "matched_source": None,
                "matched_claim": None,
                "suggestion": "出典不明です。",
                "speaker": "Host2",
            },
            {
                "segment_index": 3,
                "text": "処理速度は100倍です。",
                "status": "conflict",
                "matched_source": "https://example.com/source2",
                "matched_claim": "処理速度は10倍",
                "suggestion": "数値が不一致です。",
                "speaker": "Host1",
            },
            {
                "segment_index": None,
                "text": None,
                "status": "missing",
                "matched_source": "https://example.com/source1",
                "matched_claim": "エラー訂正率50%改善",
                "suggestion": "台本への追加を検討してください。",
            },
        ],
        "summary": {
            "total_segments": 3,
            "supported": 1,
            "orphaned": 1,
            "conflict": 1,
            "missing": 1,
        },
        "created_at": "2026-03-15T00:00:00",
    }
    report_path = tmp_path / "alignment_report.json"
    report_path.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report_path


@pytest.mark.asyncio
async def test_run_review_auto_mode(tmp_path: Path):
    """autoモードでsupported -> adopted, それ以外 -> rejected になることを確認。"""
    report_path = _make_report_json(tmp_path)

    csv_path = await run_review(report_path, auto_mode=True)

    assert csv_path.exists()

    # レポートが更新されていることを確認
    updated = json.loads(report_path.read_text(encoding="utf-8"))
    statuses = [item["status"] for item in updated["analysis"]]
    assert "adopted" in statuses
    assert "rejected" in statuses
    assert "supported" not in statuses  # supportedはadoptedに変換済み
    assert "orphaned" not in statuses   # orphanedはrejectedに変換済み

    # adopted のみがCSVに出力されていることを確認
    csv_content = csv_path.read_text(encoding="utf-8").strip()
    lines = csv_content.split("\n")
    assert len(lines) == 1  # supportedだった1件のみ
    assert "42%" in lines[0]


@pytest.mark.asyncio
async def test_run_review_auto_mode_custom_output(tmp_path: Path):
    """output指定でCSVパスをカスタマイズできることを確認。"""
    report_path = _make_report_json(tmp_path)
    custom_csv = tmp_path / "custom_output.csv"

    csv_path = await run_review(report_path, output_csv=custom_csv, auto_mode=True)

    assert csv_path == custom_csv
    assert csv_path.exists()


@pytest.mark.asyncio
async def test_run_review_rebuilds_summary(tmp_path: Path):
    """reviewがsummaryを再構築することを確認。"""
    report_path = _make_report_json(tmp_path)

    await run_review(report_path, auto_mode=True)

    updated = json.loads(report_path.read_text(encoding="utf-8"))
    summary = updated["summary"]
    assert summary["adopted"] == 1
    assert summary["rejected"] == 3
    assert "orphaned" not in summary
    assert "supported" not in summary
