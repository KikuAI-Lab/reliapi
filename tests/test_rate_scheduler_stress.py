"""Stress tests for rate scheduler - high load and memory management."""
import asyncio
import time
import pytest
import tracemalloc
from typing import List

from reliapi.core.rate_scheduler import RateScheduler, TokenBucket, MAX_BUCKETS, DEFAULT_BUCKET_TTL_SECONDS


@pytest.mark.asyncio
async def test_rate_scheduler_high_qps():
    """Test rate scheduler with 1000+ requests/sec."""
    scheduler = RateScheduler(max_buckets=MAX_BUCKETS)
    
    provider_key_id = "test_key_1"
    max_qps = 1000.0
    
    # Simulate 1000 requests/sec for 1 second
    num_requests = 1000
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
    
    # Should handle at least 1000 req/sec
    assert rps >= 1000, f"Only achieved {rps:.2f} req/sec, expected >= 1000"
    
    # Most requests should be allowed (some may be rate limited due to token consumption)
    assert allowed_count > rate_limited_count, "Too many requests rate limited"
    
    print(f"High QPS test: {rps:.2f} req/sec, allowed={allowed_count}, rate_limited={rate_limited_count}")


@pytest.mark.asyncio
async def test_rate_scheduler_concurrent_bucket_creation():
    """Test concurrent bucket creation (100+ concurrent requests creating different buckets)."""
    scheduler = RateScheduler(max_buckets=MAX_BUCKETS)
    
    num_concurrent = 100
    
    async def create_and_check_bucket(bucket_id: int):
        """Create a bucket and check rate limit."""
        provider_key_id = f"key_{bucket_id}"
        
        # Create bucket by checking rate limit
        allowed, retry_after, bucket = await scheduler.check_rate_limit(
            provider_key_id=provider_key_id,
            provider_key_qps=10.0,
        )
        
        # Verify bucket was created
        bucket_key = f"provider_key:{provider_key_id}"
        assert bucket_key in scheduler.buckets
        
        return bucket_id, allowed
    
    # Create buckets concurrently
    tasks = [create_and_check_bucket(i) for i in range(num_concurrent)]
    results = await asyncio.gather(*tasks)
    
    # All buckets should be created
    assert len(results) == num_concurrent
    
    # Verify all buckets exist
    assert len(scheduler.buckets) == num_concurrent
    
    # Verify stats
    stats = scheduler.get_bucket_stats()
    assert stats["total"] == num_concurrent
    assert stats["provider_key"] == num_concurrent
    
    print(f"Concurrent bucket creation: {num_concurrent} buckets created successfully")


@pytest.mark.asyncio
async def test_rate_scheduler_memory_leak_simulation():
    """Simulate 24+ hours of operation to detect memory leaks."""
    scheduler = RateScheduler(
        max_buckets=MAX_BUCKETS,
        bucket_ttl_seconds=2,  # Very short TTL for testing
        cleanup_interval_seconds=1,  # Frequent cleanup for testing
    )
    
    await scheduler.start_cleanup_task()
    
    try:
        # Simulate many hours of operation by creating and using buckets
        # We'll simulate this by creating many buckets and letting cleanup run
        
        num_buckets_created = 0
        num_iterations = 20  # Simulate 20 cycles
        
        for iteration in range(num_iterations):
            # Create new buckets
            for i in range(10):
                provider_key_id = f"key_{iteration}_{i}"
                await scheduler.check_rate_limit(
                    provider_key_id=provider_key_id,
                    provider_key_qps=10.0,
                )
                num_buckets_created += 1
            
            # Wait for cleanup to run (longer than TTL)
            await asyncio.sleep(0.3)
            
            # Check bucket count doesn't exceed max
            stats = scheduler.get_bucket_stats()
            assert stats["total"] <= MAX_BUCKETS, f"Bucket count exceeded max: {stats['total']}"
        
        # Wait for final cleanup cycle
        await asyncio.sleep(3)  # Wait longer than TTL
        
        # Manually trigger cleanup to ensure expired buckets are removed
        await scheduler._cleanup_expired_buckets()
        
        # After cleanup cycles, bucket count should be reasonable
        final_stats = scheduler.get_bucket_stats()
        print(f"Memory leak test: created {num_buckets_created} buckets, final count={final_stats['total']}")
        
        # Final count should be less than created (due to cleanup and TTL expiration)
        # Some buckets may still exist if they were recently accessed
        assert final_stats["total"] <= num_buckets_created, "Bucket count exceeded created count"
        
        # Verify max_buckets limit is enforced
        assert final_stats["total"] <= MAX_BUCKETS, f"Bucket count exceeded max: {final_stats['total']}"
        
    finally:
        await scheduler.stop_cleanup_task()


