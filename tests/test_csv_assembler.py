"""CsvAssembler テスト (SP-032 Gap 1, SP-033 拡張, SP-052 overlay)"""
import csv
import json
from pathlib import Path

import pytest

from core.csv_assembler import CsvAssembler
from core.visual.models import AnimationType


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


class TestCsvAssemblerAnimation:
    """SP-033: CSV 4列目（アニメーション種別）のテスト"""

    def test_auto_animation_adds_4th_column(self, tmp_path):
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        for i in range(3):
            (slides_dir / f"slide_{i:04d}.png").write_bytes(b"\x89PNG")
        slide_paths = sorted(slides_dir.glob("*.png"))

        segments = [
            {"speaker": "A", "content": "t1"},
            {"speaker": "B", "content": "t2"},
            {"speaker": "A", "content": "t3"},
        ]
        out = tmp_path / "out.csv"
        assembler = CsvAssembler()
        assembler.assemble(segments, slide_paths, out, auto_animation=True)
        rows = _read_csv(out)

        # 全行が4列
        for row in rows:
            assert len(row) == 4, f"Expected 4 columns, got {len(row)}: {row}"

        # 4列目が有効なアニメーション種別
        valid = {t.value for t in AnimationType}
        for row in rows:
            assert row[3] in valid, f"Invalid animation type: {row[3]}"

    def test_text_slides_default_all_static(self, tmp_path):
        """デフォルト (text_slides=True) では全画像が static になる。"""
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        for i in range(3):
            (slides_dir / f"slide_{i:04d}.png").write_bytes(b"\x89PNG")
        slide_paths = sorted(slides_dir.glob("*.png"))

        segments = [{"speaker": "A", "content": f"t{i}"} for i in range(3)]
        out = tmp_path / "out.csv"
        assembler = CsvAssembler()
        assembler.assemble(segments, slide_paths, out, auto_animation=True)
        rows = _read_csv(out)

        for row in rows:
            assert row[3] == "static"

    def test_auto_animation_disabled(self, tmp_path):
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        (slides_dir / "slide_0000.png").write_bytes(b"\x89PNG")
        slide_paths = sorted(slides_dir.glob("*.png"))

        segments = [{"speaker": "A", "content": "t1"}]
        out = tmp_path / "out.csv"
        assembler = CsvAssembler()
        assembler.assemble(segments, slide_paths, out, auto_animation=False)
        rows = _read_csv(out)

        assert len(rows[0]) == 4
        assert rows[0][3] == "ken_burns"

    def test_no_slides_uses_static(self, tmp_path):
        segments = [{"speaker": "A", "content": "t1"}]
        out = tmp_path / "out.csv"
        assembler = CsvAssembler()
        assembler.assemble(segments, [], out, auto_animation=True)
        rows = _read_csv(out)

        assert rows[0][3] == "static"


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


class TestOverlayPlanGeneration:
    """SP-052: CsvAssembler からの overlay_plan.json 自動生成テスト。"""

    def test_overlay_generated_with_script_data(self, tmp_path):
        """script_data を渡すと overlay_plan.json が生成される。"""
        script_data = {
            "title": "テスト動画",
            "segments": [
                {
                    "section": "導入",
                    "speaker": "Host1",
                    "content": "こんにちは",
                    "duration_estimate": 5.0,
                    "key_points": ["テストポイント"],
                },
                {
                    "section": "本論",
                    "speaker": "Host2",
                    "content": "本題に入ります",
                    "duration_estimate": 10.0,
                    "key_points": ["メインポイント"],
                },
            ],
        }

        out = tmp_path / "output" / "timeline.csv"
        assembler = CsvAssembler()
        assembler.assemble(
            script_segments=script_data["segments"],
            slide_image_paths=[],
            output_path=out,
            script_data=script_data,
        )

        overlay_path = tmp_path / "output" / "overlay_plan.json"
        assert overlay_path.exists()

        data = json.loads(overlay_path.read_text(encoding="utf-8"))
        assert data["version"] == "1.0"
        assert len(data["overlays"]) >= 2  # at least 2 chapter_titles

    def test_no_overlay_without_key_points(self, tmp_path):
        """key_points が空で section が全て同じなら overlay は chapter_title のみ。"""
        segments = [
            {"speaker": "A", "content": "テキスト", "section": "同じセクション"},
            {"speaker": "B", "content": "テキスト2", "section": "同じセクション"},
        ]

        out = tmp_path / "timeline.csv"
        assembler = CsvAssembler()
        assembler.assemble(segments, [], out, script_data={"segments": segments})

        overlay_path = tmp_path / "overlay_plan.json"
        assert overlay_path.exists()

        data = json.loads(overlay_path.read_text(encoding="utf-8"))
        chapter_titles = [o for o in data["overlays"] if o["type"] == "chapter_title"]
        assert len(chapter_titles) == 1  # 1 section change only

    def test_overlay_not_generated_without_content(self, tmp_path):
        """key_points も section もない場合は overlay_plan.json が生成されない。"""
        segments = [
            {"speaker": "A", "content": "テキスト"},
        ]

        out = tmp_path / "timeline.csv"
        assembler = CsvAssembler()
        assembler.assemble(segments, [], out)

        overlay_path = tmp_path / "overlay_plan.json"
        # section/key_points がないので overlays は空 → ファイル生成されない
        assert not overlay_path.exists()

    def test_from_script_bundle_generates_overlay(self, tmp_path):
        """from_script_bundle 経由でも overlay_plan.json が生成される。"""
        script_bundle = {
            "title": "バンドルテスト",
            "segments": [
                {
                    "section": "Part1",
                    "speaker": "Host1",
                    "content": "ファーストセグメント",
                    "duration_estimate": 8.0,
                    "key_points": ["ポイント1"],
                },
                {
                    "section": "Part2",
                    "speaker": "Host2",
                    "content": "セカンドセグメント",
                    "duration_estimate": 10.0,
                    "key_points": [],
                },
            ],
        }

        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()

        out = tmp_path / "output" / "timeline.csv"
        CsvAssembler.from_script_bundle(script_bundle, slides_dir, out)

        overlay_path = tmp_path / "output" / "overlay_plan.json"
        assert overlay_path.exists()

        data = json.loads(overlay_path.read_text(encoding="utf-8"))
        assert len(data["overlays"]) >= 2
