import pytest
from notebook_lm.source_collector import SourceInfo
from notebook_lm.research_models import ResearchPackage, AlignmentReport
from dataclasses import asdict

def test_source_info_new_fields():
    source = SourceInfo(
        url="https://example.com",
        title="Test",
        content_preview="Preview",
        relevance_score=0.9,
        reliability_score=0.8,
        source_type="news",
        adoption_status="pending",
        key_claims=["Claim 1"]
    )
    assert source.adoption_status == "pending"
    assert source.key_claims == ["Claim 1"]

def test_research_package_serialization():
    source = SourceInfo(
        url="https://example.com",
        title="Test",
        content_preview="Preview",
        relevance_score=0.9,
        reliability_score=0.8,
        source_type="news"
    )
    package = ResearchPackage(
        package_id="rp_test",
        topic="Test Topic",
        created_at="2026-02-28T17:00:00",
        sources=[source],
        summary="Test Summary"
    )
    
    data = package.to_dict()
    assert data["package_id"] == "rp_test"
    assert data["sources"][0]["url"] == "https://example.com"
    
    # Restore from dict
    restored = ResearchPackage.from_dict(data)
    assert restored.package_id == "rp_test"
    assert restored.sources[0].url == "https://example.com"
    assert isinstance(restored.sources[0], SourceInfo)

def test_alignment_report_serialization():
    report = AlignmentReport(
        report_id="ar_test",
        package_id="rp_test",
        analysis=[{"segment_index": 1, "status": "supported"}],
        summary={"total": 1}
    )
    
    data = report.to_dict()
    assert data["report_id"] == "ar_test"
    assert data["analysis"][0]["status"] == "supported"
    
    restored = AlignmentReport.from_dict(data)
    assert restored.report_id == "ar_test"
    assert restored.analysis[0]["status"] == "supported"
