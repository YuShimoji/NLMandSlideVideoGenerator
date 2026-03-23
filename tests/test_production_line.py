"""ProductionLine データモデル + ストアのテスト (SP-053)"""

import json
from pathlib import Path

import pytest

from src.core.production_line import (
    LineStatus,
    ProductionLine,
    ProductionLineStore,
    _slugify,
)


class TestProductionLine:
    """ProductionLineデータモデルのテスト"""

    def test_create_sets_defaults(self):
        line = ProductionLine.create("量子コンピュータの最新動向")
        assert line.topic == "量子コンピュータの最新動向"
        assert line.status == "draft"
        assert line.current_phase == 0
        assert line.line_id  # 非空
        assert line.created_at  # 非空
        # Windowsではバックスラッシュになるため正規化して比較
        assert line.topic_dir.replace("\\", "/").startswith("data/topics/")
        # topic_dirはslugifiedされたトピック名を含む
        assert line.line_id[:6] in line.topic_dir

    def test_create_custom_base_dir(self):
        line = ProductionLine.create("test", base_dir="custom/dir")
        assert "custom/dir" in line.topic_dir.replace("\\", "/")

    def test_advance_phase(self):
        line = ProductionLine.create("test")
        line.advance_phase(2)
        assert line.current_phase == 2
        assert "phase_2_start" in line.phase_timestamps

    def test_complete_phase(self):
        line = ProductionLine.create("test")
        line.advance_phase(1)
        line.complete_phase(1)
        assert "phase_1_end" in line.phase_timestamps

    def test_set_status(self):
        line = ProductionLine.create("test")
        line.set_status(LineStatus.STRUCTURING)
        assert line.status == "structuring"

    def test_add_error(self):
        line = ProductionLine.create("test")
        line.add_error("Something went wrong")
        assert len(line.error_log) == 1
        assert "Something went wrong" in line.error_log[0]

    def test_to_dict_roundtrip(self):
        line = ProductionLine.create("roundtrip test")
        line.source_urls = ["https://example.com"]
        line.segment_count = 42
        d = line.to_dict()
        restored = ProductionLine.from_dict(d)
        assert restored.topic == "roundtrip test"
        assert restored.source_urls == ["https://example.com"]
        assert restored.segment_count == 42
        assert restored.line_id == line.line_id

    def test_from_dict_ignores_unknown_fields(self):
        data = {"topic": "test", "line_id": "abc", "unknown_field": 999}
        line = ProductionLine.from_dict(data)
        assert line.topic == "test"

    def test_display_status(self):
        line = ProductionLine.create("test")
        assert line.display_status == "下書き"
        line.set_status(LineStatus.PRODUCING)
        assert line.display_status == "YMM4制作中"

    def test_phase_column_nlm(self):
        line = ProductionLine.create("test")
        line.current_phase = 0
        assert line.phase_column == "nlm"
        line.current_phase = 1
        assert line.phase_column == "nlm"

    def test_phase_column_structuring(self):
        line = ProductionLine.create("test")
        line.current_phase = 3
        assert line.phase_column == "structuring"

    def test_phase_column_producing(self):
        line = ProductionLine.create("test")
        line.current_phase = 6
        assert line.phase_column == "producing"

    def test_phase_column_publishing(self):
        line = ProductionLine.create("test")
        line.current_phase = 7
        assert line.phase_column == "publishing"

    def test_phase_column_done_overrides(self):
        line = ProductionLine.create("test")
        line.current_phase = 3
        line.set_status(LineStatus.DONE)
        assert line.phase_column == "done"


