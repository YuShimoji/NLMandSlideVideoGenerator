"""YMM4 ベースの編集バックエンド（テンプレート + AutoHotkey フォールバック）"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import settings
from ..interfaces import IEditingBackend
from .moviepy_backend import MoviePyEditingBackend
from notebook_lm.audio_generator import AudioInfo
from notebook_lm.transcript_processor import TranscriptInfo
from slides.slide_generator import SlidesPackage
from video_editor.video_composer import VideoInfo

logger = logging.getLogger(__name__)


class YMM4EditingBackend(IEditingBackend):
    """YMM4 プロジェクトを生成しつつ MoviePy にフォールバックして動画を書き出すバックエンド"""

    def __init__(
        self,
        project_template: Optional[Path] = None,
        workspace_dir: Optional[Path] = None,
        auto_hotkey_script: Optional[Path] = None,
        fallback_backend: Optional[MoviePyEditingBackend] = None,
    ) -> None:
        settings_payload = settings.YMM4_SETTINGS
        self.project_template = Path(project_template or settings_payload["project_template"])
        self.workspace_dir = Path(workspace_dir or settings_payload["workspace_dir"])
        self.auto_hotkey_script = Path(auto_hotkey_script or settings_payload["auto_hotkey_script"])
        self.fallback_backend = fallback_backend or MoviePyEditingBackend()

    async def render(
        self,
        timeline_plan: Dict[str, Any],
        audio: AudioInfo,
        slides: SlidesPackage,
        transcript: TranscriptInfo,
        quality: str = "1080p",
    ) -> VideoInfo:
        project_dir = self._prepare_workspace()
        project_file = self._prepare_project_file(project_dir)
        self._export_plan(project_dir, timeline_plan, audio, transcript)

        self._record_execution_hint(project_dir)

        # YMM4 書き出しが未整備のため、MoviePy にフォールバックして動画を生成
        video_info = await self.fallback_backend.render(
            timeline_plan=timeline_plan,
            audio=audio,
            slides=slides,
            transcript=transcript,
            quality=quality,
        )

        self._export_video_metadata(project_dir, video_info)
        logger.info("YMM4 プロジェクト Placeholder + MoviePy フォールバックを完了")
        logger.info(f"YMM4 プロジェクト: {project_file}")
        logger.info(f"フォールバック動画: {video_info.file_path}")
        return video_info

    def _prepare_workspace(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = self.workspace_dir / f"ymm4_project_{timestamp}"
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def _prepare_project_file(self, project_dir: Path) -> Path:
        project_path = project_dir / "project.y4mmp"
        if self.project_template.exists():
            try:
                shutil.copy2(self.project_template, project_path)
                logger.info(f"YMM4 テンプレートを複製しました: {project_path}")
            except Exception as err:
                logger.warning(f"YMM4 テンプレート複製に失敗しました: {err}")
                project_path.touch()
        else:
            logger.warning(f"YMM4 テンプレートが見つかりません: {self.project_template}")
            project_path.touch()
        return project_path

    def _export_plan(
        self,
        project_dir: Path,
        timeline_plan: Dict[str, Any],
        audio: AudioInfo,
        transcript: TranscriptInfo,
    ) -> None:
        payload = {
            "timeline_plan": timeline_plan,
            "audio": {
                "file_path": str(getattr(audio, "file_path", "")),
                "duration": getattr(audio, "duration", 0.0),
                "language": getattr(audio, "language", ""),
            },
            "transcript": {
                "title": getattr(transcript, "title", ""),
                "segments": [
                    {
                        "id": getattr(seg, "id", ""),
                        "start_time": getattr(seg, "start_time", 0.0),
                        "end_time": getattr(seg, "end_time", 0.0),
                        "text": getattr(seg, "text", ""),
                    }
                    for seg in getattr(transcript, "segments", [])
                ],
            },
        }
        plan_path = project_dir / "timeline_plan.json"
        plan_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"YMM4 タイムライン情報を書き出しました: {plan_path}")

    def _record_execution_hint(self, project_dir: Path) -> None:
        hint_path = project_dir / "RUN_AHK_INSTRUCTIONS.txt"
        content = [
            "# YMM4 書き出し手順",
            f"1. YMM4 を起動して {project_dir / 'project.y4mmp'} を開く",
            "2. 必要に応じてタイムラインを調整",
            "3. AutoHotkey を利用する場合は以下コマンドを実行",
            f"   ahk {self.auto_hotkey_script} --project \"{project_dir / 'project.y4mmp'}\"",
            "4. 完了後、生成された動画ファイルを pipeline の成果物に差し替え",
        ]
        hint_path.write_text("\n".join(content), encoding="utf-8")

    def _export_video_metadata(self, project_dir: Path, video_info: VideoInfo) -> None:
        metadata_path = project_dir / "render_metadata.json"
        payload = {
            "video_file": str(video_info.file_path),
            "duration": video_info.duration,
            "resolution": video_info.resolution,
            "fps": video_info.fps,
            "file_size": video_info.file_size,
            "created_at": video_info.created_at.isoformat(),
        }
        metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
