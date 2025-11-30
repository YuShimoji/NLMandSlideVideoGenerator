import asyncio
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from config.settings import settings
from ..interfaces import IEditingBackend
from ..utils.logger import logger
from .moviepy_backend import MoviePyEditingBackend
from notebook_lm.audio_generator import AudioInfo
from notebook_lm.transcript_processor import TranscriptInfo
from slides.slide_generator import SlidesPackage
from video_editor.video_composer import VideoInfo


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
        extras: Optional[Dict[str, Any]] = None,
    ) -> VideoInfo:
        project_dir = self._prepare_workspace()
        project_file = self._prepare_project_file(project_dir)
        self._export_plan(project_dir, timeline_plan, audio, transcript)
        self._export_slides_payload(project_dir, extras)
        self._copy_csv_source(project_dir, extras)
        self._copy_audio_assets(project_dir, extras)
        self._record_export_outputs(project_dir, project_file, extras)
        self._record_execution_hint(project_dir)

        # YMM4 AutoHotkeyスクリプト実行（オプション）
        await self._run_autohotkey_script(project_dir, project_file)

        # YMM4書き出しが未整備のため、MoviePy にフォールバックして動画を生成
        video_info = await self.fallback_backend.render(
            timeline_plan=timeline_plan,
            audio=audio,
            slides=slides,
            transcript=transcript,
            quality=quality,
            extras=extras,
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
                
                # テンプレート差分適用プロトタイプ
                self._apply_template_diff(project_dir, project_path)
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
                        "speaker": getattr(seg, "speaker", ""),
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

    def _export_slides_payload(self, project_dir: Path, extras: Optional[Dict[str, Any]]) -> None:
        if not extras:
            return
        payload = extras.get("slides_payload")
        if not payload:
            logger.info("slides_payload が提供されていないため書き出しをスキップします")
            return

        slides_path = project_dir / "slides_payload.json"
        slides_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"slides_payload.json を出力しました: {slides_path}")

    def _copy_csv_source(self, project_dir: Path, extras: Optional[Dict[str, Any]]) -> None:
        if not extras:
            return
        csv_path = extras.get("csv_path")
        if not csv_path:
            return

        source = Path(csv_path)
        if not source.exists():
            logger.warning(f"CSVファイルが見つからないためコピーをスキップします: {source}")
            return

        text_dir = project_dir / "text"
        text_dir.mkdir(parents=True, exist_ok=True)
        destination = text_dir / source.name
        shutil.copy2(source, destination)
        logger.info(f"CSVをコピーしました: {destination}")

    def _copy_audio_assets(self, project_dir: Path, extras: Optional[Dict[str, Any]]) -> None:
        if not extras:
            return

        audio_dir = project_dir / "audio"
        segments_dir = audio_dir / "segments"
        segments_dir.mkdir(parents=True, exist_ok=True)

        audio_files: Sequence[str] = extras.get("audio_files") or []
        for idx, audio_path in enumerate(audio_files, start=1):
            source = Path(audio_path)
            if not source.exists():
                logger.warning(f"セグメント音声が見つかりません: {source}")
                continue

            ext = source.suffix or ".wav"
            destination = segments_dir / f"{idx:03d}{ext.lower()}"
            shutil.copy2(source, destination)

        combined_audio = extras.get("combined_audio_path")
        if combined_audio:
            combined_source = Path(combined_audio)
            if combined_source.exists():
                audio_dir.mkdir(parents=True, exist_ok=True)
                destination = audio_dir / combined_source.name
                shutil.copy2(combined_source, destination)
            else:
                logger.warning(f"結合音声が見つからないためコピーをスキップします: {combined_source}")

    def _record_export_outputs(
        self,
        project_dir: Path,
        project_file: Path,
        extras: Optional[Dict[str, Any]],
    ) -> None:
        if extras is None:
            return
        export_outputs = extras.setdefault("export_outputs", {})
        payload = {
            "project_dir": str(project_dir),
            "project_file": str(project_file),
        }

        timeline_path = project_dir / "timeline_plan.json"
        if timeline_path.exists():
            payload["timeline_plan"] = str(timeline_path)

        slides_payload_path = project_dir / "slides_payload.json"
        if slides_payload_path.exists():
            payload["slides_payload"] = str(slides_payload_path)

        audio_dir = project_dir / "audio"
        if audio_dir.exists():
            payload["audio_dir"] = str(audio_dir)

        export_outputs["ymm4"] = payload

    async def _run_autohotkey_script(self, project_dir: Path, project_file: Path) -> None:
        """AutoHotkeyスクリプトを実行してYMM4を操作（オプション）

        1. slides_payload.jsonとtimeline_plan.jsonからカスタムAHKスクリプトを生成
        2. 生成したスクリプトを実行
        """
        if not self.auto_hotkey_script.exists():
            logger.warning(f"AutoHotkeyスクリプトが見つかりません: {self.auto_hotkey_script}")
            return

        try:
            # カスタムAHKスクリプトの生成
            custom_script_path = await self._generate_custom_ahk_script(project_dir, project_file)
            if custom_script_path:
                logger.info(f"カスタムAHKスクリプトを使用: {custom_script_path}")
                script_to_run = custom_script_path
            else:
                logger.info("カスタムスクリプト生成失敗、テンプレートを使用")
                script_to_run = self.auto_hotkey_script

            # AutoHotkeyスクリプト実行
            await self._execute_ahk_script(script_to_run, project_file)

        except Exception as e:
            logger.warning(f"AutoHotkeyスクリプト実行エラー: {e}")

    async def _generate_custom_ahk_script(self, project_dir: Path, project_file: Path) -> Optional[Path]:
        """slides_payloadとtimeline_planからカスタムAHKスクリプトを生成"""
        try:
            # JSONファイルの読み込み
            slides_payload_path = project_dir / "slides_payload.json"
            timeline_plan_path = project_dir / "timeline_plan.json"

            if not slides_payload_path.exists() or not timeline_plan_path.exists():
                logger.warning("必要なJSONファイルが見つからないため、カスタムスクリプト生成をスキップ")
                return None

            with open(slides_payload_path, 'r', encoding='utf-8') as f:
                slides_payload = json.load(f)

            with open(timeline_plan_path, 'r', encoding='utf-8') as f:
                timeline_plan = json.load(f)

            # PythonスクリプトでAHKスクリプトを生成
            # __file__ = src/core/editing/ymm4_backend.py なので 4つ上がるとリポジトリルート
            project_root = Path(__file__).resolve().parents[3]
            generate_script = project_root / "scripts" / "generate_ymm4_ahk.py"
            if not generate_script.exists():
                logger.warning(f"AHK生成スクリプトが見つかりません: {generate_script}")
                return None

            # Pythonスクリプト実行
            import subprocess
            result = subprocess.run([
                sys.executable, str(generate_script), str(project_dir)
            ], capture_output=True, text=True, cwd=project_dir)

            if result.returncode == 0:
                custom_script = project_dir / "ymm4_automation.ahk"
                if custom_script.exists():
                    logger.info(f"カスタムAHKスクリプト生成成功: {custom_script}")
                    return custom_script
                else:
                    logger.warning("カスタムスクリプトが生成されませんでした")
            else:
                logger.warning(f"AHKスクリプト生成失敗: {result.stderr}")

        except Exception as e:
            logger.warning(f"カスタムAHKスクリプト生成エラー: {e}")

        return None

    async def _execute_ahk_script(self, script_path: Path, project_file: Path) -> None:
        """AutoHotkeyスクリプトを実行"""
        # AutoHotkey実行ファイルのパスを決定
        ahk_exe_paths = [
            Path("C:/Program Files/AutoHotkey/AutoHotkey.exe"),
            Path("C:/Program Files/AutoHotkey/v2/AutoHotkey.exe"),
        ]

        ahk_exe = None
        for path in ahk_exe_paths:
            if path.exists():
                ahk_exe = path
                break

        if not ahk_exe:
            logger.warning("AutoHotkey実行ファイルが見つかりません。手動実行してください。")
            return

        try:
            # AutoHotkeyスクリプト実行
            cmd = [str(ahk_exe), str(script_path), "--project", str(project_file)]

            logger.info(f"AutoHotkeyスクリプト実行: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(script_path.parent)
            )

            # タイムアウト付きで待機（例: 5分）
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300.0)
                if process.returncode == 0:
                    logger.info("AutoHotkeyスクリプト実行成功")
                    if stdout:
                        logger.debug(f"AHK stdout: {stdout.decode()}")
                else:
                    logger.warning(f"AutoHotkeyスクリプト実行失敗 (exit code: {process.returncode})")
                    if stderr:
                        logger.warning(f"AHK stderr: {stderr.decode()}")
            except asyncio.TimeoutError:
                logger.warning("AutoHotkeyスクリプト実行タイムアウト")
                process.terminate()
                await process.wait()

        except FileNotFoundError:
            logger.warning("AutoHotkey実行ファイルが見つかりません。手動実行してください。")
        except Exception as e:
            logger.warning(f"AutoHotkeyスクリプト実行エラー: {e}")

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

    def _apply_template_diff(self, project_dir: Path, project_path: Path) -> None:
        """
        テンプレート差分適用プロトタイプ
        
        Args:
            project_dir: プロジェクトディレクトリ
            project_path: プロジェクトファイルパス
        """
        try:
            # テンプレートの JSON メタデータを探す
            template_json = self.project_template.with_suffix('.json')
            if not template_json.exists():
                logger.info("テンプレート JSON メタデータが見つからないため、差分適用をスキップ")
                return
            
            # テンプレートメタデータを読み込み
            with open(template_json, 'r', encoding='utf-8') as f:
                template_meta = json.load(f)
            
            # 差分適用設定を取得（例: 環境変数や設定ファイルから）
            diff_config = self._load_diff_config()
            
            if diff_config:
                # 差分適用ロジック（プロトタイプ）
                updated_meta = self._compute_template_diff(template_meta, diff_config)
                
                # 更新されたメタデータを保存
                updated_json = project_dir / "template_diff_applied.json"
                with open(updated_json, 'w', encoding='utf-8') as f:
                    json.dump(updated_meta, f, ensure_ascii=False, indent=2)
                
                logger.info(f"テンプレート差分適用完了: {updated_json}")
                logger.info(f"適用された差分: {diff_config}")
            else:
                logger.info("適用する差分設定が見つからないため、スキップ")
                
        except Exception as e:
            logger.warning(f"テンプレート差分適用エラー: {e}")

    def _load_diff_config(self) -> Optional[Dict[str, Any]]:
        """
        差分適用設定を読み込み
        
        Returns:
            Optional[Dict[str, Any]]: 差分設定
        """
        # プロトタイプ: 環境変数から読み込み
        diff_str = os.getenv("YMM4_TEMPLATE_DIFF", "")
        if diff_str:
            try:
                return json.loads(diff_str)
            except json.JSONDecodeError:
                logger.warning(f"無効な差分設定: {diff_str}")
        return None

    def _compute_template_diff(self, template_meta: Dict[str, Any], diff_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        テンプレート差分を計算して適用
        
        Args:
            template_meta: テンプレートメタデータ
            diff_config: 差分設定
            
        Returns:
            Dict[str, Any]: 更新されたメタデータ
        """
        # プロトタイプ: シンプルな差分適用
        updated = template_meta.copy()
        
        # 例: 字幕スタイルの更新
        if "subtitle_style" in diff_config:
            updated.setdefault("styles", {})["subtitle"] = diff_config["subtitle_style"]
            logger.info(f"字幕スタイルを更新: {diff_config['subtitle_style']}")
        
        # 例: 背景色の更新
        if "background_color" in diff_config:
            updated.setdefault("styles", {})["background"] = diff_config["background_color"]
            logger.info(f"背景色を更新: {diff_config['background_color']}")
        
        # 例: エフェクトの追加
        if "effects" in diff_config:
            updated.setdefault("effects", []).extend(diff_config["effects"])
            logger.info(f"エフェクトを追加: {diff_config['effects']}")
        
        return updated
