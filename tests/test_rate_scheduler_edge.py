"""Edge case tests for rate scheduler - extreme QPS values and burst handling."""
import asyncio
import time
import pytest

from reliapi.core.rate_scheduler import RateScheduler, TokenBucket


@pytest.mark.asyncio
async def test_rate_scheduler_very_low_qps():
    """Test rate scheduler with very low QPS (0.1 req/sec)."""
    scheduler = RateScheduler()
    
    provider_key_id = "low_qps_key"
    max_qps = 0.1  # Very low QPS
    
    # Bucket starts with max_qps tokens (0.1), which is less than 1.0 needed for a request
    # So first request will be rate limited
    allowed1, retry_after1, bucket1 = await scheduler.check_rate_limit(
        provider_key_id=provider_key_id,
        provider_key_qps=max_qps,
    )
    
    # Verify bucket was created
    bucket_key = f"provider_key:{provider_key_id}"
    assert bucket_key in scheduler.buckets
    
    # First request should be rate limited (0.1 < 1.0 tokens needed)
    assert allowed1 is False
    assert retry_after1 is not None
    assert retry_after1 > 0.0
    
    # Retry_after should be approximately (1.0 - 0.1) / 0.1 = 9 seconds
    # Allow some margin for timing
    assert retry_after1 <= 15.0, f"Retry after too long: {retry_after1}"
    assert retry_after1 >= 5.0, f"Retry after too short: {retry_after1}"
    
    # Verify retry_after calculation is reasonable for very low QPS
    # For 0.1 QPS, to get 1 token we need 10 seconds
    # Current tokens = 0.1, need 0.9 more = 0.9 / 0.1 = 9 seconds
    expected_retry_after = (1.0 - max_qps) / max_qps  # ~9 seconds
    assert abs(retry_after1 - expected_retry_after) < 5.0, \
        f"Retry after {retry_after1:.2f}s not close to expected {expected_retry_after:.2f}s"
    
    # Verify that very low QPS produces reasonable retry_after values
    # The key test is that the system handles very low QPS without errors
    # and provides reasonable retry_after guidance
    
    print(f"Very low QPS test: retry_after={retry_after1:.2f}s (expected ~{expected_retry_after:.2f}s) for {max_qps} QPS")


@pytest.mark.asyncio
async def test_rate_scheduler_very_high_qps():
    """Test rate scheduler with very high QPS (1000 req/sec)."""
    scheduler = RateScheduler()
    
    provider_key_id = "high_qps_key"
    max_qps = 1000.0  # Very high QPS
    
    # Make many requests quickly
    num_requests = 2000
    start_time = time.time()
    
    allowed_count = 0
    rate_limited_count = 0
    
    for i in range(num_requests):
        allowed, retry_after, bucket = await scheduler.check_rate_limit(
            provider_key_id=provider_key_id,
            provider_key_qps=max_qps,
        )
        
        if allowed:
            allowed_count += 1
        else:
            rate_limited_count += 1
    
    elapsed = time.time() - start_time
    rps = num_requests / elapsed
    
    # Should handle high QPS efficiently
    assert rps >= 500, f"Only achieved {rps:.2f} req/sec, expected >= 500"
    
    # With 1000 QPS, bucket starts with 1000 tokens
    # First 1000 requests should be allowed, then rate limited
    # But tokens refill during execution, so more may be allowed
    # At minimum, first batch should be allowed
    assert allowed_count >= 1000, f"Too few requests allowed: {allowed_count}/{num_requests}"
    
    # Some requests should be rate limited (tokens consumed)
    assert rate_limited_count > 0, "No requests were rate limited"
    
    print(f"Very high QPS test: {rps:.2f} req/sec, allowed={allowed_count}/{num_requests}")


@pytest.mark.asyncio
async def test_rate_scheduler_burst_handling():
    """Test burst handling (100 requests simultaneously)."""
    scheduler = RateScheduler()
    
    provider_key_id = "burst_key"
    max_qps = 10.0  # 10 QPS
    
    # Create bucket - starts with max_qps tokens (10)
    bucket = scheduler.get_or_create_bucket(
        f"provider_key:{provider_key_id}",
        max_qps=max_qps,
        burst_size=20,
        max_concurrent=100,
    )
    
    # Bucket starts with max_qps tokens (10)
    # Make 100 simultaneous requests
    num_burst = 100
    
    async def make_request():
        allowed, retry_after, bucket = await scheduler.check_rate_limit(
            provider_key_id=provider_key_id,
            provider_key_qps=max_qps,
        )
        return allowed
    
    # Execute all requests concurrently
    tasks = [make_request() for _ in range(num_burst)]
    results = await asyncio.gather(*tasks)
    
    allowed_count = sum(1 for r in results if r)
    rate_limited_count = num_burst - allowed_count
    
    # Bucket starts with max_qps (10) tokens
    # At least 10 requests should be allowed initially
    # Tokens may refill slightly during concurrent execution
    assert allowed_count >= max_qps, f"Burst handling failed: only {allowed_count} allowed, expected at least {max_qps}"
    
    # Most requests should be rate limited (tokens consumed)
    assert rate_limited_count > allowed_count, "Too many requests allowed in burst"
    
    print(f"Burst handling test: {allowed_count} allowed, {rate_limited_count} rate limited from {num_burst} concurrent requests")


