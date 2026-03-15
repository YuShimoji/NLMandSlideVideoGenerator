import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from notebook_lm.research_models import AlignmentReport, ResearchPackage
from notebook_lm.script_alignment import ScriptAlignmentAnalyzer
from notebook_lm.source_collector import SourceInfo


def _build_package() -> ResearchPackage:
    return ResearchPackage(
        package_id="rp_test",
        topic="AIの将来",
        created_at="2026-02-28T18:00:00+09:00",
        sources=[
            SourceInfo(
                url="https://example.com/source1",
                title="AIの将来に関するレポート",
                content_preview="AI導入率は2026年に42%へ上昇し、教育分野で活用が拡大している。",
                relevance_score=0.9,
                reliability_score=0.9,
                source_type="article",
                key_claims=[
                    "AI導入率は2026年に42%へ上昇した",
                    "教育分野で活用が拡大している",
                ],
            )
        ],
    )


def test_extract_claims_uses_sentences_and_key_points():
    analyzer = ScriptAlignmentAnalyzer()

    claims = analyzer.extract_claims(
        "AI導入率は2026年に42%へ上昇しました。教育分野で活用が拡大しています。",
        key_points=["教育分野で活用が拡大している"],
    )

    assert "AI導入率は2026年に42%へ上昇しました" in claims
    assert "教育分野で活用が拡大している" in claims


@pytest.mark.asyncio
async def test_analyze_generates_supported_missing_and_conflict():
    analyzer = ScriptAlignmentAnalyzer()
    package = _build_package()
    normalized_script = {
        "title": "テスト",
        "segments": [
            {"index": 1, "speaker": "A", "text": "AI導入率は2026年に42%へ上昇した。", "key_points": []},
            {"index": 2, "speaker": "B", "text": "AI導入率は2026年に50%へ上昇した。", "key_points": []},
        ],
    }

    report = await analyzer.analyze(package, normalized_script)

    assert report.summary["supported"] == 1
    assert report.summary["conflict"] == 1
    assert report.summary["missing"] == 1
    assert any(item["status"] == "missing" for item in report.analysis)


@pytest.mark.asyncio
async def test_load_script_from_txt(tmp_path: Path):
    script_path = tmp_path / "script.txt"
    script_path.write_text("1行目の主張です。\n2行目の主張です。", encoding="utf-8")

    analyzer = ScriptAlignmentAnalyzer()
    normalized = await analyzer.load_script(script_path)

    assert len(normalized["segments"]) == 2
    assert normalized["segments"][0]["text"] == "1行目の主張です。"


@pytest.mark.asyncio
async def test_llm_alignment_rescues_orphaned_items():
    """LLMセマンティックマッチングがorphanedアイテムをsupportedに変更できることを確認。"""
    analyzer = ScriptAlignmentAnalyzer()

    # 英語の key_claims と日本語の台本テキストでトークンマッチが失敗するケース
    package = ResearchPackage(
        package_id="rp_llm_test",
        topic="Quantum computing",
        created_at="2026-03-15T00:00:00+09:00",
        sources=[
            SourceInfo(
                url="https://example.com/quantum",
                title="Quantum Computing Report",
                content_preview="IBM announced a 1000-qubit processor.",
                relevance_score=0.9,
                reliability_score=0.9,
                source_type="news",
                key_claims=["IBM announced a 1000-qubit processor"],
            )
        ],
    )

    normalized_script = {
        "title": "テスト",
        "segments": [
            {
                "index": 1,
                "speaker": "Host",
                "text": "IBMが1000量子ビットプロセッサを発表しました。",
                "key_points": [],
            },
        ],
    }

    # Gemini APIのモックを設定
    mock_llm_response = MagicMock()
    mock_llm_response.text = '{"matches": [{"sentence_id": 1, "matched_claim_keys": ["https://example.com/quantum::IBM announced a 1000-qubit processor"]}]}'

    mock_model_instance = MagicMock()
    mock_model_instance.generate_content = MagicMock(return_value=mock_llm_response)

    with patch("google.generativeai.configure"), \
         patch("google.generativeai.GenerativeModel", return_value=mock_model_instance), \
         patch("config.settings.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = "fake-key"
        report = await analyzer.analyze(package, normalized_script)

    # LLMマッチングによりorphanedからsupportedに変わっているか確認
    seg1 = next(item for item in report.analysis if item.get("segment_index") == 1)
    assert seg1["status"] == "supported"
    assert seg1["matched_source"] == "https://example.com/quantum"


@pytest.mark.asyncio
async def test_llm_alignment_skipped_without_api_key():
    """APIキー未設定時にLLMマッチングがスキップされ、orphanedのまま残ることを確認。"""
    analyzer = ScriptAlignmentAnalyzer()

    package = ResearchPackage(
        package_id="rp_nokey",
        topic="Test",
        created_at="2026-03-15T00:00:00+09:00",
        sources=[
            SourceInfo(
                url="https://example.com/en",
                title="English Source",
                content_preview="Important discovery in physics.",
                relevance_score=0.9,
                reliability_score=0.9,
                source_type="article",
                key_claims=["Important discovery in physics"],
            )
        ],
    )

    normalized_script = {
        "title": "テスト",
        "segments": [
            {
                "index": 1,
                "speaker": "Host",
                "text": "物理学で重要な発見がありました。",
                "key_points": [],
            },
        ],
    }

    with patch("config.settings.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = ""
        report = await analyzer.analyze(package, normalized_script)

    seg1 = next(item for item in report.analysis if item.get("segment_index") == 1)
    assert seg1["status"] == "orphaned"


def test_alignment_report_update_item_status():
    """AlignmentReport.update_item_status() のテスト。"""
    report = AlignmentReport(
        report_id="ar_test",
        package_id="rp_test",
        analysis=[
            {"segment_index": 1, "text": "テスト文", "status": "orphaned"},
            {"segment_index": 2, "text": "別の文", "status": "supported"},
        ],
        summary={"total_segments": 2, "orphaned": 1, "supported": 1},
    )

    assert report.update_item_status(1, "adopted")
    assert report.analysis[0]["status"] == "adopted"

    assert report.update_item_status(1, "adopted", new_text="修正済みテスト文")
    assert report.analysis[0]["text"] == "修正済みテスト文"

    assert not report.update_item_status(99, "adopted")


def test_alignment_report_rebuild_summary():
    """AlignmentReport.rebuild_summary() のテスト。"""
    report = AlignmentReport(
        report_id="ar_test",
        package_id="rp_test",
        analysis=[
            {"segment_index": 1, "text": "A", "status": "adopted"},
            {"segment_index": 2, "text": "B", "status": "rejected"},
            {"segment_index": None, "text": None, "status": "missing"},
        ],
        summary={},
    )

    report.rebuild_summary()

    assert report.summary["total_segments"] == 2
    assert report.summary["adopted"] == 1
    assert report.summary["rejected"] == 1
    assert report.summary["missing"] == 1
    assert "supported" not in report.summary
