"""Tests for rate scheduler with token bucket algorithm."""
import asyncio
import time
import pytest

from reliapi.core.rate_scheduler import RateScheduler, TokenBucket


def test_token_bucket_refill():
    """Test that token bucket refills over time."""
    bucket = TokenBucket(
        max_qps=10.0,
        burst_size=5,
        tokens=0.0,
        last_refill=time.time(),
        max_concurrent=2,
    )
    
    # Consume all tokens
    assert bucket.consume(10.0) is False  # Not enough tokens
    
    # Wait and refill
    time.sleep(0.2)  # 200ms
    bucket.refill(time.time())
    
    # Should have ~2 tokens (0.2s * 10 qps)
    assert bucket.tokens > 1.0
    assert bucket.tokens <= 2.5  # Allow some margin


def test_token_bucket_consume():
    """Test token consumption."""
    bucket = TokenBucket(
        max_qps=10.0,
        burst_size=5,
        tokens=5.0,
        last_refill=time.time(),
        max_concurrent=2,
    )
    
    # Consume tokens
    assert bucket.consume(3.0) is True
    # Use approximate comparison due to refill during consume
    assert abs(bucket.tokens - 2.0) < 0.1
    
    # Store tokens before failed consume
    tokens_before = bucket.tokens
    
    # Try to consume more than available
    assert bucket.consume(5.0) is False
    # Tokens might increase slightly due to refill but no consumption
    assert bucket.tokens >= tokens_before


def test_token_bucket_get_retry_after():
    """Test retry_after estimation."""
    bucket = TokenBucket(
        max_qps=10.0,
        burst_size=5,
        tokens=0.5,
        last_refill=time.time(),
        max_concurrent=2,
    )
    
    retry_after = bucket.get_retry_after()
    # Need 0.5 tokens, at 10 qps = 0.05 seconds
    assert retry_after > 0.0
    assert retry_after < 0.1


@pytest.mark.asyncio
async def test_rate_scheduler_check_rate_limit_allowed():
    """Test that rate scheduler allows requests within limits."""
    scheduler = RateScheduler()
    
    allowed, retry_after, bucket = await scheduler.check_rate_limit(
        provider_key_id="key1",
        provider_key_qps=10.0,
    )
    
    assert allowed is True
    assert retry_after is None
    assert bucket is None


@pytest.mark.asyncio
async def test_rate_scheduler_check_rate_limit_exceeded():
    """Test that rate scheduler rejects requests exceeding limits."""
    scheduler = RateScheduler()
    
    # Create bucket with low QPS
    bucket = scheduler.get_or_create_bucket("provider_key:key1", max_qps=1.0, burst_size=2, max_concurrent=1)
    
    # Consume all tokens
    bucket.consume(1.0)
    
    # Next request should be rate limited
    allowed, retry_after, limiting_bucket = await scheduler.check_rate_limit(
        provider_key_id="key1",
        provider_key_qps=1.0,
    )
    
    assert allowed is False
    assert retry_after is not None
    assert retry_after > 0.0
    assert limiting_bucket == "provider_key"


@pytest.mark.asyncio
async def test_rate_scheduler_multiple_buckets():
    """Test that all buckets are checked."""
    scheduler = RateScheduler()
    
    # Set up buckets
    key_bucket = scheduler.get_or_create_bucket("provider_key:key1", max_qps=10.0, burst_size=5, max_concurrent=2)
    tenant_bucket = scheduler.get_or_create_bucket("tenant:tenant1", max_qps=5.0, burst_size=3, max_concurrent=2)
    
    # Consume from tenant bucket
    tenant_bucket.consume(5.0)
    
    # Check should fail on tenant bucket
    allowed, retry_after, limiting_bucket = await scheduler.check_rate_limit(
        provider_key_id="key1",
        tenant="tenant1",
        provider_key_qps=10.0,
        tenant_qps=5.0,
    )
    
    assert allowed is False
    assert limiting_bucket == "tenant"


@pytest.mark.asyncio
async def test_rate_scheduler_concurrent_limiting():
    """Test concurrent request limiting with semaphore."""
    scheduler = RateScheduler()
    
    bucket = scheduler.get_or_create_bucket("provider_key:key1", max_qps=10.0, burst_size=5, max_concurrent=2)
    
    # Acquire 2 slots (max_concurrent)
    buckets1 = await scheduler.acquire_concurrent_slot(provider_key_id="key1")
    buckets2 = await scheduler.acquire_concurrent_slot(provider_key_id="key1")
    
    # Third acquisition should wait (but we'll test it doesn't block forever)
    acquired = False
    
    async def try_acquire():
        nonlocal acquired
        buckets3 = await scheduler.acquire_concurrent_slot(provider_key_id="key1")
        acquired = True
        scheduler.release_concurrent_slots(buckets3)
    
    # Start third acquisition
    task = asyncio.create_task(try_acquire())
    
    # Release first two
    await asyncio.sleep(0.1)
    scheduler.release_concurrent_slots(buckets1)
    scheduler.release_concurrent_slots(buckets2)
    
    # Wait for third to acquire
    await asyncio.wait_for(task, timeout=1.0)
    assert acquired is True


@pytest.mark.asyncio
async def test_rate_scheduler_no_limits():
    """Test that scheduler allows requests when no limits configured."""
    scheduler = RateScheduler()
    
    allowed, retry_after, bucket = await scheduler.check_rate_limit()
    
    assert allowed is True
    assert retry_after is None
    assert bucket is None