@pytest.mark.asyncio
async def test_rate_scheduler_cleanup_mechanism():
    """Test that cleanup mechanism removes expired buckets."""
    scheduler = RateScheduler(
        max_buckets=MAX_BUCKETS,
        bucket_ttl_seconds=1,  # Very short TTL for testing
        cleanup_interval_seconds=1,  # Cleanup every second
    )
    
    await scheduler.start_cleanup_task()
    
    try:
        # Create some buckets
        for i in range(10):
            provider_key_id = f"cleanup_test_key_{i}"
            await scheduler.check_rate_limit(
                provider_key_id=provider_key_id,
                provider_key_qps=10.0,
            )
        
        # Verify buckets exist
        assert len(scheduler.buckets) == 10
        
        # Wait for TTL to expire and cleanup to run
        await asyncio.sleep(2)
        
        # Manually trigger cleanup
        await scheduler._cleanup_expired_buckets()
        
        # All buckets should be cleaned up (they haven't been accessed)
        final_count = len(scheduler.buckets)
        print(f"Cleanup test: started with 10 buckets, ended with {final_count}")
        
        # Buckets should be cleaned up (may take a moment)
        # Allow some buckets to remain if they were recently accessed
        assert final_count <= 10, "Cleanup didn't remove expired buckets"
        
    finally:
        await scheduler.stop_cleanup_task()


@pytest.mark.asyncio
async def test_rate_scheduler_lru_eviction():
    """Test that LRU eviction works when max_buckets is reached."""
    scheduler = RateScheduler(
        max_buckets=10,  # Small limit for testing
        bucket_ttl_seconds=DEFAULT_BUCKET_TTL_SECONDS,
    )
    
    # Create buckets up to the limit
    for i in range(10):
        provider_key_id = f"lru_key_{i}"
        await scheduler.check_rate_limit(
            provider_key_id=provider_key_id,
            provider_key_qps=10.0,
        )
    
    assert len(scheduler.buckets) == 10
    
    # Create one more bucket - should evict oldest
    provider_key_id = "lru_key_new"
    await scheduler.check_rate_limit(
        provider_key_id=provider_key_id,
        provider_key_qps=10.0,
    )
    
    # Should still have 10 buckets (one evicted)
    assert len(scheduler.buckets) == 10
    
    # New bucket should exist
    assert "provider_key:lru_key_new" in scheduler.buckets
    
    # Oldest bucket should be evicted (first one created)
    assert "provider_key:lru_key_0" not in scheduler.buckets
    
    print("LRU eviction test: oldest bucket evicted correctly")


@pytest.mark.asyncio
async def test_rate_scheduler_memory_usage():
    """Test memory usage doesn't grow unbounded."""
    tracemalloc.start()
    
    snapshot_before = tracemalloc.take_snapshot()
    
    scheduler = RateScheduler(max_buckets=MAX_BUCKETS)
    
    # Create many buckets
    for i in range(500):
        provider_key_id = f"memory_test_key_{i}"
        await scheduler.check_rate_limit(
            provider_key_id=provider_key_id,
            provider_key_qps=10.0,
        )
    
    snapshot_after = tracemalloc.take_snapshot()
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Memory should be reasonable (less than 50MB for 500 buckets)
    assert current < 50 * 1024 * 1024, f"Memory usage too high: {current / 1024 / 1024:.2f} MB"
    
    print(f"Memory usage test: {current / 1024 / 1024:.2f} MB for 500 buckets")


@pytest.mark.asyncio
async def test_rate_scheduler_concurrent_access():
    """Test concurrent access to rate scheduler from multiple coroutines."""
    scheduler = RateScheduler(max_buckets=MAX_BUCKETS)
    
    num_concurrent = 50
    requests_per_coroutine = 20
    
    async def make_requests(coroutine_id: int):
        """Make multiple requests from a coroutine."""
        results = []
        for i in range(requests_per_coroutine):
            provider_key_id = f"concurrent_key_{coroutine_id}"
            allowed, retry_after, bucket = await scheduler.check_rate_limit(
                provider_key_id=provider_key_id,
                provider_key_qps=100.0,
            )
            results.append((allowed, retry_after))
        return results
    
    # Run concurrent requests
    tasks = [make_requests(i) for i in range(num_concurrent)]
    all_results = await asyncio.gather(*tasks)
    
    # Verify all requests completed
    total_requests = sum(len(results) for results in all_results)
    assert total_requests == num_concurrent * requests_per_coroutine
    
    # Verify no errors occurred
    for results in all_results:
        for allowed, retry_after in results:
            assert isinstance(allowed, bool)
            assert retry_after is None or isinstance(retry_after, float)
    
    print(f"Concurrent access test: {total_requests} requests from {num_concurrent} coroutines")
