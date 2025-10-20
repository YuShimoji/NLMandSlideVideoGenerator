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