class TestProductionLineStore:
    """ProductionLineStoreの永続化テスト"""

    def test_add_and_get(self, tmp_path: Path):
        store = ProductionLineStore(tmp_path / "lines.json")
        line = ProductionLine.create("store test")
        store.add(line)

        retrieved = store.get(line.line_id)
        assert retrieved is not None
        assert retrieved.topic == "store test"

    def test_persistence(self, tmp_path: Path):
        path = tmp_path / "lines.json"
        store1 = ProductionLineStore(path)
        line = ProductionLine.create("persist test")
        store1.add(line)

        # 新しいインスタンスで読み直し
        store2 = ProductionLineStore(path)
        retrieved = store2.get(line.line_id)
        assert retrieved is not None
        assert retrieved.topic == "persist test"

    def test_update(self, tmp_path: Path):
        store = ProductionLineStore(tmp_path / "lines.json")
        line = ProductionLine.create("update test")
        store.add(line)

        line.segment_count = 99
        store.update(line)

        retrieved = store.get(line.line_id)
        assert retrieved is not None
        assert retrieved.segment_count == 99

    def test_delete(self, tmp_path: Path):
        store = ProductionLineStore(tmp_path / "lines.json")
        line = ProductionLine.create("delete test")
        store.add(line)

        assert store.delete(line.line_id) is True
        assert store.get(line.line_id) is None

    def test_delete_nonexistent(self, tmp_path: Path):
        store = ProductionLineStore(tmp_path / "lines.json")
        assert store.delete("nonexistent") is False

    def test_list_all_sorted(self, tmp_path: Path):
        import time
        store = ProductionLineStore(tmp_path / "lines.json")
        line1 = ProductionLine.create("first")
        store.add(line1)
        time.sleep(0.01)  # タイムスタンプの差を確保
        line2 = ProductionLine.create("second")
        store.add(line2)

        all_lines = store.list_all()
        assert len(all_lines) == 2
        # 降順: 最新が先
        assert all_lines[0].topic == "second"

    def test_list_by_status(self, tmp_path: Path):
        store = ProductionLineStore(tmp_path / "lines.json")
        line1 = ProductionLine.create("draft line")
        store.add(line1)
        line2 = ProductionLine.create("structuring line")
        line2.set_status(LineStatus.STRUCTURING)
        store.add(line2)

        drafts = store.list_by_status(LineStatus.DRAFT)
        assert len(drafts) == 1
        assert drafts[0].topic == "draft line"

    def test_list_by_column(self, tmp_path: Path):
        store = ProductionLineStore(tmp_path / "lines.json")
        line1 = ProductionLine.create("nlm line")
        line1.current_phase = 1
        store.add(line1)
        line2 = ProductionLine.create("struct line")
        line2.current_phase = 3
        store.add(line2)

        nlm = store.list_by_column("nlm")
        assert len(nlm) == 1
        assert nlm[0].topic == "nlm line"

    def test_count_by_status(self, tmp_path: Path):
        store = ProductionLineStore(tmp_path / "lines.json")
        store.add(ProductionLine.create("a"))
        store.add(ProductionLine.create("b"))
        line_c = ProductionLine.create("c")
        line_c.set_status(LineStatus.DONE)
        store.add(line_c)

        counts = store.count_by_status()
        assert counts.get("draft") == 2
        assert counts.get("done") == 1

    def test_empty_store(self, tmp_path: Path):
        store = ProductionLineStore(tmp_path / "nonexistent.json")
        assert store.list_all() == []

    def test_corrupt_file(self, tmp_path: Path):
        path = tmp_path / "corrupt.json"
        path.write_text("not valid json", encoding="utf-8")
        store = ProductionLineStore(path)
        assert store.list_all() == []

    def test_json_format(self, tmp_path: Path):
        path = tmp_path / "lines.json"
        store = ProductionLineStore(path)
        store.add(ProductionLine.create("format check"))

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert "updated_at" in data
        assert len(data["lines"]) == 1


class TestSlugify:
    """_slugify関数のテスト"""

    def test_ascii(self):
        assert _slugify("hello world") == "hello_world"

    def test_japanese(self):
        result = _slugify("量子コンピュータの最新動向")
        assert "量子コンピュータの最新動向" == result

    def test_mixed(self):
        result = _slugify("AI技術 2026年版!!")
        assert "!!" not in result
        assert "ai技術" in result

    def test_empty(self):
        assert _slugify("") == "untitled"
        assert _slugify("!!!") == "untitled"

    def test_special_chars(self):
        result = _slugify("path/to/file.txt")
        assert "/" not in result
        assert "." not in result
