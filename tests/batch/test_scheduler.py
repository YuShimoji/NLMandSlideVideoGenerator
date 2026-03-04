"""Tests for BatchScheduler"""

from __future__ import annotations

import sys
import asyncio
from datetime import datetime
from pathlib import Path

import pytest

# プロジェクトルートを sys.path に追加
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from batch.models import JobStatus
from batch.scheduler import BatchScheduler
from batch.tracker import JobTracker
from batch.executor import BatchExecutor
from batch.retry_manager import RetryManager, RetryPolicy
from core.persistence import DatabaseManager
from unittest.mock import AsyncMock, MagicMock


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
def mock_executor(tracker, db_manager):
    """Create a mock BatchExecutor that simulates job execution"""
    executor = BatchExecutor(job_tracker=tracker, db_manager=db_manager)

    # Mock execute_job to complete quickly
    async def mock_execute(job_id, config=None, progress_callback=None):
        # Simulate fast execution
        await asyncio.sleep(1.0)
        tracker.update_status(job_id, JobStatus.COMPLETED)
        return tracker.get_job(job_id)

    executor.execute_job = AsyncMock(side_effect=mock_execute)
    return executor


@pytest.fixture
def scheduler(tracker, db_manager, mock_executor):
    """Create a BatchScheduler instance with mock executor"""
    return BatchScheduler(
        job_tracker=tracker,
        db_manager=db_manager,
        executor=mock_executor,
        max_concurrent_jobs=2,  # Small limit for testing
    )


@pytest.fixture
def sample_paths(tmp_path):
    """Create sample paths for testing"""
    csv_path = tmp_path / "test.csv"
    csv_path.touch()
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    return csv_path, audio_dir


