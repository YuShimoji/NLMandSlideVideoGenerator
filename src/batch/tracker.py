"""Job tracking and progress management for batch processing"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable, Awaitable, Dict, Any

from .models import JobStatus, CSVJobConfig, JobResult, BatchSummary
from .retry_manager import RetryManager
from core.persistence import DatabaseManager
from core.utils.logger import logger


class JobTracker:
    """Tracks batch job status, progress, and metrics"""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        retry_manager: Optional[RetryManager] = None,
    ):
        """Initialize JobTracker

        Args:
            db_manager: Database manager for persistence (creates new if None)
            retry_manager: Retry manager for handling failures (creates new if None)
        """
        self.db = db_manager or DatabaseManager()
        self.retry_manager = retry_manager or RetryManager()

        logger.info("JobTracker initialized")

    def create_job(
        self,
        csv_path: Path,
        audio_dir: Path,
        **kwargs
    ) -> JobResult:
        """Create a new batch job

        Args:
            csv_path: Path to CSV timeline file
            audio_dir: Directory containing audio files
            **kwargs: Additional CSVJobConfig parameters

        Returns:
            Newly created JobResult
        """
        # Create config
        config = CSVJobConfig(
            csv_path=csv_path,
            audio_dir=audio_dir,
            **kwargs
        )

        # Generate unique job ID
        job_id = f"job-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"

        # Create job result
        job_result = JobResult(
            job_id=job_id,
            status=JobStatus.PENDING,
            config=config,
            created_at=datetime.now(),
        )

        # Persist to database
        self.db.save_batch_job(job_result)

        logger.info(
            f"Created job {job_id}: {config.topic or csv_path.stem} "
            f"(priority={config.priority})"
        )

        return job_result

    def get_job(self, job_id: str) -> Optional[JobResult]:
        """Get a job by ID

        Args:
            job_id: Job ID to retrieve

        Returns:
            JobResult if found, None otherwise
        """
        job_data = self.db.get_batch_job(job_id)
        if job_data is None:
            return None

        return self._job_data_to_result(job_data)

    def get_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[JobResult]:
        """Get multiple jobs with optional filtering

        Args:
            status: Filter by status (optional)
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip

        Returns:
            List of JobResult objects
        """
        status_str = status.value if status else None
        jobs_data = self.db.get_batch_jobs(
            status=status_str,
            limit=limit,
            offset=offset,
        )

        return [self._job_data_to_result(data) for data in jobs_data]

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """Update job status

        Args:
            job_id: Job ID
            status: New status
            error_message: Error message if failed
        """
        now = datetime.now()

        # Determine timestamp updates based on status
        started_at = now if status == JobStatus.RUNNING else None
        completed_at = now if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED) else None

        self.db.update_batch_job_status(
            job_id=job_id,
            status=status.value,
            error_message=error_message,
            started_at=started_at,
            completed_at=completed_at,
        )

        logger.info(f"Job {job_id} status updated: {status.value}")

    def update_progress(
        self,
        job_id: str,
        progress: float,
        stage: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """Update job progress

        Args:
            job_id: Job ID
            progress: Progress percentage (0.0-100.0)
            stage: Current stage name (optional)
            message: Progress message (optional)
        """
        # Validate progress
        progress = max(0.0, min(100.0, progress))

        # Build metadata
        metadata = {}
        if stage:
            metadata["current_stage"] = stage
        if message:
            metadata["progress_message"] = message
        metadata["last_updated"] = datetime.now().isoformat()

        # Get existing metadata and merge
        job_data = self.db.get_batch_job(job_id)
        if job_data and job_data.get("metadata"):
            existing_metadata = job_data["metadata"]
            existing_metadata.update(metadata)
            metadata = existing_metadata

        self.db.update_batch_job_progress(
            job_id=job_id,
            progress=progress,
            metadata=metadata,
        )

        logger.debug(
            f"Job {job_id} progress: {progress:.1f}% "
            f"{f'[{stage}]' if stage else ''} {message or ''}"
        )

    def mark_started(self, job_id: str) -> None:
        """Mark a job as started

        Args:
            job_id: Job ID
        """
        self.update_status(job_id, JobStatus.RUNNING)
        self.update_progress(job_id, 0.0, stage="starting", message="Job started")

    def mark_completed(
        self,
        job_id: str,
        output_path: Optional[Path] = None,
        youtube_url: Optional[str] = None,
    ) -> None:
        """Mark a job as completed

        Args:
            job_id: Job ID
            output_path: Path to generated video
            youtube_url: YouTube URL if uploaded
        """
        self.update_status(job_id, JobStatus.COMPLETED)
        self.update_progress(job_id, 100.0, stage="completed", message="Job completed")

        # Update output info if provided
        if output_path or youtube_url:
            job = self.get_job(job_id)
            if job:
                job.output_path = output_path
                job.youtube_url = youtube_url
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
                self.db.save_batch_job(job)

        logger.info(f"Job {job_id} completed successfully")

    def mark_failed(
        self,
        job_id: str,
        error: Exception,
        stage: Optional[str] = None,
    ) -> bool:
        """Mark a job as failed and check if retry is needed

        Args:
            job_id: Job ID
            error: The exception that caused failure
            stage: Stage where failure occurred

        Returns:
            True if job will be retried, False otherwise
        """
        job = self.get_job(job_id)
        if not job:
            logger.error(f"Cannot mark failed: job {job_id} not found")
            return False

        error_message = f"{type(error).__name__}: {str(error)}"
        if stage:
            error_message = f"[{stage}] {error_message}"

        # Temporarily set status to FAILED for retry check
        job.status = JobStatus.FAILED

        # Check if retry is possible
        should_retry = self.retry_manager.should_retry(job, error)

        if should_retry:
            # Increment retry count and mark as retrying
            new_retry_count = self.db.increment_batch_job_retry(job_id)
            next_retry_time = self.retry_manager.calculate_next_retry_time(job)

            logger.warning(
                f"Job {job_id} will be retried "
                f"(attempt {new_retry_count + 1}/{job.config.max_retries})"
            )

            # Update metadata with retry info
            metadata = {
                "retry_scheduled": next_retry_time.isoformat(),
                "last_error": error_message,
            }
            self.update_progress(
                job_id,
                job.progress,
                stage="retrying",
                message=f"Retry scheduled for {next_retry_time.strftime('%H:%M:%S')}",
            )

            return True
        else:
            # Mark as permanently failed
            self.update_status(job_id, JobStatus.FAILED, error_message=error_message)
            self.update_progress(
                job_id,
                job.progress,
                stage="failed",
                message="Job failed permanently",
            )

            logger.error(f"Job {job_id} failed permanently: {error_message}")

            return False

    def mark_cancelled(self, job_id: str, reason: Optional[str] = None) -> None:
        """Mark a job as cancelled

        Args:
            job_id: Job ID
            reason: Cancellation reason
        """
        message = f"Cancelled: {reason}" if reason else "Cancelled by user"

        self.update_status(job_id, JobStatus.CANCELLED, error_message=message)
        self.update_progress(job_id, 0.0, stage="cancelled", message=message)

        logger.info(f"Job {job_id} cancelled: {message}")

    def delete_job(self, job_id: str) -> bool:
        """Delete a job from tracking

        Args:
            job_id: Job ID

        Returns:
            True if deleted, False if not found
        """
        deleted = self.db.delete_batch_job(job_id)

        if deleted:
            logger.info(f"Job {job_id} deleted")
        else:
            logger.warning(f"Cannot delete: job {job_id} not found")

        return deleted

    def get_summary(self) -> BatchSummary:
        """Get summary statistics for all jobs

        Returns:
            BatchSummary with job counts
        """
        summary_data = self.db.get_batch_summary()

        return BatchSummary(
            total_jobs=summary_data["total_jobs"],
            completed=summary_data["completed"],
            failed=summary_data["failed"],
            running=summary_data["running"],
            pending=summary_data["pending"],
            retrying=summary_data["retrying"],
            cancelled=summary_data["cancelled"],
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics about job execution

        Returns:
            Dict with various metrics
        """
        summary = self.get_summary()

        # Calculate average duration for completed jobs
        completed_jobs = self.get_jobs(status=JobStatus.COMPLETED, limit=1000)
        durations = [
            job.duration_seconds
            for job in completed_jobs
            if job.duration_seconds is not None
        ]

        avg_duration = sum(durations) / len(durations) if durations else 0.0
        min_duration = min(durations) if durations else 0.0
        max_duration = max(durations) if durations else 0.0

        # Calculate retry statistics
        all_jobs = self.get_jobs(limit=1000)
        retry_counts = [job.retry_count for job in all_jobs if job.retry_count > 0]
        avg_retries = sum(retry_counts) / len(retry_counts) if retry_counts else 0.0

        return {
            "summary": summary.to_dict(),
            "duration_stats": {
                "average_seconds": avg_duration,
                "min_seconds": min_duration,
                "max_seconds": max_duration,
                "total_completed": len(completed_jobs),
            },
            "retry_stats": {
                "jobs_with_retries": len(retry_counts),
                "average_retries": avg_retries,
                "total_retries": sum(retry_counts),
            },
            "throughput": {
                "completed_per_hour": self._calculate_throughput(completed_jobs),
            },
        }

    def _calculate_throughput(self, jobs: List[JobResult]) -> float:
        """Calculate jobs completed per hour

        Args:
            jobs: List of completed jobs

        Returns:
            Jobs per hour
        """
        if not jobs:
            return 0.0

        # Get oldest and newest completion times
        completion_times = [
            job.completed_at
            for job in jobs
            if job.completed_at is not None
        ]

        if len(completion_times) < 2:
            return 0.0

        oldest = min(completion_times)
        newest = max(completion_times)

        hours = (newest - oldest).total_seconds() / 3600.0

        if hours == 0:
            return 0.0

        return len(jobs) / hours

    def _job_data_to_result(self, job_data: Dict[str, Any]) -> JobResult:
        """Convert database job data to JobResult

        Args:
            job_data: Job data dict from database

        Returns:
            JobResult object
        """
        config = CSVJobConfig.from_dict(job_data["config"])

        return JobResult(
            job_id=job_data["job_id"],
            status=JobStatus(job_data["status"]),
            config=config,
            created_at=datetime.fromisoformat(job_data["created_at"]),
            started_at=datetime.fromisoformat(job_data["started_at"]) if job_data.get("started_at") else None,
            completed_at=datetime.fromisoformat(job_data["completed_at"]) if job_data.get("completed_at") else None,
            output_path=Path(job_data["output_path"]) if job_data.get("output_path") else None,
            youtube_url=job_data.get("youtube_url"),
            error_message=job_data.get("error_message"),
            retry_count=job_data.get("retry_count", 0),
            progress=job_data.get("progress", 0.0),
            metadata=job_data.get("metadata", {}),
        )

    async def track_job_execution(
        self,
        job_id: str,
        task: Callable[[], Awaitable[dict]],
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> dict:
        """Track execution of a job with automatic progress updates

        Args:
            job_id: Job ID
            task: Async function to execute
            progress_callback: Optional callback for progress updates (progress, message)

        Returns:
            Task result dict

        Raises:
            Exception: If job execution fails
        """
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Mark as started
        self.mark_started(job_id)

        # Notify callback of start
        if progress_callback:
            progress_callback(0.0, "Job started")

        try:
            # Create progress update wrapper
            def update_progress(progress: float, stage: str = "", message: str = ""):
                self.update_progress(job_id, progress, stage, message)
                if progress_callback:
                    progress_callback(progress, message)

            # Execute with retry
            result = await self.retry_manager.execute_with_retry(
                job_result=job,
                task=task,
                on_retry=lambda job, count: self._on_retry_callback(job_id, count),
            )

            # Mark as completed
            output_path = result.get("artifacts", {}).get("video", {}).get("file_path")
            youtube_url = result.get("youtube_url")

            self.mark_completed(
                job_id,
                output_path=Path(output_path) if output_path else None,
                youtube_url=youtube_url,
            )

            return result

        except Exception as error:
            # Mark as failed (will retry if applicable)
            will_retry = self.mark_failed(job_id, error)

            if not will_retry:
                raise

            # If retrying, let the caller handle re-execution
            return {"success": False, "will_retry": True}

    async def _on_retry_callback(self, job_id: str, retry_count: int) -> None:
        """Callback called before each retry

        Args:
            job_id: Job ID
            retry_count: Current retry count
        """
        self.update_progress(
            job_id,
            0.0,
            stage="retrying",
            message=f"Retrying (attempt {retry_count + 1})...",
        )
