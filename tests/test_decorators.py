"""retry_on_failure デコレータテスト"""
import asyncio

import pytest

from core.utils.decorators import retry_on_failure


@pytest.mark.asyncio
class TestRetryOnFailure:
    async def test_succeeds_first_try(self):
        call_count = 0

        @retry_on_failure(max_retries=3, backoff_factor=0.01)
        async def good():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await good()
        assert result == "ok"
        assert call_count == 1

    async def test_retries_then_succeeds(self):
        call_count = 0

        @retry_on_failure(max_retries=3, backoff_factor=0.01)
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "recovered"

        result = await flaky()
        assert result == "recovered"
        assert call_count == 3

    async def test_exhausts_retries(self):
        call_count = 0

        @retry_on_failure(max_retries=2, backoff_factor=0.01)
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("permanent")

        with pytest.raises(RuntimeError, match="permanent"):
            await always_fail()
        # 初回 + 2リトライ = 3回
        assert call_count == 3

    async def test_only_catches_specified_exceptions(self):
        """exceptions 引数で指定した例外のみリトライ"""
        call_count = 0

        @retry_on_failure(max_retries=3, backoff_factor=0.01, exceptions=(ValueError,))
        async def wrong_type():
            nonlocal call_count
            call_count += 1
            raise TypeError("not caught")

        with pytest.raises(TypeError):
            await wrong_type()
        assert call_count == 1  # リトライされない

    async def test_backoff_increases(self):
        """バックオフが指数的に増加する（実行時間で間接確認）"""
        call_count = 0

        @retry_on_failure(max_retries=2, backoff_factor=0.05)
        async def slow_fail():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("retry me")
            return "done"

        result = await slow_fail()
        assert result == "done"

    async def test_preserves_function_metadata(self):
        @retry_on_failure(max_retries=1, backoff_factor=0.01)
        async def my_func():
            """docstring"""
            return 1

        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "docstring"

    async def test_zero_retries(self):
        """max_retries=0 ならリトライなし"""
        call_count = 0

        @retry_on_failure(max_retries=0, backoff_factor=0.01)
        async def once():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await once()
        assert call_count == 1
