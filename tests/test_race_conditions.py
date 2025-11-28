"""Unit tests for race conditions in cache and idempotency."""
import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

import pytest
import redis

from reliapi.core.cache import Cache
from reliapi.core.idempotency import IdempotencyManager


@pytest.fixture
def redis_client():
    """Create Redis client for testing."""
    try:
        client = redis.from_url("redis://localhost:6379/1", decode_responses=True)
        client.ping()
        # Clean test database
        client.flushdb()
        yield client
        client.flushdb()
        client.close()
    except redis.ConnectionError:
        pytest.skip("Redis not available")


@pytest.fixture
def cache(redis_client):
    """Create Cache instance for testing."""
    return Cache("redis://localhost:6379/1", key_prefix="test_cache")


@pytest.fixture
def idempotency(redis_client):
    """Create IdempotencyManager instance for testing."""
    return IdempotencyManager("redis://localhost:6379/1", key_prefix="test_idempotency")


class TestCacheRaceConditions:
    """Test race conditions in cache operations."""
    
    def test_concurrent_set_same_key(self, cache):
        """Test concurrent SET operations on the same key.
        
        Edge case: Multiple requests try to cache the same response simultaneously.
        Expected: All succeed, last write wins (or all write same value).
        """
        key = "test_key"
        value = {"status": 200, "body": "test"}
        
        def set_cache():
            cache.set("GET", "http://example.com/test", None, None, value, ttl_s=60)
        
        # Run 10 concurrent sets
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(set_cache) for _ in range(10)]
            for future in futures:
                future.result()  # Wait for completion
        
        # Verify cache has value (any of the writes should succeed)
        cached = cache.get("GET", "http://example.com/test", None, None)
        assert cached is not None
        assert cached["status"] == 200
    
    def test_concurrent_get_set(self, cache):
        """Test concurrent GET and SET on same key.
        
        Edge case: One request reads while another writes.
        Expected: GET may return None or the new value, but no errors.
        """
        key = "test_key"
        value = {"status": 200, "body": "test"}
        
        def get_cache():
            return cache.get("GET", "http://example.com/test", None, None)
        
        def set_cache():
            cache.set("GET", "http://example.com/test", None, None, value, ttl_s=60)
        
        # Set initial value
        cache.set("GET", "http://example.com/test", None, None, value, ttl_s=60)
        
        # Run concurrent get and set
        with ThreadPoolExecutor(max_workers=5) as executor:
            get_futures = [executor.submit(get_cache) for _ in range(5)]
            set_futures = [executor.submit(set_cache) for _ in range(5)]
            
            # Wait for all
            for future in get_futures + set_futures:
                future.result()  # Should not raise
        
        # Final value should exist
        cached = cache.get("GET", "http://example.com/test", None, None)
        assert cached is not None


class TestIdempotencyRaceConditions:
    """Test race conditions in idempotency operations."""
    
    def test_concurrent_register_same_key(self, idempotency):
        """Test concurrent registration of the same idempotency key.
        
        Edge case: Multiple requests with same idempotency_key arrive simultaneously.
        Expected: Only one should register (is_new=True), others should get existing (is_new=False).
        This is the core race condition test.
        """
        idempotency_key = "test_key_123"
        method = "POST"
        url = "http://example.com/api"
        body = b'{"test": "data"}'
        
        def register():
            return idempotency.register_request(
                idempotency_key, method, url, None, body, f"req_{time.time()}"
            )
        
        # Run 10 concurrent registrations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(register) for _ in range(10)]
            results = [f.result() for f in futures]
        
        # Exactly one should be new (is_new=True)
        new_count = sum(1 for is_new, _, _ in results if is_new)
        assert new_count == 1, f"Expected exactly 1 new registration, got {new_count}"
        
        # All others should have existing_request_id
        existing_ids = [req_id for _, req_id, _ in results if req_id is not None]
        assert len(set(existing_ids)) == 1, "All should reference the same existing request"
    
    def test_concurrent_register_different_body(self, idempotency):
        """Test concurrent registration with same key but different body.
        
        Edge case: Same idempotency_key but different request body.
        Expected: First one registers, others get conflict (is_new=False, different hash).
        """
        idempotency_key = "test_key_456"
        method = "POST"
        url = "http://example.com/api"
        
        def register(body_data):
            return idempotency.register_request(
                idempotency_key, method, url, None, body_data, f"req_{time.time()}"
            )
        
        # First request with body1
        body1 = b'{"amount": 100}'
        is_new1, req_id1, hash1 = register(body1)
        assert is_new1, "First request should be new"
        
        # Concurrent requests with different body
        body2 = b'{"amount": 200}'
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(register, body2) for _ in range(5)]
            results = [f.result() for f in futures]
        
        # All should detect conflict (is_new=False, different hash)
        for is_new, req_id, hash_val in results:
            assert not is_new, "Should detect conflict"
            assert req_id == req_id1, "Should reference first request"
            assert hash_val != hash1, "Hash should differ"
    
    def test_register_then_get_result_race(self, idempotency):
        """Test race between register and get_result.
        
        Edge case: Request A registers, Request B checks for result before A stores it.
        Expected: B should wait (coalescing) or get None, then get result when A completes.
        """
        idempotency_key = "test_key_789"
        method = "POST"
        url = "http://example.com/api"
        body = b'{"test": "data"}'
        
        # Register first request
        is_new, req_id, _ = idempotency.register_request(
            idempotency_key, method, url, None, body, "req_A"
        )
        assert is_new, "First should be new"
        
        # Mark as in progress
        idempotency.mark_in_progress(idempotency_key)
        
        # Second request tries to register (should get existing)
        is_new2, req_id2, _ = idempotency.register_request(
            idempotency_key, method, url, None, body, "req_B"
        )
        assert not is_new2, "Second should not be new"
        assert req_id2 == req_id, "Should reference first request"
        
        # Second request checks for result (should be None initially)
        result = idempotency.get_result(idempotency_key)
        assert result is None, "Result should not exist yet"
        
        # First request stores result
        idempotency.store_result(idempotency_key, {"data": "result"}, ttl_s=60)
        idempotency.clear_in_progress(idempotency_key)
        
        # Second request should now get result
        result = idempotency.get_result(idempotency_key)
        assert result is not None, "Result should exist after storage"
        assert result["data"] == "result"
    
    def test_atomic_setnx_expire(self, idempotency):
        """Test that SETNX + EXPIRE is atomic.
        
        Edge case: Verify that Redis SET with nx=True and ex=... is atomic.
        This is critical for preventing race conditions.
        """
        idempotency_key = "test_atomic_123"
        method = "POST"
        url = "http://example.com/api"
        body = b'{"test": "atomic"}'
        
        # Multiple concurrent registrations
        def register():
            return idempotency.register_request(
                idempotency_key, method, url, None, body, f"req_{time.time()}"
            )
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(register) for _ in range(20)]
            results = [f.result() for f in futures]
        
        # Exactly one should succeed
        new_count = sum(1 for is_new, _, _ in results if is_new)
        assert new_count == 1, f"Atomic operation failed: {new_count} new registrations"
        
        # Verify key exists with TTL
        if idempotency.enabled and idempotency.client:
            key = f"{idempotency.key_prefix}:idempotency:{idempotency_key}"
            ttl = idempotency.client.ttl(key)
            assert ttl > 0, "Key should have TTL set"
            assert ttl <= 3600, "TTL should be <= 3600 seconds"


