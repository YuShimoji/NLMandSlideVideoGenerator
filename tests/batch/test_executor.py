"""Tests for BatchExecutor (integration with pipeline)"""

from __future__ import annotations

import sys
import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# プロジェクトルートを sys.path に追加
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from batch.models import JobStatus, CSVJobConfig
from batch.executor import BatchExecutor
from batch.tracker import JobTracker
from batch.retry_manager import RetryManager, RetryPolicy
from core.persistence import DatabaseManager
from core.exceptions import PipelineError


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
    # Create a minimal CSV file
    csv_path.write_text("start_time,text,audio_file\n0.0,Test content,audio_001.wav\n")

    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    # Create a dummy audio file
    audio_file = audio_dir / "audio_001.wav"
    audio_file.touch()

    return csv_path, audio_dir


@pytest.fixture
def mock_pipeline():
    """Create a mock ModularVideoPipeline"""
    with patch("batch.executor.build_default_pipeline") as mock_build:
        pipeline = MagicMock()
        pipeline.slide_generator = MagicMock()
        pipeline.video_composer = MagicMock()
        pipeline.metadata_generator = MagicMock()
        pipeline.uploader = MagicMock()
        pipeline.timeline_planner = MagicMock()
        pipeline.platform_adapter = MagicMock()
        pipeline.publishing_queue = MagicMock()

        mock_build.return_value = pipeline
        yield pipeline


@pytest.fixture
def executor(tracker, db_manager, mock_pipeline):
    """Create a BatchExecutor instance with mocked pipeline"""
    return BatchExecutor(
        job_tracker=tracker,
        db_manager=db_manager,
    )


class TestBatchExecutorBasics:
    """Test basic BatchExecutor operations"""

    def test_initialization(self, executor):
        """Test BatchExecutor initialization"""
        assert executor.tracker is not None
        assert executor.db is not None
        assert executor.pipeline is not None

    @pytest.mark.asyncio
    async def test_execute_job_not_found(self, executor):
        """Test executing a non-existent job raises error"""
        with pytest.raises(ValueError, match="Job not found"):
            await executor.execute_job("fake-job-id")


