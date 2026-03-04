"""Unit tests for batch processing models"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# プロジェクトルートを sys.path に追加
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from batch.models import (
    JobStatus,
    CSVJobConfig,
    JobResult,
    BatchSummary,
)


class TestJobStatus:
    """Test JobStatus enum"""

    def test_all_statuses_defined(self):
        """Verify all expected statuses are defined"""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.RETRYING == "retrying"
        assert JobStatus.CANCELLED == "cancelled"

    def test_status_is_string(self):
        """Verify JobStatus inherits from str"""
        assert isinstance(JobStatus.PENDING, str)
        assert JobStatus.PENDING.value == "pending"


class TestCSVJobConfig:
    """Test CSVJobConfig dataclass"""

    def test_minimal_config(self, tmp_path):
        """Test creation with minimal required fields"""
        csv_path = tmp_path / "test.csv"
        csv_path.touch()
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        config = CSVJobConfig(
            csv_path=csv_path,
            audio_dir=audio_dir,
        )

        assert config.csv_path == csv_path
        assert config.audio_dir == audio_dir
        assert config.topic is None
        assert config.video_quality == "1080p"
        assert config.priority == 0
        assert config.max_retries == 3
        assert config.timeout_minutes == 60

    def test_full_config(self, tmp_path):
        """Test creation with all fields"""
        csv_path = tmp_path / "test.csv"
        csv_path.touch()
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        package_path = tmp_path / "package.json"
        package_path.touch()

        config = CSVJobConfig(
            csv_path=csv_path,
            audio_dir=audio_dir,
            topic="Test Topic",
            video_quality="720p",
            priority=10,
            max_chars_per_slide=100,
            upload=True,
            public_upload=True,
            export_ymm4=True,
            package_path=package_path,
            strict_alignment=True,
            max_retries=5,
            timeout_minutes=120,
            metadata={"key": "value"},
        )

        assert config.topic == "Test Topic"
        assert config.video_quality == "720p"
        assert config.priority == 10
        assert config.max_chars_per_slide == 100
        assert config.upload is True
        assert config.public_upload is True
        assert config.export_ymm4 is True
        assert config.package_path == package_path
        assert config.strict_alignment is True
        assert config.max_retries == 5
        assert config.timeout_minutes == 120
        assert config.metadata == {"key": "value"}

    def test_path_normalization(self, tmp_path):
        """Test that paths are normalized and resolved"""
        csv_path = tmp_path / "test.csv"
        csv_path.touch()
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        config = CSVJobConfig(
            csv_path=str(csv_path),
            audio_dir=str(audio_dir),
        )

        assert isinstance(config.csv_path, Path)
        assert isinstance(config.audio_dir, Path)
        assert config.csv_path.is_absolute()
        assert config.audio_dir.is_absolute()

    def test_invalid_video_quality(self, tmp_path):
        """Test validation of video_quality"""
        csv_path = tmp_path / "test.csv"
        csv_path.touch()
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        with pytest.raises(ValueError, match="Invalid video_quality"):
            CSVJobConfig(
                csv_path=csv_path,
                audio_dir=audio_dir,
                video_quality="4K",
            )

    def test_invalid_priority(self, tmp_path):
        """Test validation of priority range"""
        csv_path = tmp_path / "test.csv"
        csv_path.touch()
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        with pytest.raises(ValueError, match="Priority must be between"):
            CSVJobConfig(
                csv_path=csv_path,
                audio_dir=audio_dir,
                priority=101,
            )

        with pytest.raises(ValueError, match="Priority must be between"):
            CSVJobConfig(
                csv_path=csv_path,
                audio_dir=audio_dir,
                priority=-101,
            )

    def test_invalid_timeout(self, tmp_path):
        """Test validation of timeout_minutes"""
        csv_path = tmp_path / "test.csv"
        csv_path.touch()
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        with pytest.raises(ValueError, match="timeout_minutes must be positive"):
            CSVJobConfig(
                csv_path=csv_path,
                audio_dir=audio_dir,
                timeout_minutes=0,
            )

    def test_to_dict(self, tmp_path):
        """Test serialization to dict"""
        csv_path = tmp_path / "test.csv"
        csv_path.touch()
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        config = CSVJobConfig(
            csv_path=csv_path,
            audio_dir=audio_dir,
            topic="Test",
            priority=5,
        )

        data = config.to_dict()

        assert isinstance(data, dict)
        assert data["csv_path"] == str(csv_path)
        assert data["audio_dir"] == str(audio_dir)
        assert data["topic"] == "Test"
        assert data["priority"] == 5
        assert data["video_quality"] == "1080p"

    def test_from_dict(self, tmp_path):
        """Test deserialization from dict"""
        csv_path = tmp_path / "test.csv"
        csv_path.touch()
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        data = {
            "csv_path": str(csv_path),
            "audio_dir": str(audio_dir),
            "topic": "Test",
            "video_quality": "720p",
            "priority": 5,
            "max_chars_per_slide": 100,
            "upload": True,
            "public_upload": False,
            "export_ymm4": False,
            "package_path": None,
            "strict_alignment": False,
            "max_retries": 3,
            "timeout_minutes": 60,
            "metadata": {},
        }

        config = CSVJobConfig.from_dict(data)

        assert config.csv_path == csv_path
        assert config.audio_dir == audio_dir
        assert config.topic == "Test"
        assert config.video_quality == "720p"
        assert config.priority == 5

    def test_roundtrip_serialization(self, tmp_path):
        """Test that to_dict -> from_dict preserves data"""
        csv_path = tmp_path / "test.csv"
        csv_path.touch()
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        original = CSVJobConfig(
            csv_path=csv_path,
            audio_dir=audio_dir,
            topic="Test",
            priority=10,
            metadata={"key": "value"},
        )

        data = original.to_dict()
        restored = CSVJobConfig.from_dict(data)

        assert restored.csv_path == original.csv_path
        assert restored.audio_dir == original.audio_dir
        assert restored.topic == original.topic
        assert restored.priority == original.priority
        assert restored.metadata == original.metadata


class TestJobResult:
    """Test JobResult dataclass"""

    def test_minimal_result(self, tmp_path):
        """Test creation with minimal required fields"""
        config = CSVJobConfig(
            csv_path=tmp_path / "test.csv",
            audio_dir=tmp_path / "audio",
        )

        result = JobResult(
            job_id="job-001",
            status=JobStatus.PENDING,
            config=config,
            created_at=datetime.now(),
        )

        assert result.job_id == "job-001"
        assert result.status == JobStatus.PENDING
        assert result.config == config
        assert result.started_at is None
        assert result.completed_at is None
        assert result.retry_count == 0
        assert result.progress == 0.0

    def test_invalid_progress(self, tmp_path):
        """Test validation of progress range"""
        config = CSVJobConfig(
            csv_path=tmp_path / "test.csv",
            audio_dir=tmp_path / "audio",
        )

        with pytest.raises(ValueError, match="progress must be between"):
            JobResult(
                job_id="job-001",
                status=JobStatus.RUNNING,
                config=config,
                created_at=datetime.now(),
                progress=150.0,
            )

    def test_duration_calculation(self, tmp_path):
        """Test duration_seconds property"""
        config = CSVJobConfig(
            csv_path=tmp_path / "test.csv",
            audio_dir=tmp_path / "audio",
        )

        # No start time
        result = JobResult(
            job_id="job-001",
            status=JobStatus.PENDING,
            config=config,
            created_at=datetime.now(),
        )
        assert result.duration_seconds is None

        # With start time, no end time (ongoing)
        start_time = datetime.now() - timedelta(seconds=10)
        result = JobResult(
            job_id="job-001",
            status=JobStatus.RUNNING,
            config=config,
            created_at=start_time,
            started_at=start_time,
        )
        duration = result.duration_seconds
        assert duration is not None
        assert duration >= 10.0

        # With start and end time
        start_time = datetime.now() - timedelta(seconds=30)
        end_time = start_time + timedelta(seconds=20)
        result = JobResult(
            job_id="job-001",
            status=JobStatus.COMPLETED,
            config=config,
            created_at=start_time,
            started_at=start_time,
            completed_at=end_time,
        )
        assert result.duration_seconds == pytest.approx(20.0, abs=0.1)

    def test_is_terminal(self, tmp_path):
        """Test is_terminal property"""
        config = CSVJobConfig(
            csv_path=tmp_path / "test.csv",
            audio_dir=tmp_path / "audio",
        )

        # Terminal states
        for status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            result = JobResult(
                job_id="job-001",
                status=status,
                config=config,
                created_at=datetime.now(),
            )
            assert result.is_terminal is True

        # Non-terminal states
        for status in [JobStatus.PENDING, JobStatus.RUNNING, JobStatus.RETRYING]:
            result = JobResult(
                job_id="job-001",
                status=status,
                config=config,
                created_at=datetime.now(),
            )
            assert result.is_terminal is False

    def test_is_running(self, tmp_path):
        """Test is_running property"""
        config = CSVJobConfig(
            csv_path=tmp_path / "test.csv",
            audio_dir=tmp_path / "audio",
        )

        # Running states
        for status in [JobStatus.RUNNING, JobStatus.RETRYING]:
            result = JobResult(
                job_id="job-001",
                status=status,
                config=config,
                created_at=datetime.now(),
            )
            assert result.is_running is True

        # Non-running states
        for status in [JobStatus.PENDING, JobStatus.COMPLETED, JobStatus.FAILED]:
            result = JobResult(
                job_id="job-001",
                status=status,
                config=config,
                created_at=datetime.now(),
            )
            assert result.is_running is False

    def test_success(self, tmp_path):
        """Test success property"""
        config = CSVJobConfig(
            csv_path=tmp_path / "test.csv",
            audio_dir=tmp_path / "audio",
        )

        # Success
        result = JobResult(
            job_id="job-001",
            status=JobStatus.COMPLETED,
            config=config,
            created_at=datetime.now(),
        )
        assert result.success is True

        # Not success
        for status in [JobStatus.PENDING, JobStatus.RUNNING, JobStatus.FAILED]:
            result = JobResult(
                job_id="job-001",
                status=status,
                config=config,
                created_at=datetime.now(),
            )
            assert result.success is False

    def test_to_dict(self, tmp_path):
        """Test serialization to dict"""
        config = CSVJobConfig(
            csv_path=tmp_path / "test.csv",
            audio_dir=tmp_path / "audio",
        )

        created_at = datetime.now()
        started_at = created_at + timedelta(seconds=5)

        result = JobResult(
            job_id="job-001",
            status=JobStatus.RUNNING,
            config=config,
            created_at=created_at,
            started_at=started_at,
            progress=50.0,
        )

        data = result.to_dict()

        assert isinstance(data, dict)
        assert data["job_id"] == "job-001"
        assert data["status"] == "running"
        assert "config" in data
        assert data["created_at"] == created_at.isoformat()
        assert data["started_at"] == started_at.isoformat()
        assert data["progress"] == 50.0
        assert "duration_seconds" in data

    def test_from_dict(self, tmp_path):
        """Test deserialization from dict"""
        csv_path = tmp_path / "test.csv"
        audio_dir = tmp_path / "audio"

        created_at = datetime.now()

        data = {
            "job_id": "job-001",
            "status": "completed",
            "config": {
                "csv_path": str(csv_path),
                "audio_dir": str(audio_dir),
                "topic": None,
                "video_quality": "1080p",
                "priority": 0,
                "max_chars_per_slide": None,
                "upload": False,
                "public_upload": False,
                "export_ymm4": False,
                "package_path": None,
                "strict_alignment": False,
                "max_retries": 3,
                "timeout_minutes": 60,
                "metadata": {},
            },
            "created_at": created_at.isoformat(),
            "started_at": None,
            "completed_at": None,
            "output_path": None,
            "youtube_url": None,
            "error_message": None,
            "retry_count": 0,
            "progress": 100.0,
            "metadata": {},
        }

        result = JobResult.from_dict(data)

        assert result.job_id == "job-001"
        assert result.status == JobStatus.COMPLETED
        assert result.created_at == created_at
        assert result.progress == 100.0


class TestBatchSummary:
    """Test BatchSummary dataclass"""

    def test_empty_summary(self):
        """Test empty batch summary"""
        summary = BatchSummary()

        assert summary.total_jobs == 0
        assert summary.completed == 0
        assert summary.failed == 0
        assert summary.success_rate == 0.0
        assert summary.is_complete is True
        assert summary.progress_percentage == 0.0

    def test_success_rate_calculation(self):
        """Test success_rate property"""
        # 100% success
        summary = BatchSummary(total_jobs=10, completed=10)
        assert summary.success_rate == 100.0

        # 50% success
        summary = BatchSummary(total_jobs=10, completed=5, failed=5)
        assert summary.success_rate == 50.0

        # With cancelled jobs
        summary = BatchSummary(total_jobs=10, completed=6, failed=2, cancelled=2)
        assert summary.success_rate == 60.0

        # No finished jobs
        summary = BatchSummary(total_jobs=10, running=5, pending=5)
        assert summary.success_rate == 0.0

    def test_is_complete(self):
        """Test is_complete property"""
        # All completed
        summary = BatchSummary(total_jobs=5, completed=5)
        assert summary.is_complete is True

        # Mix of terminal states
        summary = BatchSummary(total_jobs=5, completed=3, failed=2)
        assert summary.is_complete is True

        # Has running jobs
        summary = BatchSummary(total_jobs=5, completed=3, running=2)
        assert summary.is_complete is False

        # Has pending jobs
        summary = BatchSummary(total_jobs=5, completed=3, pending=2)
        assert summary.is_complete is False

        # Has retrying jobs
        summary = BatchSummary(total_jobs=5, completed=3, retrying=2)
        assert summary.is_complete is False

    def test_progress_percentage(self):
        """Test progress_percentage property"""
        # No jobs
        summary = BatchSummary()
        assert summary.progress_percentage == 0.0

        # All completed
        summary = BatchSummary(total_jobs=10, completed=10)
        assert summary.progress_percentage == 100.0

        # 50% done
        summary = BatchSummary(total_jobs=10, completed=5, pending=5)
        assert summary.progress_percentage == 50.0

        # Mix of terminal states
        summary = BatchSummary(total_jobs=10, completed=3, failed=2, running=5)
        assert summary.progress_percentage == 50.0

    def test_to_dict(self):
        """Test serialization to dict"""
        summary = BatchSummary(
            total_jobs=10,
            completed=6,
            failed=2,
            running=1,
            pending=1,
        )

        data = summary.to_dict()

        assert isinstance(data, dict)
        assert data["total_jobs"] == 10
        assert data["completed"] == 6
        assert data["failed"] == 2
        assert data["running"] == 1
        assert data["pending"] == 1
        assert "success_rate" in data
        assert "is_complete" in data
        assert "progress_percentage" in data

    def test_from_dict(self):
        """Test deserialization from dict"""
        data = {
            "total_jobs": 10,
            "completed": 5,
            "failed": 3,
            "running": 1,
            "pending": 1,
            "retrying": 0,
            "cancelled": 0,
            # These computed properties should be ignored
            "success_rate": 62.5,
            "is_complete": False,
            "progress_percentage": 80.0,
        }

        summary = BatchSummary.from_dict(data)

        assert summary.total_jobs == 10
        assert summary.completed == 5
        assert summary.failed == 3
        # Verify computed properties are recalculated
        assert summary.success_rate == 62.5
        assert summary.is_complete is False

    def test_str_representation(self):
        """Test __str__ method"""
        summary = BatchSummary(
            total_jobs=10,
            completed=6,
            failed=2,
            running=1,
            pending=1,
        )

        str_repr = str(summary)

        assert "BatchSummary" in str_repr
        assert "total=10" in str_repr
        assert "completed=6" in str_repr
        assert "failed=2" in str_repr
        assert "%" in str_repr
