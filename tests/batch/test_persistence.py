"""Tests for batch job persistence"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

# プロジェクトルートを sys.path に追加
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from batch.models import JobStatus, CSVJobConfig, JobResult
from core.persistence import DatabaseManager


@pytest.fixture
def db_manager(tmp_path):
    """Create a temporary database manager for testing"""
    db_path = tmp_path / "test.db"
    return DatabaseManager(db_path=db_path)


@pytest.fixture
def sample_job_result(tmp_path):
    """Create a sample JobResult for testing"""
    config = CSVJobConfig(
        csv_path=tmp_path / "test.csv",
        audio_dir=tmp_path / "audio",
        topic="Test Topic",
        priority=5,
    )

    return JobResult(
        job_id="test-job-001",
        status=JobStatus.PENDING,
        config=config,
        created_at=datetime.now(),
    )


class TestBatchJobPersistence:
    """Test batch job database operations"""

    def test_save_and_get_batch_job(self, db_manager, sample_job_result):
        """Test saving and retrieving a batch job"""
        # Save job
        db_manager.save_batch_job(sample_job_result)

        # Retrieve job
        job_data = db_manager.get_batch_job("test-job-001")

        assert job_data is not None
        assert job_data["job_id"] == "test-job-001"
        assert job_data["status"] == "pending"
        assert job_data["retry_count"] == 0
        assert job_data["progress"] == 0.0

        # Verify config was serialized correctly
        assert isinstance(job_data["config"], dict)
        assert job_data["config"]["topic"] == "Test Topic"
        assert job_data["config"]["priority"] == 5

    def test_save_batch_job_updates_existing(self, db_manager, sample_job_result):
        """Test that save_batch_job updates existing jobs"""
        # Save initial job
        db_manager.save_batch_job(sample_job_result)

        # Update job status
        sample_job_result.status = JobStatus.RUNNING
        sample_job_result.progress = 50.0
        sample_job_result.started_at = datetime.now()

        # Save again
        db_manager.save_batch_job(sample_job_result)

        # Verify update
        job_data = db_manager.get_batch_job("test-job-001")
        assert job_data["status"] == "running"
        assert job_data["progress"] == 50.0
        assert job_data["started_at"] is not None

    def test_get_batch_job_not_found(self, db_manager):
        """Test getting a non-existent job returns None"""
        job_data = db_manager.get_batch_job("nonexistent")
        assert job_data is None

    def test_get_batch_jobs_empty(self, db_manager):
        """Test getting jobs from empty database"""
        jobs = db_manager.get_batch_jobs()
        assert jobs == []

    def test_get_batch_jobs_multiple(self, db_manager, tmp_path):
        """Test getting multiple batch jobs"""
        config = CSVJobConfig(
            csv_path=tmp_path / "test.csv",
            audio_dir=tmp_path / "audio",
        )

        # Create multiple jobs with different statuses
        jobs = [
            JobResult(
                job_id=f"job-{i:03d}",
                status=JobStatus.PENDING if i % 2 == 0 else JobStatus.COMPLETED,
                config=config,
                created_at=datetime.now(),
            )
            for i in range(5)
        ]

        for job in jobs:
            db_manager.save_batch_job(job)

        # Get all jobs
        all_jobs = db_manager.get_batch_jobs()
        assert len(all_jobs) == 5

        # Get pending jobs only
        pending_jobs = db_manager.get_batch_jobs(status="pending")
        assert len(pending_jobs) == 3

        # Get completed jobs only
        completed_jobs = db_manager.get_batch_jobs(status="completed")
        assert len(completed_jobs) == 2

    def test_get_batch_jobs_pagination(self, db_manager, tmp_path):
        """Test pagination with limit and offset"""
        config = CSVJobConfig(
            csv_path=tmp_path / "test.csv",
            audio_dir=tmp_path / "audio",
        )

        # Create 10 jobs
        for i in range(10):
            job = JobResult(
                job_id=f"job-{i:03d}",
                status=JobStatus.PENDING,
                config=config,
                created_at=datetime.now(),
            )
            db_manager.save_batch_job(job)

        # Get first page
        page1 = db_manager.get_batch_jobs(limit=3, offset=0)
        assert len(page1) == 3

        # Get second page
        page2 = db_manager.get_batch_jobs(limit=3, offset=3)
        assert len(page2) == 3

        # Verify no overlap
        page1_ids = {job["job_id"] for job in page1}
        page2_ids = {job["job_id"] for job in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_update_batch_job_status(self, db_manager, sample_job_result):
        """Test updating job status"""
        db_manager.save_batch_job(sample_job_result)

        # Update to running
        started_at = datetime.now()
        db_manager.update_batch_job_status(
            "test-job-001",
            "running",
            started_at=started_at
        )

        job_data = db_manager.get_batch_job("test-job-001")
        assert job_data["status"] == "running"
        assert job_data["started_at"] is not None

        # Update to completed
        completed_at = datetime.now()
        db_manager.update_batch_job_status(
            "test-job-001",
            "completed",
            completed_at=completed_at
        )

        job_data = db_manager.get_batch_job("test-job-001")
        assert job_data["status"] == "completed"
        assert job_data["completed_at"] is not None

        # Update to failed with error message
        db_manager.update_batch_job_status(
            "test-job-001",
            "failed",
            error_message="Test error"
        )

        job_data = db_manager.get_batch_job("test-job-001")
        assert job_data["status"] == "failed"
        assert job_data["error_message"] == "Test error"

    def test_update_batch_job_progress(self, db_manager, sample_job_result):
        """Test updating job progress"""
        db_manager.save_batch_job(sample_job_result)

        # Update progress only
        db_manager.update_batch_job_progress("test-job-001", 25.0)

        job_data = db_manager.get_batch_job("test-job-001")
        assert job_data["progress"] == 25.0

        # Update progress with metadata
        metadata = {"current_stage": "audio", "slides_done": 5}
        db_manager.update_batch_job_progress("test-job-001", 50.0, metadata)

        job_data = db_manager.get_batch_job("test-job-001")
        assert job_data["progress"] == 50.0
        assert job_data["metadata"]["current_stage"] == "audio"
        assert job_data["metadata"]["slides_done"] == 5

    def test_increment_batch_job_retry(self, db_manager, sample_job_result):
        """Test incrementing retry count"""
        db_manager.save_batch_job(sample_job_result)

        # First retry
        retry_count = db_manager.increment_batch_job_retry("test-job-001")
        assert retry_count == 1

        job_data = db_manager.get_batch_job("test-job-001")
        assert job_data["retry_count"] == 1
        assert job_data["status"] == "retrying"

        # Second retry
        retry_count = db_manager.increment_batch_job_retry("test-job-001")
        assert retry_count == 2

        job_data = db_manager.get_batch_job("test-job-001")
        assert job_data["retry_count"] == 2

    def test_delete_batch_job(self, db_manager, sample_job_result):
        """Test deleting a batch job"""
        db_manager.save_batch_job(sample_job_result)

        # Verify job exists
        assert db_manager.get_batch_job("test-job-001") is not None

        # Delete job
        deleted = db_manager.delete_batch_job("test-job-001")
        assert deleted is True

        # Verify job is gone
        assert db_manager.get_batch_job("test-job-001") is None

        # Try deleting non-existent job
        deleted = db_manager.delete_batch_job("nonexistent")
        assert deleted is False

    def test_get_batch_summary_empty(self, db_manager):
        """Test getting summary from empty database"""
        summary = db_manager.get_batch_summary()

        assert summary["total_jobs"] == 0
        assert summary["completed"] == 0
        assert summary["failed"] == 0
        assert summary["running"] == 0
        assert summary["pending"] == 0

    def test_get_batch_summary_with_jobs(self, db_manager, tmp_path):
        """Test getting summary with various job statuses"""
        config = CSVJobConfig(
            csv_path=tmp_path / "test.csv",
            audio_dir=tmp_path / "audio",
        )

        # Create jobs with different statuses
        statuses = [
            JobStatus.PENDING,
            JobStatus.PENDING,
            JobStatus.RUNNING,
            JobStatus.COMPLETED,
            JobStatus.COMPLETED,
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.RETRYING,
            JobStatus.CANCELLED,
        ]

        for i, status in enumerate(statuses):
            job = JobResult(
                job_id=f"job-{i:03d}",
                status=status,
                config=config,
                created_at=datetime.now(),
            )
            db_manager.save_batch_job(job)

        summary = db_manager.get_batch_summary()

        assert summary["total_jobs"] == 9
        assert summary["pending"] == 2
        assert summary["running"] == 1
        assert summary["completed"] == 3
        assert summary["failed"] == 1
        assert summary["retrying"] == 1
        assert summary["cancelled"] == 1

    def test_batch_job_with_output_path(self, db_manager, tmp_path):
        """Test saving job with output path and YouTube URL"""
        config = CSVJobConfig(
            csv_path=tmp_path / "test.csv",
            audio_dir=tmp_path / "audio",
        )

        job = JobResult(
            job_id="test-job-001",
            status=JobStatus.COMPLETED,
            config=config,
            created_at=datetime.now(),
            output_path=tmp_path / "output" / "video.mp4",
            youtube_url="https://youtube.com/watch?v=test123",
        )

        db_manager.save_batch_job(job)

        job_data = db_manager.get_batch_job("test-job-001")
        assert job_data["output_path"] is not None
        assert "video.mp4" in job_data["output_path"]
        assert job_data["youtube_url"] == "https://youtube.com/watch?v=test123"

    def test_batch_job_metadata_persistence(self, db_manager, tmp_path):
        """Test that metadata is correctly persisted"""
        config = CSVJobConfig(
            csv_path=tmp_path / "test.csv",
            audio_dir=tmp_path / "audio",
        )

        metadata = {
            "user": "test_user",
            "priority_level": "high",
            "tags": ["production", "batch1"],
            "custom_data": {"key": "value"},
        }

        job = JobResult(
            job_id="test-job-001",
            status=JobStatus.PENDING,
            config=config,
            created_at=datetime.now(),
            metadata=metadata,
        )

        db_manager.save_batch_job(job)

        job_data = db_manager.get_batch_job("test-job-001")
        assert job_data["metadata"]["user"] == "test_user"
        assert job_data["metadata"]["priority_level"] == "high"
        assert job_data["metadata"]["tags"] == ["production", "batch1"]
        assert job_data["metadata"]["custom_data"]["key"] == "value"