class TestBatchExecutorIntegration:
    """Test integration with pipeline (mocked)"""

    @pytest.mark.asyncio
    async def test_execute_job_success(self, executor, tracker, sample_paths):
        """Test successful job execution"""
        csv_path, audio_dir = sample_paths

        # Create a job
        job = tracker.create_job(
            csv_path=csv_path,
            audio_dir=audio_dir,
            topic="Test Video",
        )

        # Mock run_csv_timeline to return success
        with patch("batch.executor.run_csv_timeline") as mock_run:
            mock_run.return_value = {
                "video_path": "/tmp/output.mp4",
                "youtube_url": None,
            }

            # Execute job
            result = await executor.execute_job(job.job_id)

            assert result.status == JobStatus.COMPLETED
            assert mock_run.called

            # Verify DB updated
            db_job = executor.db.get_batch_job(job.job_id)
            assert db_job["status"] == "completed"
            # Path may be normalized to OS format
            assert db_job["output_path"] in ["/tmp/output.mp4", "\\tmp\\output.mp4"]

    @pytest.mark.asyncio
    async def test_execute_job_with_ymm4_export(self, executor, tracker, sample_paths, tmp_path):
        """Test job execution with YMM4 export enabled"""
        csv_path, audio_dir = sample_paths
        package_path = tmp_path / "output.exo"

        # Create a job with YMM4 export
        job = tracker.create_job(
            csv_path=csv_path,
            audio_dir=audio_dir,
            topic="YMM4 Test",
            export_ymm4=True,
            package_path=package_path,
        )

        # Mock run_csv_timeline and YMM4 backend
        with patch("batch.executor.run_csv_timeline") as mock_run:
            with patch("core.editing.ymm4_backend.YMM4EditingBackend"):
                mock_run.return_value = {
                    "video_path": str(package_path),
                }

                # Execute job
                result = await executor.execute_job(job.job_id)

                assert result.status == JobStatus.COMPLETED
                assert mock_run.called

                # Verify YMM4 backend was used
                call_kwargs = mock_run.call_args.kwargs
                assert "editing_backend" in call_kwargs
                assert call_kwargs["editing_backend"] is not None

    @pytest.mark.asyncio
    async def test_execute_job_with_progress_callback(self, executor, tracker, sample_paths):
        """Test that progress callback is invoked"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        progress_calls = []

        def progress_callback(stage: str, progress: float, message: str):
            progress_calls.append((stage, progress, message))

        # Mock run_csv_timeline to simulate progress
        with patch("batch.executor.run_csv_timeline") as mock_run:
            async def mock_run_with_progress(*args, **kwargs):
                # Simulate progress callbacks
                callback = kwargs.get("progress_callback")
                if callback:
                    callback("slides", 0.5, "Generating slides")
                    callback("video", 1.0, "Composing video")

                return {"video_path": "/tmp/test.mp4"}

            mock_run.side_effect = mock_run_with_progress

            # Execute with callback
            await executor.execute_job(job.job_id, progress_callback=progress_callback)

            # Verify callback was invoked
            assert len(progress_calls) >= 2
            assert any("slides" in call[0] or "slide" in call[2].lower() for call in progress_calls)

    @pytest.mark.asyncio
    async def test_execute_job_failure_recoverable(self, executor, tracker, sample_paths):
        """Test job failure with recoverable error triggers retry"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(
            csv_path=csv_path,
            audio_dir=audio_dir,
            max_retries=3,
        )

        # Mock run_csv_timeline to raise recoverable error
        with patch("batch.executor.run_csv_timeline") as mock_run:
            mock_run.side_effect = PipelineError(
                message="Temporary network error",
                stage="upload",
                recoverable=True,
            )

            # Execute should raise PipelineError
            with pytest.raises(PipelineError) as exc_info:
                await executor.execute_job(job.job_id)

            assert exc_info.value.recoverable is True

            # Job should be in retrying state
            updated_job = tracker.get_job(job.job_id)
            # Status may be RUNNING or RETRYING depending on timing
            assert updated_job.status in [JobStatus.RUNNING, JobStatus.RETRYING]

    @pytest.mark.asyncio
    async def test_execute_job_failure_non_recoverable(self, executor, tracker, sample_paths):
        """Test job failure with non-recoverable error"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(csv_path=csv_path, audio_dir=audio_dir)

        # Mock run_csv_timeline to raise non-recoverable error
        with patch("batch.executor.run_csv_timeline") as mock_run:
            mock_run.side_effect = ValueError("Invalid CSV format")

            # Execute should raise PipelineError
            with pytest.raises(PipelineError):
                await executor.execute_job(job.job_id)

            # Job should be marked as failed
            updated_job = tracker.get_job(job.job_id)
            assert updated_job.status == JobStatus.FAILED
            assert "Invalid CSV format" in updated_job.error_message


class TestBatchExecutorRetry:
    """Test retry logic"""

    @pytest.mark.asyncio
    async def test_execute_job_with_retry_success_on_second_attempt(
        self, executor, tracker, sample_paths
    ):
        """Test that job succeeds on retry after initial failure"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(
            csv_path=csv_path,
            audio_dir=audio_dir,
            max_retries=3,
        )

        # Mock run_csv_timeline to fail once, then succeed
        call_count = 0

        with patch("batch.executor.run_csv_timeline") as mock_run:
            def mock_run_with_retry(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # First attempt fails
                    raise PipelineError(
                        message="Temporary error",
                        stage="test",
                        recoverable=True,
                    )
                else:
                    # Second attempt succeeds
                    return {"video_path": "/tmp/test.mp4"}

            mock_run.side_effect = mock_run_with_retry

            # Execute with retry
            result = await executor.execute_job_with_retry(job.job_id)

            assert result.status == JobStatus.COMPLETED
            assert call_count == 2  # Failed once, succeeded on retry

    @pytest.mark.asyncio
    async def test_execute_job_with_retry_max_retries_exceeded(
        self, executor, tracker, sample_paths
    ):
        """Test that job fails after max retries"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(
            csv_path=csv_path,
            audio_dir=audio_dir,
            max_retries=2,
        )

        # Mock run_csv_timeline to always fail
        with patch("batch.executor.run_csv_timeline") as mock_run:
            mock_run.side_effect = PipelineError(
                message="Persistent error",
                stage="test",
                recoverable=True,
            )

            # Execute with retry should eventually fail
            with pytest.raises(PipelineError):
                await executor.execute_job_with_retry(job.job_id)

            # Job should be marked as failed
            updated_job = tracker.get_job(job.job_id)
            assert updated_job.status == JobStatus.FAILED
            assert updated_job.retry_count >= 2


class TestBatchExecutorConfiguration:
    """Test configuration handling"""

    @pytest.mark.asyncio
    async def test_execute_job_with_custom_quality(self, executor, tracker, sample_paths):
        """Test that video quality setting is passed to pipeline"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(
            csv_path=csv_path,
            audio_dir=audio_dir,
            video_quality="720p",
        )

        with patch("batch.executor.run_csv_timeline") as mock_run:
            mock_run.return_value = {"video_path": "/tmp/test.mp4"}

            await executor.execute_job(job.job_id)

            # Verify quality was passed
            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs["quality"] == "720p"

    @pytest.mark.asyncio
    async def test_execute_job_with_upload(self, executor, tracker, sample_paths):
        """Test that upload flag is passed to pipeline"""
        csv_path, audio_dir = sample_paths

        job = tracker.create_job(
            csv_path=csv_path,
            audio_dir=audio_dir,
            upload=True,
            public_upload=True,
        )

        with patch("batch.executor.run_csv_timeline") as mock_run:
            mock_run.return_value = {
                "video_path": "/tmp/test.mp4",
                "youtube_url": "https://youtube.com/watch?v=test",
            }

            await executor.execute_job(job.job_id)

            # Verify upload settings were passed
            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs["upload"] is True
            assert call_kwargs["private_upload"] is False  # public_upload=True → private=False

            # Verify YouTube URL stored
            db_job = executor.db.get_batch_job(job.job_id)
            assert db_job["youtube_url"] == "https://youtube.com/watch?v=test"
