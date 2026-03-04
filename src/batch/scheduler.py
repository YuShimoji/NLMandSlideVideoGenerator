"""Batch job scheduler with priority queue and concurrency control"""

from __future__ import annotations

import asyncio
import heapq
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable, Awaitable, Dict, Any

from .models import JobStatus, CSVJobConfig, JobResult
from .tracker import JobTracker
from .executor import BatchExecutor
from core.persistence import DatabaseManager
from core.utils.logger import logger


@dataclass(order=True)
class _PriorityJob:
    """Priority queue entry for job scheduling (lower priority value = higher priority)"""
    priority: int
    created_at: datetime = field(compare=True)
    job_id: str = field(compare=False)
    config: CSVJobConfig = field(compare=False)


class BatchScheduler:
    """
    Manages job scheduling with priority queue and concurrency control

    Features:
    - AsyncIO-based parallel execution (Python 3.11 TaskGroup)
    - Hybrid persistence (in-memory PriorityQueue + DB sync)
    - Configurable max_concurrent_jobs limit
    - Auto-recovery from DB on startup
    """

    def __init__(
        self,
        job_tracker: Optional[JobTracker] = None,
        db_manager: Optional[DatabaseManager] = None,
        executor: Optional[BatchExecutor] = None,
        max_concurrent_jobs: int = 3,
    ):
        """Initialize BatchScheduler

        Args:
            job_tracker: Job tracker for status management (creates new if None)
            db_manager: Database manager for persistence (creates new if None)
            executor: Batch executor for running jobs (creates new if None)
            max_concurrent_jobs: Maximum number of jobs to run concurrently
        """
        self.tracker = job_tracker or JobTracker(db_manager=db_manager)
        self.db = db_manager or self.tracker.db
        self.executor = executor or BatchExecutor(
            job_tracker=self.tracker,
            db_manager=self.db,
        )
        self.max_concurrent_jobs = max_concurrent_jobs

        # In-memory priority queue (heapq-based, thread-safe via asyncio)
        self._queue: List[_PriorityJob] = []
        self._running_jobs: Dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()
        self._scheduler_task: Optional[asyncio.Task] = None

        logger.info(
            f"BatchScheduler initialized (max_concurrent_jobs={max_concurrent_jobs})"
        )

    async def start(self):
        """Start the scheduler (loads pending jobs from DB and starts scheduling loop)"""
        if self._scheduler_task is not None:
            logger.warning("Scheduler already running")
            return

        logger.info("Starting BatchScheduler...")

        # Load pending/running jobs from DB
        await self._restore_from_db()

        # Start scheduler loop
        self._shutdown_event.clear()
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

        logger.info("BatchScheduler started")

    async def stop(self, wait_for_completion: bool = False):
        """Stop the scheduler

        Args:
            wait_for_completion: If True, wait for all running jobs to complete
        """
        logger.info(f"Stopping BatchScheduler (wait_for_completion={wait_for_completion})...")

        self._shutdown_event.set()

        if wait_for_completion:
            # Wait for all running jobs
            if self._running_jobs:
                logger.info(f"Waiting for {len(self._running_jobs)} running jobs to complete...")
                await asyncio.gather(*self._running_jobs.values(), return_exceptions=True)
        else:
            # Cancel all running jobs
            for task in self._running_jobs.values():
                task.cancel()

            if self._running_jobs:
                await asyncio.gather(*self._running_jobs.values(), return_exceptions=True)

        # Stop scheduler loop
        if self._scheduler_task:
            await self._scheduler_task
            self._scheduler_task = None

        # Clear running jobs dict
        self._running_jobs.clear()

        logger.info("BatchScheduler stopped")

    async def submit_job(
        self,
        csv_path: Path,
        audio_dir: Path,
        **kwargs
    ) -> JobResult:
        """Submit a new job to the scheduler

        Args:
            csv_path: Path to CSV timeline file
            audio_dir: Directory containing audio files
            **kwargs: Additional CSVJobConfig parameters (priority, max_retries, etc.)

        Returns:
            Created JobResult
        """
        # Create job via tracker (persists to DB)
        job = self.tracker.create_job(csv_path, audio_dir, **kwargs)

        # Add to in-memory priority queue
        priority_job = _PriorityJob(
            priority=-job.config.priority,  # Negative for max-heap behavior
            created_at=job.created_at,
            job_id=job.job_id,
            config=job.config,
        )
        heapq.heappush(self._queue, priority_job)

        logger.info(
            f"Job submitted: {job.job_id} (priority={job.config.priority}, queue_size={len(self._queue)})"
        )

        return job

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancelled, False if not found or already completed
        """
        # Cancel running job
        if job_id in self._running_jobs:
            task = self._running_jobs[job_id]
            task.cancel()
            logger.info(f"Cancelled running job: {job_id}")
            return True

        # Remove from queue (linear search)
        for i, pjob in enumerate(self._queue):
            if pjob.job_id == job_id:
                del self._queue[i]
                heapq.heapify(self._queue)  # Re-heapify after removal

                # Update DB status
                job = self.tracker.get_job(job_id)
                if job:
                    self.tracker.update_status(job_id, JobStatus.CANCELLED)

                logger.info(f"Cancelled pending job: {job_id}")
                return True

        logger.warning(f"Job not found for cancellation: {job_id}")
        return False

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current scheduler status

        Returns:
            Dict with queue_size, running_jobs, max_concurrent
        """
        return {
            "queue_size": len(self._queue),
            "running_jobs": len(self._running_jobs),
            "max_concurrent": self.max_concurrent_jobs,
            "running_job_ids": [str(jid) for jid in self._running_jobs.keys()],
        }

    async def _restore_from_db(self):
        """Restore pending/running jobs from DB on startup"""
        logger.info("Restoring jobs from DB...")

        # Get all jobs and filter by status (DB method only supports single status)
        # So we get all jobs and filter in memory
        all_jobs = self.db.get_batch_jobs(limit=1000)
        db_jobs = [
            job for job in all_jobs
            if job.get("status") in ["pending", "running", "retrying"]
        ]

        for db_job in db_jobs:
            try:
                job = self.tracker.get_job(db_job["job_id"])
                if not job:
                    logger.warning(f"Job not found in tracker: {db_job['job_id']}")
                    continue

                # Reset running jobs to pending (they were interrupted)
                if job.status == JobStatus.RUNNING:
                    self.tracker.update_status(job.job_id, JobStatus.PENDING)
                    job.status = JobStatus.PENDING

                # Add to priority queue
                priority_job = _PriorityJob(
                    priority=-job.config.priority,
                    created_at=job.created_at,
                    job_id=job.job_id,
                    config=job.config,
                )
                heapq.heappush(self._queue, priority_job)

            except Exception as e:
                logger.error(f"Failed to restore job {db_job['job_id']}: {e}")

        logger.info(f"Restored {len(db_jobs)} jobs from DB (queue_size={len(self._queue)})")

    async def _scheduler_loop(self):
        """Main scheduler loop (runs until shutdown)"""
        logger.info("Scheduler loop started")

        while not self._shutdown_event.is_set():
            try:
                # Check if we can start new jobs
                if len(self._running_jobs) < self.max_concurrent_jobs and self._queue:
                    # Pop highest priority job
                    priority_job = heapq.heappop(self._queue)

                    # Start job execution task
                    task = asyncio.create_task(
                        self._execute_job_wrapper(priority_job.job_id, priority_job.config)
                    )
                    self._running_jobs[priority_job.job_id] = task

                    logger.info(
                        f"Started job {priority_job.job_id} "
                        f"(running={len(self._running_jobs)}/{self.max_concurrent_jobs})"
                    )

                # Clean up completed tasks
                completed_jobs = [
                    job_id for job_id, task in self._running_jobs.items()
                    if task.done()
                ]
                for job_id in completed_jobs:
                    del self._running_jobs[job_id]

                # Sleep briefly to avoid busy-waiting
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}", exc_info=True)
                await asyncio.sleep(1.0)  # Back off on error

        logger.info("Scheduler loop stopped")

    async def _execute_job_wrapper(self, job_id: str, config: CSVJobConfig):
        """Wrapper for job execution (handles status updates and errors)"""
        try:
            # Execute job via BatchExecutor
            logger.info(f"Executing job {job_id}...")
            await self.executor.execute_job(job_id, config)
            logger.info(f"Job completed: {job_id}")

        except asyncio.CancelledError:
            # Job was cancelled
            self.tracker.update_status(job_id, JobStatus.CANCELLED)
            logger.info(f"Job cancelled: {job_id}")
            raise

        except Exception as e:
            # Job failed (already handled by executor, but log here too)
            logger.error(f"Job execution wrapper caught error for {job_id}: {e}")
            # Status already updated by executor
