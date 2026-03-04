"""Tests for RetryManager"""

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
from batch.retry_manager import RetryManager, RetryPolicy
from core.exceptions import AudioGenerationError, PipelineError


@pytest.fixture
def retry_policy():
    """Create a test retry policy"""
    return RetryPolicy(
        max_retries=3,
        base_delay_seconds=2.0,
        exponential_factor=2.0,
        jitter=False,  # Disable jitter for deterministic tests
    )


@pytest.fixture
def retry_manager(retry_policy):
    """Create a RetryManager instance"""
    return RetryManager(policy=retry_policy)


@pytest.fixture
def sample_job(tmp_path):
    """Create a sample job for testing"""
    config = CSVJobConfig(
        csv_path=tmp_path / "test.csv",
        audio_dir=tmp_path / "audio",
        max_retries=3,
    )

    return JobResult(
        job_id="test-job-001",
        status=JobStatus.FAILED,
        config=config,
        created_at=datetime.now(),
        retry_count=0,
    )


class TestRetryPolicy:
    """Test RetryPolicy configuration"""

    def test_default_policy(self):
        """Test default policy values"""
        policy = RetryPolicy()

        assert policy.max_retries == 3
        assert policy.base_delay_seconds == 2.0
        assert policy.max_delay_seconds == 60.0
        assert policy.exponential_factor == 2.0
        assert policy.jitter is True

    def test_calculate_delay_exponential(self, retry_policy):
        """Test exponential backoff calculation"""
        # retry_count=0: 2.0 * (2^0) = 2.0s
        assert retry_policy.calculate_delay(0) == pytest.approx(2.0)

        # retry_count=1: 2.0 * (2^1) = 4.0s
        assert retry_policy.calculate_delay(1) == pytest.approx(4.0)

        # retry_count=2: 2.0 * (2^2) = 8.0s
        assert retry_policy.calculate_delay(2) == pytest.approx(8.0)

        # retry_count=3: 2.0 * (2^3) = 16.0s
        assert retry_policy.calculate_delay(3) == pytest.approx(16.0)

    def test_calculate_delay_max_cap(self):
        """Test that delay is capped at max_delay_seconds"""
        policy = RetryPolicy(
            base_delay_seconds=2.0,
            max_delay_seconds=10.0,
            exponential_factor=2.0,
            jitter=False,
        )

        # retry_count=10 would be 2.0 * (2^10) = 2048.0s
        # But should be capped at 10.0s
        assert policy.calculate_delay(10) == pytest.approx(10.0)

    def test_calculate_delay_negative_retry_count(self, retry_policy):
        """Test that negative retry counts return 0"""
        assert retry_policy.calculate_delay(-1) == 0.0
        assert retry_policy.calculate_delay(-100) == 0.0

    def test_calculate_delay_with_jitter(self):
        """Test that jitter adds randomness"""
        policy = RetryPolicy(
            base_delay_seconds=10.0,
            exponential_factor=1.0,
            jitter=True,
        )

        # Get multiple delays and check they're different (due to jitter)
        delays = [policy.calculate_delay(0) for _ in range(10)]

        # All delays should be close to 10.0 but not identical
        assert all(9.0 <= d <= 11.0 for d in delays)
        assert len(set(delays)) > 1  # At least some variation


