"""CsvAssembler テスト (SP-032 Gap 1)"""
import csv
from pathlib import Path

import pytest

from core.csv_assembler import CsvAssembler


@pytest.fixture
def assembler():
    return CsvAssembler()


@pytest.fixture
def tmp_slides(tmp_path):
    """テスト用スライドPNGファイルを作成"""
    slides_dir = tmp_path / "slides"
    slides_dir.mkdir()
    paths = []
    for i in range(3):
        p = slides_dir / f"slide_{i:04d}.png"
        p.write_bytes(b"\x89PNG")  # minimal PNG header
        paths.append(p)
    return paths


def _read_csv(path: Path):
    with open(path, encoding="utf-8") as f:
        return list(csv.reader(f))


class TestCsvAssembler:
    def test_equal_segments_and_slides(self, assembler, tmp_slides, tmp_path):
        """セグメント数 == スライド数 → 1:1マッチ"""
        segments = [
            {"speaker": "Host1", "content": "テキスト1"},
            {"speaker": "Host2", "content": "テキスト2"},
            {"speaker": "Host1", "content": "テキスト3"},
        ]
        out = tmp_path / "out.csv"
        assembler.assemble(segments, tmp_slides, out)
        rows = _read_csv(out)
        assert len(rows) == 3
        assert rows[0][0] == "Host1"
        assert rows[0][2] == str(tmp_slides[0].resolve())
        assert rows[1][2] == str(tmp_slides[1].resolve())
        assert rows[2][2] == str(tmp_slides[2].resolve())

    def test_more_segments_than_slides(self, assembler, tmp_slides, tmp_path):
        """セグメント6 > スライド3 → 均等分割"""
        segments = [{"speaker": f"S{i}", "content": f"T{i}"} for i in range(6)]
        out = tmp_path / "out.csv"
        assembler.assemble(segments, tmp_slides, out)
        rows = _read_csv(out)
        assert len(rows) == 6
        # 最初の2行は同じスライド
        assert rows[0][2] == rows[1][2]
        assert rows[2][2] == rows[3][2]
        assert rows[4][2] == rows[5][2]
        # 異なるスライド
        assert rows[0][2] != rows[2][2]

    def test_fewer_segments_than_slides(self, assembler, tmp_slides, tmp_path):
        """セグメント2 < スライド3 → 1:1、余剰スライド無視"""
        segments = [
            {"speaker": "Host1", "content": "テキスト1"},
            {"speaker": "Host2", "content": "テキスト2"},
        ]
        out = tmp_path / "out.csv"
        assembler.assemble(segments, tmp_slides, out)
        rows = _read_csv(out)
        assert len(rows) == 2
        assert rows[0][2] == str(tmp_slides[0].resolve())
        assert rows[1][2] == str(tmp_slides[1].resolve())

    def test_no_slides(self, assembler, tmp_path):
        """スライド0件 → 画像パス空欄"""
        segments = [{"speaker": "Host1", "content": "テキスト1"}]
        out = tmp_path / "out.csv"
        assembler.assemble(segments, [], out)
        rows = _read_csv(out)
        assert len(rows) == 1
        assert rows[0][2] == ""

    def test_empty_segments_raises(self, assembler, tmp_slides, tmp_path):
        """セグメント空 → ValueError"""
        out = tmp_path / "out.csv"
        with pytest.raises(ValueError, match="空"):
            assembler.assemble([], tmp_slides, out)

    def test_speaker_mapping(self, assembler, tmp_slides, tmp_path):
        """話者マッピングが適用される"""
        segments = [{"speaker": "Host1", "content": "テキスト1"}]
        mapping = {"Host1": "ずんだもん"}
        out = tmp_path / "out.csv"
        assembler.assemble(segments, tmp_slides, out, speaker_mapping=mapping)
        rows = _read_csv(out)
        assert rows[0][0] == "ずんだもん"

    def test_text_field_fallback(self, assembler, tmp_slides, tmp_path):
        """content がなく text フィールドがある場合"""
        segments = [{"speaker": "Host1", "text": "テキストfallback"}]
        out = tmp_path / "out.csv"
        assembler.assemble(segments, tmp_slides, out)
        rows = _read_csv(out)
        assert rows[0][1] == "テキストfallback"

    def test_from_script_bundle(self, tmp_path):
        """from_script_bundle 便利メソッド"""
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        for i in range(2):
            (slides_dir / f"slide_{i:04d}.png").write_bytes(b"\x89PNG")

        bundle = {
            "title": "テスト台本",
            "segments": [
                {"speaker": "Host1", "content": "セグメント1"},
                {"speaker": "Host2", "content": "セグメント2"},
            ],
        }
        out = tmp_path / "out.csv"
        CsvAssembler.from_script_bundle(bundle, slides_dir, out)
        rows = _read_csv(out)
        assert len(rows) == 2
        assert "slide_0000.png" in rows[0][2]
        assert "slide_0001.png" in rows[1][2]


class TestComputeMapping:
    def test_equal(self):
        m = CsvAssembler._compute_mapping(3, 3)
        assert m == {0: 0, 1: 1, 2: 2}

    def test_more_segments(self):
        m = CsvAssembler._compute_mapping(6, 3)
        assert m[0] == 0
        assert m[1] == 0
        assert m[2] == 1
        assert m[3] == 1
        assert m[4] == 2
        assert m[5] == 2

    def test_fewer_segments(self):
        m = CsvAssembler._compute_mapping(2, 5)
        assert m == {0: 0, 1: 1}

    def test_no_slides(self):
        m = CsvAssembler._compute_mapping(3, 0)
        assert all(v is None for v in m.values())

    def test_single_slide(self):
        m = CsvAssembler._compute_mapping(5, 1)
        assert all(v == 0 for v in m.values())
