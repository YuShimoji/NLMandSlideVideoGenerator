"""パイプライン状態管理 — ステップ再開機能。

各ステップの完了/失敗状態を pipeline_state.json に永続化し、
途中失敗時に完了済みステップをスキップして再開できるようにする。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.utils.logger import logger


# パイプラインステップ名 (実行順)
STEP_NAMES = ["collect", "script", "align", "review", "orchestrate", "assemble"]


@dataclass
class StepInfo:
    """個別ステップの状態。"""
    status: str = "pending"  # pending | running | done | failed | skipped
    output: Optional[str] = None  # 出力ファイルの相対パス
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    duration_sec: Optional[float] = None


@dataclass
class PipelineState:
    """パイプライン全体の状態。work_dir/pipeline_state.json に永続化。"""
    topic: str = ""
    urls: List[str] = field(default_factory=list)
    created_at: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    steps: Dict[str, StepInfo] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in STEP_NAMES:
            if name not in self.steps:
                self.steps[name] = StepInfo()

    @classmethod
    def load(cls, work_dir: Path) -> PipelineState:
        """work_dir から状態を読み込む。ファイルがなければ新規作成。"""
        state_path = work_dir / "pipeline_state.json"
        if state_path.exists():
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            steps = {}
            for name, info in data.get("steps", {}).items():
                steps[name] = StepInfo(**info)
            state = cls(
                topic=data.get("topic", ""),
                urls=data.get("urls", []),
                created_at=data.get("created_at", ""),
                params=data.get("params", {}),
                steps=steps,
            )
            logger.info(f"パイプライン状態読み込み: {state_path}")
            return state
        return cls()

    def save(self, work_dir: Path) -> None:
        """work_dir に状態を保存。"""
        state_path = work_dir / "pipeline_state.json"
        data = {
            "topic": self.topic,
            "urls": self.urls,
            "created_at": self.created_at,
            "params": self.params,
            "steps": {
                name: {
                    "status": info.status,
                    "output": info.output,
                    "started_at": info.started_at,
                    "finished_at": info.finished_at,
                    "error": info.error,
                    "duration_sec": info.duration_sec,
                }
                for name, info in self.steps.items()
            },
        }
        work_dir.mkdir(parents=True, exist_ok=True)
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def is_step_done(self, step_name: str) -> bool:
        """ステップが完了済みかつ出力ファイルが存在するか。"""
        info = self.steps.get(step_name)
        return info is not None and info.status == "done"

    def mark_running(self, step_name: str) -> None:
        """ステップ開始をマーク。"""
        info = self.steps.setdefault(step_name, StepInfo())
        info.status = "running"
        info.started_at = _now_iso()
        info.error = None

    def mark_done(self, step_name: str, output: Optional[str] = None) -> None:
        """ステップ完了をマーク。"""
        info = self.steps.setdefault(step_name, StepInfo())
        info.status = "done"
        info.output = output
        info.finished_at = _now_iso()
        if info.started_at:
            try:
                start = _parse_time(info.started_at)
                end = _parse_time(info.finished_at)
                info.duration_sec = round(end - start, 1)
            except Exception:
                pass

    def mark_failed(self, step_name: str, error: str) -> None:
        """ステップ失敗をマーク。"""
        info = self.steps.setdefault(step_name, StepInfo())
        info.status = "failed"
        info.error = error
        info.finished_at = _now_iso()

    def summary(self) -> str:
        """状態サマリを文字列で返す。"""
        lines = []
        for name in STEP_NAMES:
            info = self.steps.get(name, StepInfo())
            icon = {"done": "OK", "failed": "NG", "running": "..", "skipped": "--"}.get(
                info.status, "  "
            )
            dur = f" ({info.duration_sec:.1f}s)" if info.duration_sec else ""
            err = f" [{info.error[:40]}]" if info.error else ""
            lines.append(f"  [{icon}] {name:12s}{dur}{err}")
        return "\n".join(lines)

    def first_incomplete_step(self) -> Optional[str]:
        """最初の未完了ステップ名を返す。全完了ならNone。"""
        for name in STEP_NAMES:
            info = self.steps.get(name, StepInfo())
            if info.status not in ("done", "skipped"):
                return name
        return None

    def output_exists(self, step_name: str, work_dir: Path) -> bool:
        """ステップの出力ファイルが実際に存在するか確認。"""
        info = self.steps.get(step_name)
        if not info or not info.output:
            return False
        output_path = work_dir / info.output
        return output_path.exists()


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now().isoformat()


def _parse_time(iso_str: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(iso_str).timestamp()
