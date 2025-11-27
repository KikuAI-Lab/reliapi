"""Tests for retry engine with Retry-After support and key pool fallback."""
import asyncio
import pytest

from reliapi.core.retry import RetryEngine, RetryMatrix


@pytest.mark.asyncio
async def test_retry_with_retry_after_header():
    """Test that Retry-After header is respected."""
    matrix = {
        "429": RetryMatrix(attempts=3, backoff="exp-jitter", base_s=1.0, max_s=60.0),
    }
    engine = RetryEngine(matrix)
    
    call_count = 0
    retry_after_value = 2.0
    
    async def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Simulate 429 with Retry-After header
            error = Exception("Rate limited")
            error.status_code = 429
            error.response = type("Response", (), {"headers": {"Retry-After": str(retry_after_value)}})()
            raise error
        return "success"
    
    def get_retry_after(e):
        if hasattr(e, "response") and hasattr(e.response, "headers"):
            retry_after_str = e.response.headers.get("Retry-After")
            if retry_after_str:
                try:
                    return float(retry_after_str)
                except ValueError:
                    pass
        return None
    
    start_time = asyncio.get_event_loop().time()
    result = await engine.execute(failing_func, get_retry_after=get_retry_after)
    elapsed = asyncio.get_event_loop().time() - start_time
    
    assert result == "success"
    assert call_count == 2
    # Should wait approximately retry_after_value seconds
    assert elapsed >= retry_after_value * 0.9  # Allow 10% margin
    assert elapsed <= retry_after_value * 1.5  # Allow 50% margin for async overhead


@pytest.mark.asyncio
async def test_retry_without_retry_after_uses_backoff():
    """Test that exponential backoff is used when Retry-After is not present."""
    matrix = {
        "429": RetryMatrix(attempts=3, backoff="exp-jitter", base_s=1.0, max_s=60.0),
    }
    engine = RetryEngine(matrix)
    
    call_count = 0
    
    async def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            error = Exception("Rate limited")
            error.status_code = 429
            raise error
        return "success"
    
    start_time = asyncio.get_event_loop().time()
    result = await engine.execute(failing_func)
    elapsed = asyncio.get_event_loop().time() - start_time
    
    assert result == "success"
    assert call_count == 2
    # Should use exponential backoff (base_s * 2^(attempt-1) = 1.0 * 2^0 = 1.0)
    assert elapsed >= 0.9  # At least 0.9 seconds
    assert elapsed <= 2.0  # But less than 2 seconds (with jitter)


@pytest.mark.asyncio
async def test_retry_after_capped_at_max_s():
    """Test that Retry-After value is capped at max_s."""
    matrix = {
        "429": RetryMatrix(attempts=3, backoff="exp-jitter", base_s=1.0, max_s=5.0),
    }
    engine = RetryEngine(matrix)
    
    call_count = 0
    retry_after_value = 100.0  # Very large value
    
    async def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            error = Exception("Rate limited")
            error.status_code = 429
            error.response = type("Response", (), {"headers": {"Retry-After": str(retry_after_value)}})()
            raise error
        return "success"
    
    def get_retry_after(e):
        if hasattr(e, "response") and hasattr(e.response, "headers"):
            retry_after_str = e.response.headers.get("Retry-After")
            if retry_after_str:
                try:
                    return float(retry_after_str)
                except ValueError:
                    pass
        return None
    
    start_time = asyncio.get_event_loop().time()
    result = await engine.execute(failing_func, get_retry_after=get_retry_after)
    elapsed = asyncio.get_event_loop().time() - start_time
    
    assert result == "success"
    # Should be capped at max_s (5.0), not 100.0
    assert elapsed >= 4.5  # At least 4.5 seconds (capped)
    assert elapsed <= 6.0  # But less than 6 seconds


@pytest.mark.asyncio
async def test_retry_max_attempts_enforced():
    """Test that max attempts are enforced."""
    matrix = {
        "429": RetryMatrix(attempts=2, backoff="exp-jitter", base_s=0.1),
    }
    engine = RetryEngine(matrix)
    
    call_count = 0
    
    async def always_failing_func():
        nonlocal call_count
        call_count += 1
        error = Exception("Always fails")
        error.status_code = 429
        raise error
    
    with pytest.raises(Exception):
        await engine.execute(always_failing_func)
    
    # Should attempt: initial + 2 retries = 3 total (but engine limits to 10 total)
    # With attempts=2, should try: initial + 1 retry = 2 total
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_classifies_errors_correctly():
    """Test that errors are classified correctly for retry policy."""
    matrix = {
        "429": RetryMatrix(attempts=2, backoff="exp-jitter", base_s=0.1),
        "5xx": RetryMatrix(attempts=1, backoff="exp-jitter", base_s=0.1),
        "net": RetryMatrix(attempts=1, backoff="exp-jitter", base_s=0.1),
    }
    engine = RetryEngine(matrix)
    
    call_count = 0
    
    async def failing_429_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            error = Exception("Rate limited")
            error.status_code = 429
            raise error
        return "success"
    
    result = await engine.execute(failing_429_func)
    assert result == "success"
    assert call_count == 2  # Initial + 1 retry (attempts=2)

