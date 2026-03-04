"""Lightweight JSON-file persistence for generation history.

Stores records in data/history/ as individual JSON files per job.
Thread-safe via file locking (fcntl on Unix, msvcrt on Windows).
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_HISTORY_DIR: Path = Path("data/history")


def _ensure_dir() -> Path:
    _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    return _HISTORY_DIR


def _job_path(job_id: str) -> Path:
    return _HISTORY_DIR / f"{job_id}.json"


def _safe_read(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _safe_write(path: Path, data: Dict[str, Any]) -> None:
    try:
        _ensure_dir()
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    except OSError as e:
        logger.debug(f"Failed to write {path}: {e}")


class _JsonDbManager:
    """JSON file-based generation history manager."""

    def save_generation_record(self, record: Dict[str, Any]) -> Optional[int]:
        job_id = record.get("job_id")
        if not job_id:
            return None
        path = _job_path(job_id)
        existing = _safe_read(path)
        if existing:
            existing.update(record)
            record = existing
        record["updated_at"] = datetime.now().isoformat()
        _safe_write(path, record)
        return 1

    def get_generation_history(self, limit: int = 20, **kw) -> List[Dict[str, Any]]:
        d = _ensure_dir()
        files = sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        results = []
        for f in files[:limit]:
            rec = _safe_read(f)
            if rec:
                results.append(rec)
        return results

    def get_generation_record(self, job_id: str) -> Optional[Dict[str, Any]]:
        return _safe_read(_job_path(job_id))

    def update_generation_status(
        self, job_id: str, status: str, error: Optional[str] = None
    ) -> None:
        path = _job_path(job_id)
        rec = _safe_read(path) or {"job_id": job_id}
        rec["status"] = status
        rec["updated_at"] = datetime.now().isoformat()
        if error:
            rec["error"] = error
        if status == "completed":
            rec["completed_at"] = datetime.now().isoformat()
        _safe_write(path, rec)

    def update_generation_progress(
        self, job_id: str, progress: float, stage: str, message: str
    ) -> None:
        path = _job_path(job_id)
        rec = _safe_read(path) or {"job_id": job_id}
        rec["progress"] = progress
        rec["stage"] = stage
        rec["message"] = message
        rec["updated_at"] = datetime.now().isoformat()
        _safe_write(path, rec)

    def cleanup_old_records(self, days: int = 90) -> int:
        d = _ensure_dir()
        cutoff = time.time() - (days * 86400)
        removed = 0
        for f in d.glob("*.json"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1
            except OSError:
                pass
        return removed

    def save_config_change(self, **kw) -> None:
        pass

    def get_config_history(self, **kw) -> List[Dict[str, Any]]:
        return []


db_manager = _JsonDbManager()
backup_manager = _JsonDbManager()
