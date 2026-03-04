"""Batch job executor - integrates with ModularVideoPipeline"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from .models import JobStatus, CSVJobConfig, JobResult
from .tracker import JobTracker
from .retry_manager import RetryManager
from core.pipeline import ModularVideoPipeline, build_default_pipeline
from core.csv_pipeline_runner import run_csv_timeline
from core.persistence import DatabaseManager
from core.utils.logger import logger
from core.exceptions import PipelineError


class BatchExecutor:
    """
    Executes batch jobs by integrating with ModularVideoPipeline

    Features:
    - Integrates with run_csv_timeline for CSV-based video generation
    - Handles errors with RetryManager integration
    - Reports progress via JobTracker
    - Supports YMM4 export and YouTube upload
    """

    def __init__(
        self,
        job_tracker: Optional[JobTracker] = None,
        db_manager: Optional[DatabaseManager] = None,
        pipeline: Optional[ModularVideoPipeline] = None,
    ):
        """Initialize BatchExecutor

        Args:
            job_tracker: Job tracker for status management (creates new if None)
            db_manager: Database manager for persistence (creates new if None)
            pipeline: Pipeline instance for video generation (creates default if None)
        """
        self.tracker = job_tracker or JobTracker(db_manager=db_manager)
        self.db = db_manager or self.tracker.db
        self.pipeline = pipeline or build_default_pipeline()

        logger.info("BatchExecutor initialized")

    async def execute_job(
        self,
        job_id: str,
        config: Optional[CSVJobConfig] = None,
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
    ) -> JobResult:
        """Execute a single batch job

        Args:
            job_id: Job ID to execute
            config: Job configuration (loads from tracker if None)
            progress_callback: Optional callback for progress updates

        Returns:
            Updated JobResult

        Raises:
            PipelineError: If job execution fails
        """
        # Load job if config not provided
        if config is None:
            job = self.tracker.get_job(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")
            config = job.config
        else:
            job = self.tracker.get_job(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

        logger.info(f"Executing job {job_id}: {config.topic or config.csv_path.name}")

        # Update status to running
        self.tracker.update_status(job_id, JobStatus.RUNNING)

        try:
            # Execute pipeline
            result = await self._run_pipeline(job_id, config, progress_callback)

            # Update job with results
            output_path = Path(result["video_path"]) if result.get("video_path") else None
            youtube_url = result.get("youtube_url")
            self.tracker.mark_completed(job_id, output_path=output_path, youtube_url=youtube_url)

            logger.info(f"Job completed successfully: {job_id}")

            # Return updated job result
            return self.tracker.get_job(job_id)

        except Exception as e:
            # Check if should retry using mark_failed (which returns True if retry scheduled)
            will_retry = self.tracker.mark_failed(job_id, e)

            raise PipelineError(
                message=f"Job execution failed: {e}",
                stage="batch_execution",
                recoverable=will_retry,
            ) from e

    async def _run_pipeline(
        self,
        job_id: str,
        config: CSVJobConfig,
        progress_callback: Optional[Callable[[str, float, str], None]],
    ) -> Dict[str, Any]:
        """Run the video generation pipeline

        Args:
            job_id: Job ID
            config: Job configuration
            progress_callback: Progress callback

        Returns:
            Pipeline execution results
        """
        # Determine editing backend based on config
        editing_backend = None
        if config.export_ymm4:
            from core.editing.ymm4_backend import YMM4EditingBackend
            editing_backend = YMM4EditingBackend(package_path=config.package_path)
            logger.info(f"Using YMM4 backend for job {job_id}")

        # Build stage modes
        stage_modes = {}
        if editing_backend:
            stage_modes["stage3"] = "ymm4"

        # Create progress wrapper
        def wrapped_progress(stage: str, progress: float, message: str):
            """Wraps progress callback to update JobTracker"""
            # Update tracker
            self.tracker.update_progress(job_id, progress * 100)  # Convert to percentage

            # Call user callback if provided
            if progress_callback:
                progress_callback(stage, progress, message)

        # Execute run_csv_timeline
        logger.info(
            f"Running CSV pipeline: csv={config.csv_path}, audio_dir={config.audio_dir}"
        )

        result = await run_csv_timeline(
            csv_path=config.csv_path,
            audio_dir=config.audio_dir,
            slide_generator=self.pipeline.slide_generator,
            video_composer=self.pipeline.video_composer,
            metadata_generator=self.pipeline.metadata_generator,
            uploader=self.pipeline.uploader,
            timeline_planner=self.pipeline.timeline_planner,
            editing_backend=editing_backend,
            platform_adapter=self.pipeline.platform_adapter,
            publishing_queue=self.pipeline.publishing_queue,
            stage_modes=stage_modes,
            topic=config.topic,
            quality=config.video_quality,
            private_upload=not config.public_upload,
            upload=config.upload,
            user_preferences={
                "max_chars_per_slide": config.max_chars_per_slide,
                "strict_alignment": config.strict_alignment,
            },
            progress_callback=wrapped_progress,
            job_id=job_id,
        )

        return result

    async def execute_job_with_retry(
        self,
        job_id: str,
        config: Optional[CSVJobConfig] = None,
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
    ) -> JobResult:
        """Execute a job with automatic retry on failure

        Args:
            job_id: Job ID to execute
            config: Job configuration (loads from tracker if None)
            progress_callback: Optional callback for progress updates

        Returns:
            Final JobResult (completed or failed)
        """
        # Load job
        job = self.tracker.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        config = config or job.config

        while True:
            try:
                return await self.execute_job(job_id, config, progress_callback)

            except PipelineError as e:
                if not e.recoverable:
                    # Non-recoverable error, stop retrying
                    logger.error(f"Non-recoverable error for job {job_id}: {e}")
                    raise

                # Check retry count
                job = self.tracker.get_job(job_id)
                if job.retry_count >= config.max_retries:
                    logger.error(
                        f"Max retries exceeded for job {job_id} "
                        f"({job.retry_count}/{config.max_retries})"
                    )
                    self.tracker.mark_failed(job_id, str(e))
                    raise

                # Wait for retry delay
                delay = self.tracker.retry_manager.policy.calculate_delay(job.retry_count)
                logger.info(f"Retrying job {job_id} in {delay:.1f}s...")
                await asyncio.sleep(delay)

                # Update retry count and continue loop
                self.tracker.db.increment_batch_job_retry(job_id)

            except Exception as e:
                # Unexpected error
                logger.error(f"Unexpected error for job {job_id}: {e}", exc_info=True)
                self.tracker.mark_failed(job_id, str(e))
                raise PipelineError(
                    message=f"Unexpected job execution error: {e}",
                    stage="batch_execution",
                    recoverable=False,
                ) from e
