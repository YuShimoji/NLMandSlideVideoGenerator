"""
Research workflow E2E test: collect → align → review → CSV
外部APIは使わず、シミュレーション/モックで一気通貫の統合テストを行う。
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.research_cli import run_alignment, run_research, run_review


@pytest.fixture
def research_tmp(tmp_path: Path):
    """RESEARCH_SETTINGS の data_dir を tmp_path に差し替える fixture。"""
    from config.settings import settings as real_settings

    original_research = real_settings.RESEARCH_SETTINGS.copy()
    original_data_dir = real_settings.DATA_DIR

    real_settings.RESEARCH_SETTINGS = {
        "data_dir": tmp_path / "research",
        "max_sources": 3,
        "google_search_api_key": "",
        "google_search_cx": "",
    }
    real_settings.DATA_DIR = tmp_path

    yield real_settings, tmp_path

    real_settings.RESEARCH_SETTINGS = original_research
    real_settings.DATA_DIR = original_data_dir


@pytest.mark.asyncio
async def test_e2e_collect_align_review(research_tmp):
    """collect → align → review → CSV の全フローが正常に動作することを確認。"""
    mock_settings, tmp_path = research_tmp
    topic = "量子コンピュータの最新動向"

    # ========== Step 1: collect (シミュレーションモード) ==========
    await run_research(topic, max_sources=3)

    research_dir = tmp_path / "research"
    package_dirs = list(research_dir.glob("rp_*"))
    assert len(package_dirs) == 1, f"Expected 1 package dir, got {len(package_dirs)}"

    package_dir = package_dirs[0]
    package_path = package_dir / "package.json"
    assert package_path.exists()

    package_data = json.loads(package_path.read_text(encoding="utf-8"))
    assert package_data["topic"] == topic
    assert len(package_data["sources"]) == 3

    # ========== Step 2: 台本作成 (テスト用) ==========
    # シミュレーションの key_claims に一致する行と、一致しない行を含む台本を作成
    script_path = tmp_path / "draft_script.txt"
    script_lines = [
        # key_claimsの内容を含むので supported になるはず
        f"Simulated source 1 is related to {topic}.",
        # key_claimsとは異なる内容なので orphaned になるはず
        "この主張は資料に根拠がありません。独自の見解です。",
        # 数値を含む conflict を誘発するテスト行
        f"Simulated source 2 is related to {topic}.",
    ]
    script_path.write_text("\n".join(script_lines), encoding="utf-8")

    # ========== Step 3: align ==========
    report_path = await run_alignment(package_path, script_path)

    assert report_path.exists()
    report_data = json.loads(report_path.read_text(encoding="utf-8"))

    assert report_data["package_id"] == package_data["package_id"]
    assert "analysis" in report_data
    assert "summary" in report_data
    assert report_data["summary"]["total_segments"] > 0

    # supported が少なくとも1つ存在する
    statuses = [item["status"] for item in report_data["analysis"]]
    assert "supported" in statuses, f"No supported items found in: {statuses}"

    # ========== Step 4: review (auto mode) ==========
    csv_path = tmp_path / "final_output.csv"
    result_csv = await run_review(report_path, output_csv=csv_path, auto_mode=True)

    assert result_csv == csv_path
    assert csv_path.exists()

    # CSVに adopted 分のみ出力されている
    csv_content = csv_path.read_text(encoding="utf-8").strip()
    assert len(csv_content) > 0, "CSV is empty"

    # レポートが更新されている
    updated_report = json.loads(report_path.read_text(encoding="utf-8"))
    updated_statuses = {item["status"] for item in updated_report["analysis"]}
    assert "supported" not in updated_statuses, "supported should be converted to adopted"
    assert "orphaned" not in updated_statuses, "orphaned should be converted to rejected"

    # summary が再構築されている
    summary = updated_report["summary"]
    assert "adopted" in summary or "rejected" in summary


@pytest.mark.asyncio
async def test_e2e_align_and_review_roundtrip(research_tmp):
    """align で生成された report を review で処理し、CSV行数が整合することを確認。"""
    mock_settings, tmp_path = research_tmp

    # 手動でパッケージを作成
    package_dir = tmp_path / "research" / "rp_manual"
    package_dir.mkdir(parents=True)
    package_path = package_dir / "package.json"
    package_path.write_text(
        json.dumps(
            {
                "package_id": "rp_manual",
                "topic": "テスト",
                "created_at": "2026-03-15T00:00:00",
                "sources": [
                    {
                        "url": "https://example.com/s1",
                        "title": "Source 1",
                        "content_preview": "AIは産業に革命を起こしている。",
                        "relevance_score": 0.9,
                        "reliability_score": 0.9,
                        "source_type": "article",
                        "adoption_status": "pending",
                        "adoption_reason": "",
                        "key_claims": [
                            "AIは産業に革命を起こしている",
                            "2026年までにAI市場は500億ドル規模",
                        ],
                    },
                    {
                        "url": "https://example.com/s2",
                        "title": "Source 2",
                        "content_preview": "医療AIの精度が95%に到達。",
                        "relevance_score": 0.85,
                        "reliability_score": 0.85,
                        "source_type": "news",
                        "adoption_status": "pending",
                        "adoption_reason": "",
                        "key_claims": ["医療AIの精度が95%に到達"],
                    },
                ],
                "summary": "",
                "review_status": "pending",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # 台本: 1行 supported, 1行 orphaned, 1行 conflict (95→99)
    script_path = tmp_path / "script.csv"
    script_path.write_text(
        "Host1,AIは産業に革命を起こしている。\n"
        "Host2,宇宙開発は新たなフェーズに入った。\n"
        "Host1,医療AIの精度が99%に到達した。\n",
        encoding="utf-8",
    )

    # align
    report_path = await run_alignment(package_path, script_path)
    report_data = json.loads(report_path.read_text(encoding="utf-8"))

    supported_count = sum(
        1 for item in report_data["analysis"]
        if item.get("status") == "supported" and item.get("segment_index") is not None
    )

    # review (auto)
    csv_path = tmp_path / "roundtrip.csv"
    await run_review(report_path, output_csv=csv_path, auto_mode=True)

    # CSV行数 == supported + adopted のセグメント数
    csv_lines = [
        line for line in csv_path.read_text(encoding="utf-8").strip().split("\n") if line
    ]
    assert len(csv_lines) == supported_count
