#!/usr/bin/env python3
"""CSVタイムラインモード (run_csv_timeline) の統合テスト(軽量)

- 実ファイルとして簡単な CSV と 無音WAV を生成
- ModularVideoPipeline.run_csv_timeline を実行
- SlideGenerator / VideoComposer はモックして重い依存を避ける
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tests.test_demo_csv_to_video import _create_silent_wav  # noqa: E402
from core.pipeline import ModularVideoPipeline  # noqa: E402


@pytest.mark.asyncio
async def test_run_csv_timeline_basic(tmp_path: Path):
    """CSV + 行ごとWAVから動画合成まで走ることを確認 (モック利用)"""

    # 1) CSV 作成
    csv_path = tmp_path / "timeline.csv"
    csv_content = "Speaker1,こんにちは\nSpeaker2,世界\n"
    csv_path.write_text(csv_content, encoding="utf-8")

    # 2) 行ごとの音声 (無音WAV)
    audio_dir = tmp_path / "audio"
    _create_silent_wav(audio_dir / "001.wav", duration_sec=1.0)
    _create_silent_wav(audio_dir / "002.wav", duration_sec=2.0)

    # 3) db_manager をスタブに差し替え
    import core.pipeline as pipeline_mod

    stub_db = SimpleNamespace(
        save_generation_record=lambda *args, **kwargs: 1,
        update_generation_status=lambda *args, **kwargs: None,
    )

    with patch.object(pipeline_mod, "db_manager", stub_db):
        # 4) SlideGenerator / VideoComposer をモック
        slide_gen = Mock()
        slide_gen.generate_slides = AsyncMock(return_value=Mock(total_slides=1))

        video_comp = Mock()
        dummy_video_path = tmp_path / "out.mp4"
        dummy_video_path.write_bytes(b"")
        dummy_video_info = Mock()
        dummy_video_info.file_path = dummy_video_path
        video_comp.compose_video = AsyncMock(return_value=dummy_video_info)

        pipeline = ModularVideoPipeline(
            slide_generator=slide_gen,
            video_composer=video_comp,
        )

        result = await pipeline.run_csv_timeline(
            csv_path=csv_path,
            audio_dir=audio_dir,
            quality="720p",
            upload=False,
        )

        assert result["success"] is True
        artifacts = result["artifacts"]
        assert artifacts.video.file_path == dummy_video_path
        assert artifacts.audio.duration > 0

        slide_gen.generate_slides.assert_awaited()
        video_comp.compose_video.assert_awaited()
