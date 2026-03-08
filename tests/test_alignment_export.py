
from src.notebook_lm.script_alignment import ScriptAlignmentAnalyzer

def test_export_to_csv(tmp_path):
    analyzer = ScriptAlignmentAnalyzer()
    analysis = [
        {
            "segment_index": 1,
            "speaker": "Speaker1",
            "text": "Supported text",
            "status": "supported"
        },
        {
            "segment_index": 2,
            "speaker": "Speaker2",
            "text": "Adopted text",
            "status": "adopted"
        },
        {
            "segment_index": 3,
            "speaker": "Speaker1",
            "text": "Orphaned text",
            "status": "orphaned"
        },
        {
            "segment_index": 4,
            "speaker": "Speaker2",
            "text": "Conflict text",
            "status": "conflict"
        },
        {
            "segment_index": 5,
            "speaker": "Speaker1",
            "text": "Rejected text",
            "status": "rejected"
        },
        {
            "segment_index": None,
            "speaker": None,
            "text": None,
            "status": "missing",
            "matched_claim": "Missing claim"
        }
    ]

    output_path = tmp_path / "test_output.csv"
    analyzer.export_to_csv(analysis, output_path)

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    lines = content.strip().splitlines()

    # supported と adopted のみが抽出されるはず
    assert len(lines) == 2
    assert "Speaker1,Supported text" in lines[0]
    assert "Speaker2,Adopted text" in lines[1]

def test_export_to_csv_default_speaker(tmp_path):
    analyzer = ScriptAlignmentAnalyzer()
    analysis = [
        {
            "segment_index": 1,
            "speaker": "",
            "text": "No speaker text",
            "status": "adopted"
        }
    ]

    output_path = tmp_path / "test_default.csv"
    analyzer.export_to_csv(analysis, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "ナレーター,No speaker text" in content
