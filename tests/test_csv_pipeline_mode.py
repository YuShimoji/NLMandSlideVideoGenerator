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
from config.settings import settings  # noqa: E402
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
        slide_gen.create_slides_from_content = AsyncMock(return_value=Mock(total_slides=2))

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

        slide_gen.create_slides_from_content.assert_awaited()
        video_comp.compose_video.assert_awaited()


@pytest.mark.asyncio
async def test_run_csv_timeline_long_line_split(tmp_path: Path):
    """長文1行が複数スライドに展開され、durationが総和一致する"""

    csv_path = tmp_path / "timeline.csv"
    long_text = "あ" * 180
    csv_content = f"Speaker1,{long_text}\n"
    csv_path.write_text(csv_content, encoding="utf-8")

    audio_dir = tmp_path / "audio"
    _create_silent_wav(audio_dir / "001.wav", duration_sec=3.0)

    import core.pipeline as pipeline_mod

    stub_db = SimpleNamespace(
        save_generation_record=lambda *args, **kwargs: 1,
        update_generation_status=lambda *args, **kwargs: None,
    )

    with patch.object(pipeline_mod, "db_manager", stub_db):
        slide_gen = Mock()
        slide_gen.create_slides_from_content = AsyncMock(return_value=Mock(total_slides=3))

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

        overrides = {
            "auto_split_long_lines": True,
            "long_line_char_threshold": 40,
            "long_line_target_chars_per_subslide": 40,
            "long_line_max_subslides": 3,
            "min_subslide_duration": 0.2,
        }

        with patch.dict(settings.SLIDES_SETTINGS, overrides, clear=False):
            result = await pipeline.run_csv_timeline(
                csv_path=csv_path,
                audio_dir=audio_dir,
                quality="720p",
                upload=False,
            )

        assert result["success"] is True
        slide_gen.create_slides_from_content.assert_awaited()

        slides_content = slide_gen.create_slides_from_content.await_args.kwargs["slides_content"]
        assert len(slides_content) >= 2  # 2枚以上に分割

        total_duration = sum(item["duration"] for item in slides_content)
        assert pytest.approx(total_duration, rel=1e-2) == 3.0

        for idx, item in enumerate(slides_content):
            assert item["source_segments"] == [1]
            assert item["subslide_count"] == len(slides_content)
            assert item["subslide_index"] == idx


@pytest.mark.asyncio
async def test_run_csv_timeline_ymm4_export_payload(tmp_path: Path):
    """YMM4 バックエンドに slides_payload / export_outputs が渡り、artifacts に反映される"""

    csv_path = tmp_path / "timeline.csv"
    csv_path.write_text("Speaker1,テスト\n", encoding="utf-8")

    audio_dir = tmp_path / "audio"
    _create_silent_wav(audio_dir / "001.wav", duration_sec=1.0)

    import core.pipeline as pipeline_mod

    stub_db = SimpleNamespace(
        save_generation_record=lambda *args, **kwargs: 1,
        update_generation_status=lambda *args, **kwargs: None,
    )

    with patch.object(pipeline_mod, "db_manager", stub_db):
        slide_gen = Mock()
        slide_gen.create_slides_from_content = AsyncMock(return_value=Mock(total_slides=1))

        timeline_planner = Mock()
        timeline_planner.build_plan = AsyncMock(return_value={"segments": []})

        dummy_video_path = tmp_path / "out.mp4"
        dummy_video_path.write_bytes(b"")
        dummy_video_info = SimpleNamespace(file_path=dummy_video_path)

        async def _render_side_effect(*, extras: dict, **kwargs):
            assert extras["slides_payload"]["meta"]["source_csv"].endswith("timeline.csv")
            extras["export_outputs"]["ymm4"] = {"project_dir": "/tmp/ymm4_project"}
            return dummy_video_info

        editing_backend = Mock()
        editing_backend.render = AsyncMock(side_effect=_render_side_effect)

        pipeline = ModularVideoPipeline(
            slide_generator=slide_gen,
            timeline_planner=timeline_planner,
            editing_backend=editing_backend,
        )

        result = await pipeline.run_csv_timeline(
            csv_path=csv_path,
            audio_dir=audio_dir,
            quality="720p",
            upload=False,
        )

        assert result["success"] is True
        artifacts = result["artifacts"]
        assert artifacts.slides_payload is not None
        assert artifacts.editing_outputs["ymm4"]["project_dir"] == "/tmp/ymm4_project"
        editing_backend.render.assert_awaited()