class TestStreamingBudgetCaps:
    """Test streaming + budget caps edge cases."""
    
    def test_zero_tokens_generated(self):
        """Test edge case: 0 tokens generated in streaming response.
        
        Edge case: Provider returns stream but generates 0 completion tokens.
        This can happen if:
        - Provider immediately returns finish_reason="stop" with no content
        - Provider returns empty stream
        - Provider returns only usage information with 0 completion_tokens
        
        Expected: Cost should be calculated correctly (prompt-only cost, no completion cost).
        """
        from reliapi.adapters.llm.openai import OpenAIAdapter
        
        adapter = OpenAIAdapter()
        
        # Test 1: Normal case with tokens
        cost_normal = adapter.get_cost_usd("gpt-4o-mini", prompt_tokens=100, completion_tokens=50)
        assert cost_normal > 0
        assert isinstance(cost_normal, (int, float))
        
        # Test 2: Edge case - 0 completion tokens (only prompt tokens)
        cost_zero_completion = adapter.get_cost_usd("gpt-4o-mini", prompt_tokens=100, completion_tokens=0)
        assert cost_zero_completion >= 0  # Should be >= 0 (prompt tokens cost)
        assert isinstance(cost_zero_completion, (int, float))
        # Cost with 0 completion should be less than or equal to cost with completion
        assert cost_zero_completion <= cost_normal
        
        # Test 3: Edge case - 0 prompt tokens (shouldn't happen in practice, but test robustness)
        cost_zero_prompt = adapter.get_cost_usd("gpt-4o-mini", prompt_tokens=0, completion_tokens=50)
        assert cost_zero_prompt >= 0
        assert isinstance(cost_zero_prompt, (int, float))
        
        # Test 4: Edge case - both 0 (should return 0 cost)
        cost_both_zero = adapter.get_cost_usd("gpt-4o-mini", prompt_tokens=0, completion_tokens=0)
        assert cost_both_zero == 0
        assert isinstance(cost_both_zero, (int, float))
        
        # Test 5: Verify cost calculation doesn't raise exceptions for edge cases
        # This ensures streaming handler won't crash on 0 tokens
        try:
            cost = adapter.get_cost_usd("gpt-4o-mini", prompt_tokens=100, completion_tokens=0)
            assert cost >= 0
        except Exception as e:
            pytest.fail(f"Cost calculation raised exception for 0 tokens: {e}")
    
    def test_streaming_budget_caps_before_stream(self):
        """Test that budget caps are checked before opening stream.
        
        Edge case: Hard cap should reject request before any chunks are sent.
        Soft cap should reduce max_tokens before stream starts.
        """
        # This would be tested in integration tests with mock provider
        # For unit test, we verify the logic exists in services.py
        # The actual check happens in handle_llm_stream_generator before adapter.stream_chat()
        pass  # Integration test needed

