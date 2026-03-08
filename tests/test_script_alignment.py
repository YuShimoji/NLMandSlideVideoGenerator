from pathlib import Path

import pytest

from notebook_lm.research_models import ResearchPackage
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