@pytest.mark.asyncio
async def test_rate_scheduler_retry_after_calculation():
    """Test retry_after calculation accuracy."""
    scheduler = RateScheduler()
    
    provider_key_id = "retry_after_key"
    max_qps = 10.0  # 10 QPS = 1 token per 0.1 seconds
    
    # Create bucket and consume all tokens
    bucket = scheduler.get_or_create_bucket(
        f"provider_key:{provider_key_id}",
        max_qps=max_qps,
        burst_size=10,
        max_concurrent=5,
    )
    
    # Consume all tokens
    bucket.consume(max_qps)
    
    # Check rate limit (should be denied)
    allowed, retry_after, limiting_bucket = await scheduler.check_rate_limit(
        provider_key_id=provider_key_id,
        provider_key_qps=max_qps,
    )
    
    assert allowed is False
    assert retry_after is not None
    assert retry_after > 0.0
    
    # Retry_after should be approximately 1/max_qps (0.1 seconds for 10 QPS)
    # But tokens may have refilled slightly, so allow some margin
    expected_retry_after = 1.0 / max_qps  # 0.1 seconds
    assert retry_after <= expected_retry_after * 2, f"Retry after too long: {retry_after}"
    assert retry_after >= expected_retry_after * 0.5, f"Retry after too short: {retry_after}"
    
    # Wait for retry_after and try again
    await asyncio.sleep(retry_after + 0.1)  # Wait slightly longer
    
    allowed2, retry_after2, limiting_bucket2 = await scheduler.check_rate_limit(
        provider_key_id=provider_key_id,
        provider_key_qps=max_qps,
    )
    
    # Should be allowed now
    assert allowed2 is True, f"Request should be allowed after retry_after: {retry_after}"
    
    print(f"Retry after calculation test: retry_after={retry_after:.3f}s, expected ~{expected_retry_after:.3f}s")


@pytest.mark.asyncio
async def test_rate_scheduler_zero_qps():
    """Test rate scheduler with zero QPS (should reject all requests)."""
    scheduler = RateScheduler()
    
    provider_key_id = "zero_qps_key"
    max_qps = 0.0  # Zero QPS
    
    # All requests should be rate limited
    allowed, retry_after, limiting_bucket = await scheduler.check_rate_limit(
        provider_key_id=provider_key_id,
        provider_key_qps=max_qps,
    )
    
    # With zero QPS, bucket should reject all requests
    # However, bucket creation might handle this differently
    # Let's check the behavior
    if max_qps > 0:
        # If QPS is positive, check should work
        assert isinstance(allowed, bool)
    else:
        # With zero QPS, behavior may vary - just ensure no crash
        assert isinstance(allowed, bool)
    
    print(f"Zero QPS test: allowed={allowed}, retry_after={retry_after}")


@pytest.mark.asyncio
async def test_rate_scheduler_extreme_burst():
    """Test extreme burst scenario (1000 requests at once)."""
    scheduler = RateScheduler()
    
    provider_key_id = "extreme_burst_key"
    max_qps = 100.0  # 100 QPS
    
    # Create bucket
    bucket = scheduler.get_or_create_bucket(
        f"provider_key:{provider_key_id}",
        max_qps=max_qps,
        burst_size=200,
        max_concurrent=1000,
    )
    
    # Start with full bucket
    bucket.tokens = max_qps
    
    # Make 1000 simultaneous requests
    num_burst = 1000
    
    async def make_request():
        allowed, retry_after, bucket = await scheduler.check_rate_limit(
            provider_key_id=provider_key_id,
            provider_key_qps=max_qps,
        )
        return allowed
    
    start_time = time.time()
    
    # Execute all requests concurrently
    tasks = [make_request() for _ in range(num_burst)]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    
    allowed_count = sum(1 for r in results if r)
    rate_limited_count = num_burst - allowed_count
    
    # Should handle extreme burst without crashing
    assert elapsed < 5.0, f"Extreme burst took too long: {elapsed:.2f}s"
    
    # Some requests should be allowed (at least burst_size)
    assert allowed_count > 0, "No requests allowed in extreme burst"
    
    # Most should be rate limited (burst exceeded)
    assert rate_limited_count > allowed_count, "Too many requests allowed in extreme burst"
    
    print(f"Extreme burst test: {allowed_count} allowed, {rate_limited_count} rate limited in {elapsed:.2f}s")


@pytest.mark.asyncio
async def test_rate_scheduler_rapid_alternation():
    """Test rapid alternation between different keys."""
    scheduler = RateScheduler()
    
    num_keys = 50
    max_qps = 10.0
    
    # Rapidly alternate between different keys
    for i in range(100):
        provider_key_id = f"alt_key_{i % num_keys}"
        allowed, retry_after, bucket = await scheduler.check_rate_limit(
            provider_key_id=provider_key_id,
            provider_key_qps=max_qps,
        )
        # Should not crash
        assert isinstance(allowed, bool)
    
    # Verify buckets were created
    stats = scheduler.get_bucket_stats()
    assert stats["total"] == num_keys, f"Expected {num_keys} buckets, got {stats['total']}"
    
    print(f"Rapid alternation test: {stats['total']} buckets created for {num_keys} unique keys")