class TestRetryManager:
    """Test RetryManager functionality"""

    def test_initialization(self, retry_manager):
        """Test RetryManager initialization"""
        assert retry_manager.policy is not None
        assert retry_manager.policy.max_retries == 3

    def test_should_retry_below_max(self, retry_manager, sample_job):
        """Test should_retry returns True when below max retries"""
        sample_job.retry_count = 0
        assert retry_manager.should_retry(sample_job) is True

        sample_job.retry_count = 2
        assert retry_manager.should_retry(sample_job) is True

    def test_should_retry_at_max(self, retry_manager, sample_job):
        """Test should_retry returns False when at max retries"""
        sample_job.retry_count = 3
        assert retry_manager.should_retry(sample_job) is False

        sample_job.retry_count = 10
        assert retry_manager.should_retry(sample_job) is False

    def test_should_retry_only_failed_jobs(self, retry_manager, sample_job):
        """Test should_retry only works for failed/retrying jobs"""
        # Failed status - should retry
        sample_job.status = JobStatus.FAILED
        assert retry_manager.should_retry(sample_job) is True

        # Retrying status - should retry
        sample_job.status = JobStatus.RETRYING
        assert retry_manager.should_retry(sample_job) is True

        # Completed status - should not retry
        sample_job.status = JobStatus.COMPLETED
        assert retry_manager.should_retry(sample_job) is False

        # Running status - should not retry
        sample_job.status = JobStatus.RUNNING
        assert retry_manager.should_retry(sample_job) is False

    def test_is_recoverable_error_recoverable_types(self, retry_manager):
        """Test that certain error types are recoverable"""
        # Domain errors with recoverable=True
        error = AudioGenerationError("Test error", recoverable=True)
        assert retry_manager._is_recoverable_error(error) is True

        # Network errors
        assert retry_manager._is_recoverable_error(ConnectionError()) is True
        assert retry_manager._is_recoverable_error(TimeoutError()) is True

        # IO errors
        assert retry_manager._is_recoverable_error(IOError()) is True
        assert retry_manager._is_recoverable_error(OSError()) is True

    def test_is_recoverable_error_non_recoverable_types(self, retry_manager):
        """Test that certain error types are not recoverable"""
        # Configuration errors
        assert retry_manager._is_recoverable_error(ValueError("Invalid config")) is False
        assert retry_manager._is_recoverable_error(TypeError("Type error")) is False

        # Missing files
        assert retry_manager._is_recoverable_error(FileNotFoundError()) is False

        # Permission issues
        assert retry_manager._is_recoverable_error(PermissionError()) is False

    def test_is_recoverable_error_pipeline_error_flag(self, retry_manager):
        """Test PipelineError uses recoverable flag"""
        # Recoverable
        error = PipelineError("Recoverable error", stage="test", recoverable=True)
        assert retry_manager._is_recoverable_error(error) is True

        # Non-recoverable
        error = PipelineError("Non-recoverable error", stage="test", recoverable=False)
        assert retry_manager._is_recoverable_error(error) is False

    def test_should_retry_checks_error_recoverability(self, retry_manager, sample_job):
        """Test that should_retry considers error recoverability"""
        sample_job.retry_count = 0

        # Recoverable error
        recoverable_error = ConnectionError("Network error")
        assert retry_manager.should_retry(sample_job, recoverable_error) is True

        # Non-recoverable error
        non_recoverable_error = ValueError("Invalid configuration")
        assert retry_manager.should_retry(sample_job, non_recoverable_error) is False

    def test_calculate_next_retry_time(self, retry_manager, sample_job):
        """Test calculation of next retry time"""
        sample_job.retry_count = 0

        next_retry = retry_manager.calculate_next_retry_time(sample_job)
        now = datetime.now()

        # Should be approximately 2 seconds in the future
        delta = (next_retry - now).total_seconds()
        assert 1.9 <= delta <= 2.1

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_first_try(self, retry_manager, sample_job):
        """Test execute_with_retry succeeds on first try"""
        call_count = 0

        async def task():
            nonlocal call_count
            call_count += 1
            return {"success": True, "result": "done"}

        result = await retry_manager.execute_with_retry(sample_job, task)

        assert result["success"] is True
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_after_retries(self, retry_manager, sample_job):
        """Test execute_with_retry succeeds after retries"""
        call_count = 0

        async def task():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return {"success": True, "result": "done"}

        result = await retry_manager.execute_with_retry(sample_job, task)

        assert result["success"] is True
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_exhausts_retries(self, retry_manager, sample_job):
        """Test execute_with_retry fails after exhausting retries"""
        call_count = 0

        async def task():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent failure")

        with pytest.raises(ConnectionError, match="Persistent failure"):
            await retry_manager.execute_with_retry(sample_job, task)

        # Should try: initial + 3 retries = 4 attempts
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_execute_with_retry_non_recoverable_error(self, retry_manager, sample_job):
        """Test execute_with_retry doesn't retry non-recoverable errors"""
        call_count = 0

        async def task():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid configuration")

        with pytest.raises(ValueError, match="Invalid configuration"):
            await retry_manager.execute_with_retry(sample_job, task)

        # Should only try once (no retries)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_retry_callback(self, retry_manager, sample_job):
        """Test execute_with_retry calls retry callback"""
        call_count = 0
        callback_calls = []

        async def task():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return {"success": True}

        async def on_retry(job, retry_count):
            callback_calls.append((job.job_id, retry_count))

        result = await retry_manager.execute_with_retry(
            sample_job,
            task,
            on_retry=on_retry,
        )

        assert result["success"] is True
        assert len(callback_calls) == 1
        assert callback_calls[0] == ("test-job-001", 1)

    def test_get_retry_stats(self, retry_manager, sample_job):
        """Test get_retry_stats returns correct information"""
        sample_job.retry_count = 1

        stats = retry_manager.get_retry_stats(sample_job)

        assert stats["retry_count"] == 1
        assert stats["max_retries"] == 3
        assert stats["remaining_retries"] == 2
        assert stats["next_delay_seconds"] == pytest.approx(4.0)  # 2^1 * 2.0
        assert stats["is_retriable"] is True

    def test_get_retry_stats_exhausted(self, retry_manager, sample_job):
        """Test get_retry_stats when retries exhausted"""
        sample_job.retry_count = 3

        stats = retry_manager.get_retry_stats(sample_job)

        assert stats["retry_count"] == 3
        assert stats["remaining_retries"] == 0
        assert stats["next_delay_seconds"] is None
        assert stats["is_retriable"] is False

    def test_reset_retry_count(self, retry_manager, sample_job):
        """Test reset_retry_count clears retry state"""
        sample_job.retry_count = 5
        sample_job.error_message = "Previous error"

        retry_manager.reset_retry_count(sample_job)

        assert sample_job.retry_count == 0
        assert sample_job.error_message is None
