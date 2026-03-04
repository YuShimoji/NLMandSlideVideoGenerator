"""Tests for JobTracker"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

# プロジェクトルートを sys.path に追加
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from batch.models import JobStatus
from batch.tracker import JobTracker
from batch.retry_manager import RetryManager, RetryPolicy
from core.persistence import DatabaseManager
from core.exceptions import AudioGenerationError


@pytest.fixture
def db_manager(tmp_path):
    """Create a temporary database manager"""
    db_path = tmp_path / "test.db"
    return DatabaseManager(db_path=db_path)


@pytest.fixture
def retry_manager():
    """Create a retry manager with fast retries for testing"""
    policy = RetryPolicy(
        max_retries=2,
        base_delay_seconds=0.1,
        exponential_factor=1.5,
        jitter=False,
    )
    return RetryManager(policy=policy)


@pytest.fixture
def tracker(db_manager, retry_manager):
    """Create a JobTracker instance"""
    return JobTracker(db_manager=db_manager, retry_manager=retry_manager)


@pytest.fixture
def sample_paths(tmp_path):
    """Create sample paths for testing"""
    csv_path = tmp_path / "test.csv"
    csv_path.touch()
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    return csv_path, audio_dir


class TestJobTrackerBasics:
    """Test basic JobTracker operations"""

    def test_initialization(self, tracker):
        """Test JobTracker initialization"""
        assert tracker.db is not None
        assert tracker.retry_manager is not None

    def test_create_job(self, tracker, sample_paths):
        """Test creating a new job"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(
            csv_path=csv_path,
            audio_dir=audio_dir,
            topic="Test Video",
            priority=5,
        )

        assert job.job_id.startswith("job-")
        assert job.status == JobStatus.PENDING
        assert job.config.topic == "Test Video"
        assert job.config.priority == 5
        assert job.retry_count == 0

    def test_create_job_generates_unique_ids(self, tracker, sample_paths):
        """Test that each job gets a unique ID"""
        csv_path, audio_dir = sample_paths

        job1 = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)
        job2 = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        assert job1.job_id != job2.job_id

    def test_get_job(self, tracker, sample_paths):
        """Test retrieving a job by ID"""
        csv_path, audio_dir = sample_paths

        created_job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        retrieved_job = tracker.get_job(created_job.job_id)

        assert retrieved_job is not None
        assert retrieved_job.job_id == created_job.job_id
        assert retrieved_job.status == JobStatus.PENDING

    def test_get_job_not_found(self, tracker):
        """Test getting non-existent job returns None"""
        job = tracker.get_job("nonexistent-job-id")
        assert job is None

    def test_get_jobs_empty(self, tracker):
        """Test getting jobs from empty tracker"""
        jobs = tracker.get_jobs()
        assert jobs == []

    def test_get_jobs_multiple(self, tracker, sample_paths):
        """Test getting multiple jobs"""
        csv_path, audio_dir = sample_paths

        # Create 5 jobs
        for i in range(5):
            tracker.create_job(
                csv_path=csv_path,
                audio_dir=audio_dir,
                topic=f"Video {i}",
            )

        jobs = tracker.get_jobs()

        assert len(jobs) == 5
        assert all(job.status == JobStatus.PENDING for job in jobs)

    def test_get_jobs_filtered_by_status(self, tracker, sample_paths):
        """Test filtering jobs by status"""
        csv_path, audio_dir = sample_paths

        # Create jobs with different statuses
        job1 = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)
        job2 = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)
        job3 = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        tracker.update_status(job1.job_id, JobStatus.RUNNING)
        tracker.update_status(job2.job_id, JobStatus.COMPLETED)
        # job3 remains PENDING

        # Get running jobs
        running_jobs = tracker.get_jobs(status=JobStatus.RUNNING)
        assert len(running_jobs) == 1
        assert running_jobs[0].job_id == job1.job_id

        # Get pending jobs
        pending_jobs = tracker.get_jobs(status=JobStatus.PENDING)
        assert len(pending_jobs) == 1
        assert pending_jobs[0].job_id == job3.job_id

    def test_get_jobs_pagination(self, tracker, sample_paths):
        """Test job pagination"""
        csv_path, audio_dir = sample_paths

        # Create 10 jobs
        for i in range(10):
            tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        # Get first page
        page1 = tracker.get_jobs(limit=3, offset=0)
        assert len(page1) == 3

        # Get second page
        page2 = tracker.get_jobs(limit=3, offset=3)
        assert len(page2) == 3

        # Verify no overlap
        page1_ids = {job.job_id for job in page1}
        page2_ids = {job.job_id for job in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestJobTrackerStatusUpdates:
    """Test status update operations"""

    def test_update_status(self, tracker, sample_paths):
        """Test updating job status"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        tracker.update_status(job.job_id, JobStatus.RUNNING)

        updated_job = tracker.get_job(job.job_id)
        assert updated_job.status == JobStatus.RUNNING

    def test_update_status_with_error_message(self, tracker, sample_paths):
        """Test updating status with error message"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        tracker.update_status(
            job.job_id,
            JobStatus.FAILED,
            error_message="Test error",
        )

        updated_job = tracker.get_job(job.job_id)
        assert updated_job.status == JobStatus.FAILED
        assert updated_job.error_message == "Test error"

    def test_mark_started(self, tracker, sample_paths):
        """Test marking job as started"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        tracker.mark_started(job.job_id)

        updated_job = tracker.get_job(job.job_id)
        assert updated_job.status == JobStatus.RUNNING
        assert updated_job.started_at is not None
        assert updated_job.progress == 0.0

    def test_mark_completed(self, tracker, sample_paths, tmp_path):
        """Test marking job as completed"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)
        tracker.mark_started(job.job_id)

        output_path = tmp_path / "output" / "video.mp4"
        youtube_url = "https://youtube.com/watch?v=test123"

        tracker.mark_completed(
            job.job_id,
            output_path=output_path,
            youtube_url=youtube_url,
        )

        updated_job = tracker.get_job(job.job_id)
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.progress == 100.0
        assert updated_job.completed_at is not None
        assert updated_job.output_path == output_path
        assert updated_job.youtube_url == youtube_url

    def test_mark_failed_no_retry(self, tracker, sample_paths):
        """Test marking job as failed without retry"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(
            csv_path=csv_path,
            audio_dir=audio_dir,
            max_retries=0,  # No retries allowed
        )

        error = ValueError("Invalid configuration")
        will_retry = tracker.mark_failed(job.job_id, error)

        assert will_retry is False

        updated_job = tracker.get_job(job.job_id)
        assert updated_job.status == JobStatus.FAILED
        assert "ValueError" in updated_job.error_message

    def test_mark_failed_with_retry(self, tracker, sample_paths):
        """Test marking job as failed with retry"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(
            csv_path=csv_path,
            audio_dir=audio_dir,
            max_retries=3,
        )

        error = ConnectionError("Network timeout")
        will_retry = tracker.mark_failed(job.job_id, error)

        assert will_retry is True

        updated_job = tracker.get_job(job.job_id)
        assert updated_job.status == JobStatus.RETRYING
        assert updated_job.retry_count == 1

    def test_mark_cancelled(self, tracker, sample_paths):
        """Test marking job as cancelled"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        tracker.mark_cancelled(job.job_id, reason="User requested")

        updated_job = tracker.get_job(job.job_id)
        assert updated_job.status == JobStatus.CANCELLED
        assert "User requested" in updated_job.error_message


class TestJobTrackerProgress:
    """Test progress tracking operations"""

    def test_update_progress(self, tracker, sample_paths):
        """Test updating job progress"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        tracker.update_progress(
            job.job_id,
            progress=50.0,
            stage="audio",
            message="Generating audio...",
        )

        updated_job = tracker.get_job(job.job_id)
        assert updated_job.progress == 50.0
        assert updated_job.metadata["current_stage"] == "audio"
        assert updated_job.metadata["progress_message"] == "Generating audio..."

    def test_update_progress_clamps_values(self, tracker, sample_paths):
        """Test that progress values are clamped to 0-100"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        # Test negative value
        tracker.update_progress(job.job_id, progress=-10.0)
        updated_job = tracker.get_job(job.job_id)
        assert updated_job.progress == 0.0

        # Test over 100 value
        tracker.update_progress(job.job_id, progress=150.0)
        updated_job = tracker.get_job(job.job_id)
        assert updated_job.progress == 100.0

    def test_update_progress_preserves_metadata(self, tracker, sample_paths):
        """Test that progress updates preserve existing metadata"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        # First update
        tracker.update_progress(job.job_id, 25.0, stage="stage1")

        # Second update
        tracker.update_progress(job.job_id, 50.0, stage="stage2", message="Processing...")

        updated_job = tracker.get_job(job.job_id)
        assert updated_job.progress == 50.0
        assert updated_job.metadata["current_stage"] == "stage2"
        assert updated_job.metadata["progress_message"] == "Processing..."


