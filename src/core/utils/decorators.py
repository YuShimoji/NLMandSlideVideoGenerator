"""
リトライデコレータ
"""
import asyncio
from functools import wraps

from config.settings import settings
from .logger import logger


def retry_on_failure(max_retries: int = None, backoff_factor: float = None, exceptions: tuple = (Exception,)):
    """
    リトライデコレータ

    Args:
        max_retries: 最大リトライ回数
        backoff_factor: バックオフ係数
        exceptions: リトライ対象例外
    """
    max_retries = max_retries or settings.RETRY_SETTINGS.get("max_retries", 3)
    backoff_factor = backoff_factor or settings.RETRY_SETTINGS.get("backoff_factor", 2.0)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        wait_time = backoff_factor ** attempt
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.1f}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed. Last error: {e}")
                        raise last_exception

            # この行は到達しないはず
            raise last_exception

        return wrapper
    return decorator