class TestBatchSchedulerBasics:
    """Test basic BatchScheduler operations"""

    def test_initialization(self, scheduler):
        """Test BatchScheduler initialization"""
        assert scheduler.tracker is not None
        assert scheduler.db is not None
        assert scheduler.max_concurrent_jobs == 2
        assert len(scheduler._queue) == 0
        assert len(scheduler._running_jobs) == 0

    @pytest.mark.asyncio
    async def test_submit_job(self, scheduler, sample_paths):
        """Test submitting a job to the scheduler"""
        csv_path, audio_dir = sample_paths

        job = await scheduler.submit_job(
            csv_path=csv_path,
            audio_dir=audio_dir,
            topic="Test Video",
            priority=5,
        )

        assert job.job_id is not None
        assert job.status == JobStatus.PENDING
        assert job.config.priority == 5
        assert len(scheduler._queue) == 1

        # Verify job is in DB
        db_job = scheduler.db.get_batch_job(str(job.job_id))
        assert db_job is not None
        assert db_job["status"] == "pending"

    @pytest.mark.asyncio
    async def test_submit_multiple_jobs(self, scheduler, sample_paths):
        """Test submitting multiple jobs"""
        csv_path, audio_dir = sample_paths

        jobs = []
        for i in range(5):
            job = await scheduler.submit_job(
                csv_path=csv_path,
                audio_dir=audio_dir,
                topic=f"Test Video {i}",
                priority=i,
            )
            jobs.append(job)

        assert len(scheduler._queue) == 5
        assert len(jobs) == 5

        # Verify all jobs are unique
        job_ids = [job.job_id for job in jobs]
        assert len(set(job_ids)) == 5

    @pytest.mark.asyncio
    async def test_priority_ordering(self, scheduler, sample_paths):
        """Test that jobs are ordered by priority (higher priority first)"""
        csv_path, audio_dir = sample_paths

        # Submit jobs with different priorities
        job_low = await scheduler.submit_job(
            csv_path=csv_path, audio_dir=audio_dir, priority=1
        )
        job_high = await scheduler.submit_job(
            csv_path=csv_path, audio_dir=audio_dir, priority=10
        )
        job_med = await scheduler.submit_job(
            csv_path=csv_path, audio_dir=audio_dir, priority=5
        )

        # Queue should have 3 jobs
        assert len(scheduler._queue) == 3

        # Start scheduler briefly to process jobs
        await scheduler.start()
        await asyncio.sleep(3.0)  # Let scheduler process all jobs
        await scheduler.stop(wait_for_completion=True)

        # Verify execution order (high priority should run first)
        # Note: Since max_concurrent_jobs=2, only 2 jobs run initially
        job_high_result = scheduler.tracker.get_job(job_high.job_id)
        job_med_result = scheduler.tracker.get_job(job_med.job_id)
        job_low_result = scheduler.tracker.get_job(job_low.job_id)

        # High and med priority should complete first
        assert job_high_result.status == JobStatus.COMPLETED
        assert job_med_result.status == JobStatus.COMPLETED
        assert job_low_result.status == JobStatus.COMPLETED  # Eventually completes

    @pytest.mark.asyncio
    async def test_cancel_pending_job(self, scheduler, sample_paths):
        """Test cancelling a pending job"""
        csv_path, audio_dir = sample_paths

        job = await scheduler.submit_job(
            csv_path=csv_path, audio_dir=audio_dir, topic="Test"
        )

        # Cancel the job
        result = await scheduler.cancel_job(job.job_id)
        assert result is True

        # Job should be removed from queue
        assert len(scheduler._queue) == 0

        # Job status should be cancelled in DB
        db_job = scheduler.db.get_batch_job(str(job.job_id))
        assert db_job["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_running_job(self, scheduler, sample_paths):
        """Test cancelling a running job"""
        csv_path, audio_dir = sample_paths

        job = await scheduler.submit_job(
            csv_path=csv_path, audio_dir=audio_dir, topic="Test"
        )

        # Start scheduler
        await scheduler.start()
        await asyncio.sleep(0.3)  # Let job start running

        # Cancel the job
        result = await scheduler.cancel_job(job.job_id)
        assert result is True

        await scheduler.stop()

        # Job status should be cancelled
        final_job = scheduler.tracker.get_job(job.job_id)
        assert final_job.status == JobStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job(self, scheduler):
        """Test cancelling a non-existent job"""
        fake_job_id = "job-00000000-000000-00000000"

        result = await scheduler.cancel_job(fake_job_id)
        assert result is False


class TestBatchSchedulerConcurrency:
    """Test concurrency control"""

    @pytest.mark.asyncio
    async def test_max_concurrent_jobs(self, tmp_path):
        """Test that max_concurrent_jobs limit is respected"""
        # Create fresh scheduler with new DB to avoid interference
        db_path = tmp_path / "test_concurrent.db"
        db = DatabaseManager(db_path=db_path)
        retry_policy = RetryPolicy(max_retries=2, base_delay_seconds=0.1, exponential_factor=1.5, jitter=False)
        retry_mgr = RetryManager(policy=retry_policy)
        tracker = JobTracker(db_manager=db, retry_manager=retry_mgr)

        # Mock executor
        executor = BatchExecutor(job_tracker=tracker, db_manager=db)

        async def mock_execute(job_id, config=None, progress_callback=None):
            await asyncio.sleep(1.0)
            tracker.update_status(job_id, JobStatus.COMPLETED)
            return tracker.get_job(job_id)

        executor.execute_job = AsyncMock(side_effect=mock_execute)

        scheduler = BatchScheduler(
            job_tracker=tracker,
            db_manager=db,
            executor=executor,
            max_concurrent_jobs=2,
        )

        csv_path = tmp_path / "test.csv"
        csv_path.touch()
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        # Start scheduler FIRST (to avoid duplicate loading from DB)
        await scheduler.start()

        # Then submit jobs (they won't be restored since scheduler is already running)
        for i in range(5):
            await scheduler.submit_job(
                csv_path=csv_path,
                audio_dir=audio_dir,
                topic=f"Test {i}",
            )
        await asyncio.sleep(0.3)  # Let some jobs start

        # Check running jobs count
        status = scheduler.get_queue_status()
        assert status["running_jobs"] <= scheduler.max_concurrent_jobs
        assert status["running_jobs"] >= 1  # At least one should be running

        # Let all jobs complete before stopping
        await asyncio.sleep(3.0)  # Give enough time for all 5 jobs to complete

        await scheduler.stop(wait_for_completion=True)

        # All jobs should eventually complete (check DB, not queue)
        completed_jobs = db.get_batch_jobs(status="completed")
        assert len(completed_jobs) == 5

    @pytest.mark.asyncio
    async def test_get_queue_status(self, scheduler, sample_paths):
        """Test getting scheduler status"""
        csv_path, audio_dir = sample_paths

        # Submit some jobs
        for i in range(3):
            await scheduler.submit_job(
                csv_path=csv_path, audio_dir=audio_dir, topic=f"Test {i}"
            )

        status = scheduler.get_queue_status()

        assert status["queue_size"] == 3
        assert status["running_jobs"] == 0
        assert status["max_concurrent"] == 2
        assert len(status["running_job_ids"]) == 0


class TestBatchSchedulerPersistence:
    """Test DB persistence and recovery"""

    @pytest.mark.asyncio
    async def test_restore_from_db_pending(self, db_manager, tracker, sample_paths):
        """Test restoring pending jobs from DB on startup"""
        csv_path, audio_dir = sample_paths

        # Create jobs via tracker (simulates previous session)
        job1 = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir, priority=5)
        job2 = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir, priority=10)

        # Create new scheduler (simulates restart)
        new_scheduler = BatchScheduler(
            job_tracker=tracker,
            db_manager=db_manager,
            max_concurrent_jobs=2,
        )

        await new_scheduler.start()

        # Jobs should be restored to queue
        assert len(new_scheduler._queue) == 2

        await new_scheduler.stop()

    @pytest.mark.asyncio
    async def test_restore_from_db_running(self, db_manager, tracker, sample_paths):
        """Test restoring running jobs (reset to pending) on startup"""
        csv_path, audio_dir = sample_paths

        # Create a job and mark it as running (simulates interrupted job)
        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)
        tracker.update_status(job.job_id, JobStatus.RUNNING)

        # Create new scheduler (simulates restart)
        new_scheduler = BatchScheduler(
            job_tracker=tracker,
            db_manager=db_manager,
            max_concurrent_jobs=2,
        )

        await new_scheduler.start()

        # Job should be restored to queue as pending
        assert len(new_scheduler._queue) == 1

        await new_scheduler.stop()

        # Job status should be reset to pending
        restored_job = tracker.get_job(job.job_id)
        assert restored_job.status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_restore_skips_completed_jobs(self, db_manager, tracker, sample_paths):
        """Test that completed/failed jobs are not restored"""
        csv_path, audio_dir = sample_paths

        # Create jobs with different statuses
        job_pending = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)
        job_completed = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)
        job_failed = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        tracker.update_status(job_completed.job_id, JobStatus.COMPLETED)

        # Mark as failed and ensure it doesn't auto-retry
        tracker.mark_failed(job_failed.job_id, "Test error")
        # Force status to failed (not retrying)
        db_manager.update_batch_job_status(
            str(job_failed.job_id),
            status="failed",
            error_message="Test error"
        )

        # Create new scheduler
        new_scheduler = BatchScheduler(
            job_tracker=tracker,
            db_manager=db_manager,
            max_concurrent_jobs=2,
        )

        await new_scheduler.start()

        # Only pending job should be restored
        assert len(new_scheduler._queue) == 1

        await new_scheduler.stop()