class TestJobTrackerOperations:
    """Test higher-level operations"""

    def test_delete_job(self, tracker, sample_paths):
        """Test deleting a job"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        deleted = tracker.delete_job(job.job_id)
        assert deleted is True

        # Verify job is gone
        assert tracker.get_job(job.job_id) is None

    def test_delete_job_not_found(self, tracker):
        """Test deleting non-existent job"""
        deleted = tracker.delete_job("nonexistent-id")
        assert deleted is False

    def test_get_summary(self, tracker, sample_paths):
        """Test getting batch summary"""
        csv_path, audio_dir = sample_paths

        # Create jobs with various statuses
        job1 = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)
        job2 = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)
        job3 = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)
        job4 = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        tracker.update_status(job1.job_id, JobStatus.RUNNING)
        tracker.update_status(job2.job_id, JobStatus.COMPLETED)
        tracker.update_status(job3.job_id, JobStatus.FAILED)
        # job4 remains PENDING

        summary = tracker.get_summary()

        assert summary.total_jobs == 4
        assert summary.running == 1
        assert summary.completed == 1
        assert summary.failed == 1
        assert summary.pending == 1

    def test_get_metrics(self, tracker, sample_paths):
        """Test getting detailed metrics"""
        csv_path, audio_dir = sample_paths

        # Create and complete some jobs
        for i in range(3):
            job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)
            tracker.mark_started(job.job_id)
            tracker.mark_completed(job.job_id)

        metrics = tracker.get_metrics()

        assert "summary" in metrics
        assert "duration_stats" in metrics
        assert "retry_stats" in metrics
        assert "throughput" in metrics

        assert metrics["summary"]["total_jobs"] == 3
        assert metrics["summary"]["completed"] == 3
        assert metrics["duration_stats"]["total_completed"] == 3

    @pytest.mark.asyncio
    async def test_track_job_execution_success(self, tracker, sample_paths):
        """Test tracking successful job execution"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        async def task():
            return {
                "success": True,
                "artifacts": {
                    "video": {"file_path": "/path/to/video.mp4"}
                },
            }

        result = await tracker.track_job_execution(job.job_id, task)

        assert result["success"] is True

        updated_job = tracker.get_job(job.job_id)
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.progress == 100.0

    @pytest.mark.asyncio
    async def test_track_job_execution_with_progress_callback(self, tracker, sample_paths):
        """Test job execution with progress callback"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        progress_updates = []

        def progress_callback(progress, message):
            progress_updates.append((progress, message))

        async def task():
            return {"success": True}

        await tracker.track_job_execution(
            job.job_id,
            task,
            progress_callback=progress_callback,
        )

        # Should have at least one update (start)
        assert len(progress_updates) >= 1

    @pytest.mark.asyncio
    async def test_track_job_execution_failure(self, tracker, sample_paths):
        """Test tracking failed job execution"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(
            csv_path=csv_path,
            audio_dir=audio_dir,
            max_retries=0,  # No retries
        )

        async def task():
            raise ValueError("Test failure")

        with pytest.raises(ValueError, match="Test failure"):
            await tracker.track_job_execution(job.job_id, task)

        updated_job = tracker.get_job(job.job_id)
        assert updated_job.status == JobStatus.FAILED

    @pytest.mark.asyncio
    async def test_track_job_execution_with_retry(self, tracker, sample_paths):
        """Test job execution retries on failure"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(
            csv_path=csv_path,
            audio_dir=audio_dir,
            max_retries=2,
        )

        call_count = 0

        async def task():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return {"success": True}

        result = await tracker.track_job_execution(job.job_id, task)

        assert result["success"] is True
        assert call_count == 2  # First failure, then success

        updated_job = tracker.get_job(job.job_id)
        assert updated_job.status == JobStatus.COMPLETED
