import sys
from pathlib import Path
from typing import Any


# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.editing.ymm4_backend import YMM4EditingBackend  # noqa: E402


def test_ymm4_record_export_outputs_includes_template_diff(tmp_path: Path):
    """YMM4EditingBackend が export_outputs['ymm4'] に template_diff を含めることを確認"""

    # プロジェクトディレクトリと関連ファイルを準備
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project_file = project_dir / "project.y4mmp"
    project_file.touch()

    # _record_export_outputs で参照されるファイルを用意
    (project_dir / "timeline_plan.json").write_text("{}", encoding="utf-8")
    (project_dir / "slides_payload.json").write_text("{}", encoding="utf-8")
    audio_dir = project_dir / "audio"
    audio_dir.mkdir()
    (project_dir / "template_diff_applied.json").write_text("{}", encoding="utf-8")

    backend = YMM4EditingBackend(
        project_template=tmp_path / "template.y4mmp",
        workspace_dir=tmp_path,
        auto_hotkey_script=tmp_path / "dummy.ahk",
    )

    extras: dict[str, Any] = {}
    backend._record_export_outputs(project_dir, project_file, extras)

    assert "export_outputs" in extras
    ymm4_outputs = extras["export_outputs"].get("ymm4")
    assert ymm4_outputs is not None
    assert ymm4_outputs.get("template_diff").endswith("template_diff_applied.json")