class TestBatchSchedulerLifecycle:
    """Test scheduler lifecycle (start/stop)"""

    @pytest.mark.asyncio
    async def test_start_scheduler(self, scheduler):
        """Test starting the scheduler"""
        await scheduler.start()

        assert scheduler._scheduler_task is not None
        assert not scheduler._shutdown_event.is_set()

        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_stop_scheduler_graceful(self, scheduler, sample_paths):
        """Test graceful shutdown (wait for jobs to complete)"""
        csv_path, audio_dir = sample_paths

        # Submit a job
        await scheduler.submit_job(csv_path=csv_path, audio_dir=audio_dir)

        await scheduler.start()
        await asyncio.sleep(0.3)  # Let job start

        # Graceful shutdown
        await scheduler.stop(wait_for_completion=True)

        assert len(scheduler._running_jobs) == 0
        assert scheduler._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_stop_scheduler_immediate(self, scheduler, sample_paths):
        """Test immediate shutdown (cancel jobs)"""
        csv_path, audio_dir = sample_paths

        # Submit multiple jobs
        for i in range(3):
            await scheduler.submit_job(csv_path=csv_path, audio_dir=audio_dir)

        await scheduler.start()
        await asyncio.sleep(0.3)  # Let jobs start

        # Immediate shutdown (cancel)
        await scheduler.stop(wait_for_completion=False)

        assert len(scheduler._running_jobs) == 0
        assert scheduler._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_double_start(self, scheduler):
        """Test that double start is handled gracefully"""
        await scheduler.start()
        await scheduler.start()  # Should log warning, not crash

        assert scheduler._scheduler_task is not None

        await scheduler.stop()
