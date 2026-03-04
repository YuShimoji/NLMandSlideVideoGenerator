"""Batch processing data models"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class CSVJobConfig:
    """Configuration for a single CSV-based video generation job"""

    csv_path: Path
    audio_dir: Path
    topic: Optional[str] = None
    video_quality: str = "1080p"
    priority: int = 0
    max_chars_per_slide: Optional[int] = None
    upload: bool = False
    public_upload: bool = False
    export_ymm4: bool = False
    package_path: Optional[Path] = None
    strict_alignment: bool = False
    max_retries: int = 3
    timeout_minutes: int = 60
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize paths"""
        self.csv_path = Path(self.csv_path).expanduser().resolve()
        self.audio_dir = Path(self.audio_dir).expanduser().resolve()

        if self.package_path is not None:
            self.package_path = Path(self.package_path).expanduser().resolve()

        # Validate video quality
        valid_qualities = ["1080p", "720p", "480p"]
        if self.video_quality not in valid_qualities:
            raise ValueError(
                f"Invalid video_quality: {self.video_quality}. "
                f"Must be one of {valid_qualities}"
            )

        # Validate priority
        if not -100 <= self.priority <= 100:
            raise ValueError(
                f"Priority must be between -100 and 100, got {self.priority}"
            )

        # Validate timeout
        if self.timeout_minutes <= 0:
            raise ValueError(
                f"timeout_minutes must be positive, got {self.timeout_minutes}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "csv_path": str(self.csv_path),
            "audio_dir": str(self.audio_dir),
            "topic": self.topic,
            "video_quality": self.video_quality,
            "priority": self.priority,
            "max_chars_per_slide": self.max_chars_per_slide,
            "upload": self.upload,
            "public_upload": self.public_upload,
            "export_ymm4": self.export_ymm4,
            "package_path": str(self.package_path) if self.package_path else None,
            "strict_alignment": self.strict_alignment,
            "max_retries": self.max_retries,
            "timeout_minutes": self.timeout_minutes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CSVJobConfig:
        """Create from dictionary"""
        # Convert string paths back to Path objects
        data = data.copy()
        data["csv_path"] = Path(data["csv_path"])
        data["audio_dir"] = Path(data["audio_dir"])
        if data.get("package_path"):
            data["package_path"] = Path(data["package_path"])

        return cls(**data)


@dataclass
class JobResult:
    """Result of a job execution"""

    job_id: str
    status: JobStatus
    config: CSVJobConfig
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_path: Optional[Path] = None
    youtube_url: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate progress"""
        if not 0.0 <= self.progress <= 100.0:
            raise ValueError(
                f"progress must be between 0.0 and 100.0, got {self.progress}"
            )

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds"""
        if self.started_at is None:
            return None

        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

    @property
    def is_terminal(self) -> bool:
        """Check if job is in terminal state (completed, failed, or cancelled)"""
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        )

    @property
    def is_running(self) -> bool:
        """Check if job is currently running"""
        return self.status in (JobStatus.RUNNING, JobStatus.RETRYING)

    @property
    def success(self) -> bool:
        """Check if job completed successfully"""
        return self.status == JobStatus.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "config": self.config.to_dict(),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "output_path": str(self.output_path) if self.output_path else None,
            "youtube_url": self.youtube_url,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "progress": self.progress,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> JobResult:
        """Create from dictionary"""
        data = data.copy()

        # Convert status string to enum
        data["status"] = JobStatus(data["status"])

        # Convert config dict to CSVJobConfig
        data["config"] = CSVJobConfig.from_dict(data["config"])

        # Convert ISO format strings to datetime
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])

        # Convert output_path string to Path
        if data.get("output_path"):
            data["output_path"] = Path(data["output_path"])

        # Remove computed property from dict
        data.pop("duration_seconds", None)

        return cls(**data)


@dataclass
class BatchSummary:
    """Summary statistics for a batch of jobs"""

    total_jobs: int = 0
    completed: int = 0
    failed: int = 0
    running: int = 0
    pending: int = 0
    retrying: int = 0
    cancelled: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        finished = self.completed + self.failed + self.cancelled
        if finished == 0:
            return 0.0
        return (self.completed / finished) * 100.0

    @property
    def is_complete(self) -> bool:
        """Check if all jobs are in terminal state"""
        return self.running == 0 and self.pending == 0 and self.retrying == 0

    @property
    def progress_percentage(self) -> float:
        """Calculate overall progress percentage"""
        if self.total_jobs == 0:
            return 0.0

        # Terminal states count as 100% progress
        terminal_count = self.completed + self.failed + self.cancelled
        return (terminal_count / self.total_jobs) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_jobs": self.total_jobs,
            "completed": self.completed,
            "failed": self.failed,
            "running": self.running,
            "pending": self.pending,
            "retrying": self.retrying,
            "cancelled": self.cancelled,
            "success_rate": self.success_rate,
            "is_complete": self.is_complete,
            "progress_percentage": self.progress_percentage,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BatchSummary:
        """Create from dictionary"""
        # Filter out computed properties
        data = {
            k: v for k, v in data.items()
            if k not in ("success_rate", "is_complete", "progress_percentage")
        }
        return cls(**data)

    def __str__(self) -> str:
        """Human-readable summary"""
        return (
            f"BatchSummary(total={self.total_jobs}, "
            f"completed={self.completed}, failed={self.failed}, "
            f"running={self.running}, pending={self.pending}, "
            f"success_rate={self.success_rate:.1f}%)"
        )
