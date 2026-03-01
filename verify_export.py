
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path("src").absolute()))

from notebook_lm.script_alignment import ScriptAlignmentAnalyzer

def test_manual():
    analyzer = ScriptAlignmentAnalyzer()
    analysis = [
        {"segment_index": 1, "speaker": "Speaker1", "text": "Test 1", "status": "supported"},
        {"segment_index": 2, "speaker": "Speaker2", "text": "Test 2", "status": "adopted"},
        {"segment_index": 3, "speaker": "Speaker1", "text": "Test 3", "status": "rejected"},
    ]
    output_path = Path("manual_test_output.csv")
    analyzer.export_to_csv(analysis, output_path)
    print(f"File created: {output_path.exists()}")
    if output_path.exists():
        print(f"Content:\n{output_path.read_text(encoding='utf-8')}")

if __name__ == "__main__":
    test_manual()
