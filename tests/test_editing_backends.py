import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from datetime import datetime
import asyncio

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.editing.moviepy_backend import MoviePyEditingBackend  # noqa: E402
from core.editing.ymm4_backend import YMM4EditingBackend  # noqa: E402
from video_editor.video_composer import VideoInfo  # noqa: E402


def test_moviepy_editing_backend_render():
    backend = MoviePyEditingBackend()

    # モックデータ
    timeline_plan = {
        "total_duration": 120.0,
        "segments": [
            {"segment_id": "s1", "start": 0.0, "end": 60.0, "script_ref": {}, "assets": [], "effects": []}
        ]
    }
    audio = SimpleNamespace(duration=120.0)
    slides = SimpleNamespace()
    transcript = SimpleNamespace()

    mock_video_info = VideoInfo(
        file_path=Path("test_video.mp4"),
        duration=120.0,
        resolution=(1920, 1080),
        fps=30,
        file_size=1000000,
        has_subtitles=True,
        has_effects=False,
        created_at=datetime.now(),
    )

    with patch.object(backend.video_composer, 'compose_video', new_callable=AsyncMock) as mock_compose:
        mock_compose.return_value = mock_video_info

        # asyncio.runを使ってテスト実行
        result = asyncio.run(backend.render(timeline_plan, audio, slides, transcript))

        assert result == mock_video_info
        mock_compose.assert_called_once()


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

    # 依存を最小化するため、fallback_backend は未使用だが渡しておく
    backend = YMM4EditingBackend(
        project_template=tmp_path / "template.y4mmp",
        workspace_dir=tmp_path,
        auto_hotkey_script=tmp_path / "dummy.ahk",
        fallback_backend=MoviePyEditingBackend(),
    )

    extras: dict[str, Any] = {}
    backend._record_export_outputs(project_dir, project_file, extras)

    assert "export_outputs" in extras
    ymm4_outputs = extras["export_outputs"].get("ymm4")
    assert ymm4_outputs is not None
    assert ymm4_outputs.get("template_diff").endswith("template_diff_applied.json")
