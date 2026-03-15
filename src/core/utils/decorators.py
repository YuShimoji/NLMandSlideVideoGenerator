"""
リトライデコレータ
"""
import asyncio
from functools import wraps
from typing import Optional, Type

from config.settings import settings
from .logger import logger


def retry_on_failure(max_retries: Optional[int] = None, backoff_factor: Optional[float] = None, exceptions: tuple[Type[BaseException], ...] = (Exception,)):
    """
    リトライデコレータ

    Args:
        max_retries: 最大リトライ回数
        backoff_factor: バックオフ係数
        exceptions: リトライ対象例外
    """
    _max_retries: int = max_retries if max_retries is not None else settings.RETRY_SETTINGS.get("max_retries", 3)
    _backoff_factor: float = backoff_factor if backoff_factor is not None else settings.RETRY_SETTINGS.get("backoff_factor", 2.0)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception: Optional[BaseException] = None

            for attempt in range(_max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < _max_retries:
                        wait_time = _backoff_factor ** attempt
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.1f}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {_max_retries + 1} attempts failed. Last error: {e}")
                        raise last_exception

        return wrapper
    return decorator
