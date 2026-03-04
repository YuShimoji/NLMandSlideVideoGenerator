"""Retry management for batch jobs with exponential backoff"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable

from .models import JobStatus, JobResult
from core.utils.logger import logger


@dataclass
class RetryPolicy:
    """Retry policy configuration"""

    max_retries: int = 3
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 60.0
    exponential_factor: float = 2.0
    jitter: bool = True

    def calculate_delay(self, retry_count: int) -> float:
        """Calculate delay for next retry using exponential backoff

        Args:
            retry_count: Current retry count (0-indexed)

        Returns:
            Delay in seconds
        """
        if retry_count < 0:
            return 0.0

        # Exponential backoff: base_delay * (factor ^ retry_count)
        delay = self.base_delay_seconds * (self.exponential_factor ** retry_count)

        # Cap at max delay
        delay = min(delay, self.max_delay_seconds)

        # Add jitter to prevent thundering herd
        if self.jitter:
            import random
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0.0, delay)


class RetryManager:
    """Manages retry logic for failed batch jobs"""

    def __init__(self, policy: Optional[RetryPolicy] = None):
        """Initialize RetryManager

        Args:
            policy: Retry policy to use (defaults to standard policy)
        """
        self.policy = policy or RetryPolicy()
        logger.info(
            f"RetryManager initialized with policy: "
            f"max_retries={self.policy.max_retries}, "
            f"base_delay={self.policy.base_delay_seconds}s"
        )

    def should_retry(self, job_result: JobResult, error: Optional[Exception] = None) -> bool:
        """Determine if a job should be retried

        Args:
            job_result: The job result to check
            error: The exception that caused failure (optional)

        Returns:
            True if the job should be retried
        """
        # Check if retry count exceeded
        if job_result.retry_count >= job_result.config.max_retries:
            logger.info(
                f"Job {job_result.job_id} exceeded max retries "
                f"({job_result.retry_count}/{job_result.config.max_retries})"
            )
            return False

        # Only retry failed or retrying jobs
        if job_result.status not in (JobStatus.FAILED, JobStatus.RETRYING):
            return False

        # Check if error is recoverable
        if error is not None:
            if not self._is_recoverable_error(error):
                logger.warning(
                    f"Job {job_result.job_id} has non-recoverable error: "
                    f"{type(error).__name__}: {str(error)}"
                )
                return False

        logger.info(
            f"Job {job_result.job_id} eligible for retry "
            f"(attempt {job_result.retry_count + 1}/{job_result.config.max_retries})"
        )
        return True

    def _is_recoverable_error(self, error: Exception) -> bool:
        """Check if an error is recoverable

        Args:
            error: The exception to check

        Returns:
            True if the error is recoverable
        """
        # Import exceptions locally to avoid circular imports
        from core.exceptions import (
            PipelineError,
            AudioGenerationError,
            SlideGenerationError,
            VideoCompositionError,
        )

        # Non-recoverable error types
        non_recoverable_types = (
            ValueError,  # Invalid configuration
            TypeError,  # Type errors
            FileNotFoundError,  # Missing required files
            PermissionError,  # Permission issues
        )

        if isinstance(error, non_recoverable_types):
            return False

        # Check PipelineError's recoverable flag
        if isinstance(error, PipelineError):
            return getattr(error, 'recoverable', True)

        # Domain-specific errors are generally recoverable
        if isinstance(error, (AudioGenerationError, SlideGenerationError, VideoCompositionError)):
            return True

        # Network/IO errors are typically recoverable
        if isinstance(error, (ConnectionError, TimeoutError, IOError, OSError)):
            return True

        # Default to recoverable for unknown errors
        return True

    def calculate_next_retry_time(self, job_result: JobResult) -> datetime:
        """Calculate when the job should be retried next

        Args:
            job_result: The job result

        Returns:
            Datetime for next retry
        """
        delay = self.policy.calculate_delay(job_result.retry_count)
        next_retry = datetime.now() + timedelta(seconds=delay)

        logger.info(
            f"Job {job_result.job_id} scheduled for retry in {delay:.1f}s "
            f"(at {next_retry.strftime('%H:%M:%S')})"
        )

        return next_retry

    async def execute_with_retry(
        self,
        job_result: JobResult,
        task: Callable[[], Awaitable[dict]],
        on_retry: Optional[Callable[[JobResult, int], Awaitable[None]]] = None,
    ) -> dict:
        """Execute a task with automatic retry on failure

        Args:
            job_result: The job to execute
            task: Async function to execute
            on_retry: Optional callback called before each retry

        Returns:
            Task result dict

        Raises:
            Exception: If all retries are exhausted
        """
        last_error: Optional[Exception] = None
        retry_count = 0

        while retry_count <= self.policy.max_retries:
            try:
                logger.info(
                    f"Executing job {job_result.job_id} "
                    f"(attempt {retry_count + 1}/{self.policy.max_retries + 1})"
                )

                result = await task()

                if retry_count > 0:
                    logger.info(
                        f"Job {job_result.job_id} succeeded after {retry_count} retries"
                    )

                return result

            except Exception as error:
                last_error = error
                retry_count += 1

                logger.warning(
                    f"Job {job_result.job_id} failed (attempt {retry_count}): "
                    f"{type(error).__name__}: {str(error)}"
                )

                # Check if we should retry
                if retry_count > self.policy.max_retries:
                    logger.error(
                        f"Job {job_result.job_id} exhausted all retries "
                        f"({retry_count}/{self.policy.max_retries})"
                    )
                    break

                if not self._is_recoverable_error(error):
                    logger.error(
                        f"Job {job_result.job_id} encountered non-recoverable error"
                    )
                    break

                # Calculate delay and wait
                delay = self.policy.calculate_delay(retry_count - 1)
                logger.info(
                    f"Retrying job {job_result.job_id} in {delay:.1f}s..."
                )

                # Call retry callback if provided
                if on_retry:
                    try:
                        await on_retry(job_result, retry_count)
                    except Exception as callback_error:
                        logger.warning(
                            f"Retry callback failed for {job_result.job_id}: "
                            f"{callback_error}"
                        )

                await asyncio.sleep(delay)

        # All retries exhausted
        if last_error:
            logger.error(
                f"Job {job_result.job_id} failed permanently: "
                f"{type(last_error).__name__}: {str(last_error)}"
            )
            raise last_error
        else:
            raise RuntimeError(f"Job {job_result.job_id} failed without error")

    def get_retry_stats(self, job_result: JobResult) -> dict:
        """Get retry statistics for a job

        Args:
            job_result: The job result

        Returns:
            Dict with retry statistics
        """
        remaining_retries = max(0, job_result.config.max_retries - job_result.retry_count)
        next_delay = self.policy.calculate_delay(job_result.retry_count)

        return {
            "retry_count": job_result.retry_count,
            "max_retries": job_result.config.max_retries,
            "remaining_retries": remaining_retries,
            "next_delay_seconds": next_delay if remaining_retries > 0 else None,
            "is_retriable": self.should_retry(job_result),
        }

    def reset_retry_count(self, job_result: JobResult) -> None:
        """Reset retry count for a job (used when job is manually resubmitted)

        Args:
            job_result: The job result to reset
        """
        logger.info(f"Resetting retry count for job {job_result.job_id}")
        job_result.retry_count = 0
        job_result.error_message = None
