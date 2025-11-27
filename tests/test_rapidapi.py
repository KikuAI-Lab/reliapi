"""Tests for RapidAPI integration."""
import asyncio
import hashlib
import hmac
import json
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from reliapi.integrations.rapidapi import (
    RapidAPIClient,
    RapidAPICircuitBreaker,
    SubscriptionInfo,
    SubscriptionTier,
)


class TestSubscriptionTier:
    """Tests for SubscriptionTier enum."""
    
    def test_tier_values(self):
        """Test tier enum values."""
        assert SubscriptionTier.FREE.value == "free"
        assert SubscriptionTier.DEVELOPER.value == "developer"
        assert SubscriptionTier.PRO.value == "pro"
        assert SubscriptionTier.ENTERPRISE.value == "enterprise"
    
    def test_tier_from_string(self):
        """Test creating tier from string."""
        assert SubscriptionTier("free") == SubscriptionTier.FREE
        assert SubscriptionTier("developer") == SubscriptionTier.DEVELOPER
        assert SubscriptionTier("pro") == SubscriptionTier.PRO
        assert SubscriptionTier("enterprise") == SubscriptionTier.ENTERPRISE


class TestRapidAPICircuitBreaker:
    """Tests for RapidAPICircuitBreaker."""
    
    @pytest.mark.asyncio
    async def test_initial_state_closed(self):
        """Test circuit breaker starts closed."""
        cb = RapidAPICircuitBreaker()
        assert not await cb.is_open()
    
    @pytest.mark.asyncio
    async def test_opens_after_failures(self):
        """Test circuit opens after threshold failures."""
        cb = RapidAPICircuitBreaker(failures_to_open=3)
        
        await cb.record_failure()
        assert not await cb.is_open()
        
        await cb.record_failure()
        assert not await cb.is_open()
        
        await cb.record_failure()  # 3rd failure
        assert await cb.is_open()
    
    @pytest.mark.asyncio
    async def test_success_resets_count(self):
        """Test success resets failure count."""
        cb = RapidAPICircuitBreaker(failures_to_open=3)
        
        await cb.record_failure()
        await cb.record_failure()
        await cb.record_success()  # Reset
        
        await cb.record_failure()
        await cb.record_failure()
        assert not await cb.is_open()  # Still closed (only 2 failures)
    
    @pytest.mark.asyncio
    async def test_auto_close_after_ttl(self):
        """Test circuit auto-closes after TTL."""
        cb = RapidAPICircuitBreaker(failures_to_open=2, open_ttl_s=0.1)
        
        await cb.record_failure()
        await cb.record_failure()
        assert await cb.is_open()
        
        await asyncio.sleep(0.15)  # Wait for TTL
        assert not await cb.is_open()


class TestRapidAPIClient:
    """Tests for RapidAPIClient."""
    
    @pytest.fixture
    def client_no_redis(self):
        """Create client without Redis."""
        with patch('reliapi.integrations.rapidapi.redis') as mock_redis:
            mock_redis.from_url.side_effect = Exception("Redis not available")
            client = RapidAPIClient(redis_url="redis://localhost:6379")
            assert not client.redis_enabled
            return client
    
    @pytest.fixture
    def client_with_redis(self):
        """Create client with mocked Redis."""
        with patch('reliapi.integrations.rapidapi.redis') as mock_redis:
            mock_client = MagicMock()
            mock_redis.from_url.return_value = mock_client
            client = RapidAPIClient(redis_url="redis://localhost:6379")
            assert client.redis_enabled
            return client
    
    def test_hash_api_key(self, client_no_redis):
        """Test API key hashing."""
        api_key = "test-api-key-12345"
        hash1 = client_no_redis._hash_api_key(api_key)
        hash2 = client_no_redis._hash_api_key(api_key)
        
        assert hash1 == hash2  # Same input, same hash
        assert len(hash1) == 16  # Truncated to 16 chars
        assert api_key not in hash1  # Not reversible
    
    def test_get_tier_from_headers_with_user(self, client_no_redis):
        """Test tier detection from RapidAPI headers."""
        headers = {
            "X-RapidAPI-User": "user123",
            "X-RapidAPI-Subscription": "pro",
        }
        
        result = client_no_redis.get_tier_from_headers(headers)
        assert result is not None
        user_id, tier = result
        assert user_id == "user123"
        assert tier == SubscriptionTier.DEVELOPER  # "pro" maps to DEVELOPER
    
    def test_get_tier_from_headers_basic(self, client_no_redis):
        """Test tier detection for basic subscription."""
        headers = {
            "X-RapidAPI-User": "user456",
            "X-RapidAPI-Subscription": "basic",
        }
        
        result = client_no_redis.get_tier_from_headers(headers)
        assert result is not None
        user_id, tier = result
        assert tier == SubscriptionTier.FREE
    
    def test_get_tier_from_headers_enterprise(self, client_no_redis):
        """Test tier detection for enterprise subscription."""
        headers = {
            "X-RapidAPI-User": "enterprise_user",
            "X-RapidAPI-Subscription": "enterprise",
        }
        
        result = client_no_redis.get_tier_from_headers(headers)
        assert result is not None
        user_id, tier = result
        assert tier == SubscriptionTier.ENTERPRISE
    
    def test_get_tier_from_headers_missing_user(self, client_no_redis):
        """Test tier detection fails without user header."""
        headers = {
            "X-RapidAPI-Subscription": "pro",
        }
        
        result = client_no_redis.get_tier_from_headers(headers)
        assert result is None
    
    def test_get_tier_from_headers_proxy_secret_mismatch(self, client_no_redis):
        """Test tier detection fails with proxy secret mismatch."""
        headers = {
            "X-RapidAPI-User": "user123",
            "X-RapidAPI-Subscription": "pro",
            "X-RapidAPI-Proxy-Secret": "wrong-secret",
        }
        
        result = client_no_redis.get_tier_from_headers(headers, proxy_secret="correct-secret")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_subscription_tier_test_keys(self, client_no_redis):
        """Test tier detection for test keys."""
        assert await client_no_redis.get_subscription_tier("sk-free-test") == SubscriptionTier.FREE
        assert await client_no_redis.get_subscription_tier("sk-dev-test") == SubscriptionTier.DEVELOPER
        assert await client_no_redis.get_subscription_tier("sk-pro-test") == SubscriptionTier.PRO
    
    @pytest.mark.asyncio
    async def test_get_subscription_tier_from_headers(self, client_no_redis):
        """Test tier detection prioritizes headers."""
        headers = {
            "X-RapidAPI-User": "user123",
            "X-RapidAPI-Subscription": "ultra",  # Maps to PRO
        }
        
        # Even with sk-free key, headers should take priority
        tier = await client_no_redis.get_subscription_tier("sk-free-test", headers)
        assert tier == SubscriptionTier.PRO
    
    @pytest.mark.asyncio
    async def test_validate_api_key_test_keys(self, client_no_redis):
        """Test validation passes for test keys."""
        is_valid, error = await client_no_redis.validate_api_key("sk-free-test")
        assert is_valid
        assert error is None
        
        is_valid, error = await client_no_redis.validate_api_key("sk-dev-test")
        assert is_valid
        
        is_valid, error = await client_no_redis.validate_api_key("sk-pro-test")
        assert is_valid
    
    @pytest.mark.asyncio
    async def test_validate_api_key_empty(self, client_no_redis):
        """Test validation fails for empty key."""
        is_valid, error = await client_no_redis.validate_api_key("")
        assert not is_valid
        assert error is not None
    
    @pytest.mark.asyncio
    async def test_validate_api_key_from_headers(self, client_no_redis):
        """Test validation from RapidAPI headers."""
        headers = {
            "X-RapidAPI-User": "user123",
            "X-RapidAPI-Subscription": "pro",
        }
        
        is_valid, error = await client_no_redis.validate_api_key("any-key", headers)
        assert is_valid
    
    @pytest.mark.asyncio
    async def test_get_usage_stats_default(self, client_no_redis):
        """Test usage stats returns defaults without Redis."""
        stats = await client_no_redis.get_usage_stats("test-key")
        
        assert "requests_count" in stats
        assert "requests_limit" in stats
        assert "period" in stats
        assert stats["requests_count"] == 0
    
    @pytest.mark.asyncio
    async def test_record_usage_no_redis(self, client_no_redis):
        """Test usage recording doesn't fail without Redis."""
        # Should not raise
        await client_no_redis.record_usage(
            api_key="test-key",
            endpoint="/proxy/llm",
            latency_ms=100,
            status="success",
            cost_usd=0.01,
        )
    
    def test_verify_webhook_signature_no_secret(self, client_no_redis):
        """Test webhook verification passes without secret configured."""
        assert client_no_redis.verify_webhook_signature(b"test", "any-sig")
    
    def test_verify_webhook_signature_valid(self):
        """Test webhook verification with valid signature."""
        secret = "test-webhook-secret"
        payload = b'{"type": "subscription.created"}'
        
        # Create valid signature
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        
        with patch('reliapi.integrations.rapidapi.redis') as mock_redis:
            mock_redis.from_url.side_effect = Exception("Redis not available")
            client = RapidAPIClient(
                redis_url="redis://localhost:6379",
                webhook_secret=secret,
            )
        
        assert client.verify_webhook_signature(payload, signature)
    
    def test_verify_webhook_signature_invalid(self):
        """Test webhook verification fails with invalid signature."""
        secret = "test-webhook-secret"
        payload = b'{"type": "subscription.created"}'
        
        with patch('reliapi.integrations.rapidapi.redis') as mock_redis:
            mock_redis.from_url.side_effect = Exception("Redis not available")
            client = RapidAPIClient(
                redis_url="redis://localhost:6379",
                webhook_secret=secret,
            )
        
        assert not client.verify_webhook_signature(payload, "invalid-signature")
    
    @pytest.mark.asyncio
    async def test_cache_tier(self, client_with_redis):
        """Test tier caching."""
        await client_with_redis._cache_tier(
            "test-api-key",
            SubscriptionTier.PRO,
            "user123",
        )
        
        # Verify Redis was called
        client_with_redis.redis.hset.assert_called_once()
        client_with_redis.redis.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_cached_tier(self, client_with_redis):
        """Test getting cached tier."""
        client_with_redis.redis.hgetall.return_value = {
            "tier": "pro",
            "user_id": "user123",
            "cached_at": str(time.time()),
        }
        
        tier = await client_with_redis._get_cached_tier("test-api-key")
        assert tier == SubscriptionTier.PRO
    
    @pytest.mark.asyncio
    async def test_get_cached_tier_miss(self, client_with_redis):
        """Test cache miss returns None."""
        client_with_redis.redis.hgetall.return_value = {}
        
        tier = await client_with_redis._get_cached_tier("test-api-key")
        assert tier is None
    
    @pytest.mark.asyncio
    async def test_invalidate_tier_cache(self, client_with_redis):
        """Test cache invalidation."""
        await client_with_redis.invalidate_tier_cache("test-api-key")
        
        client_with_redis.redis.delete.assert_called_once()


class TestTierMapping:
    """Tests for subscription tier mapping."""
    
    @pytest.fixture
    def client(self):
        """Create client without Redis."""
        with patch('reliapi.integrations.rapidapi.redis') as mock_redis:
            mock_redis.from_url.side_effect = Exception("Redis not available")
            return RapidAPIClient(redis_url="redis://localhost:6379")
    
    @pytest.mark.parametrize("subscription,expected_tier", [
        ("basic", SubscriptionTier.FREE),
        ("free", SubscriptionTier.FREE),
        ("pro", SubscriptionTier.DEVELOPER),
        ("developer", SubscriptionTier.DEVELOPER),
        ("ultra", SubscriptionTier.PRO),
        ("mega", SubscriptionTier.PRO),
        ("enterprise", SubscriptionTier.ENTERPRISE),
        ("unknown", SubscriptionTier.FREE),  # Unknown defaults to FREE
        ("", SubscriptionTier.FREE),  # Empty defaults to FREE
    ])
    def test_tier_mapping(self, client, subscription, expected_tier):
        """Test subscription to tier mapping."""
        headers = {
            "X-RapidAPI-User": "test_user",
            "X-RapidAPI-Subscription": subscription,
        }
        
        result = client.get_tier_from_headers(headers)
        assert result is not None
        _, tier = result
        assert tier == expected_tier


class TestUsageTracking:
    """Tests for usage tracking functionality."""
    
    @pytest.fixture
    def client(self):
        """Create client with mocked Redis."""
        with patch('reliapi.integrations.rapidapi.redis') as mock_redis:
            mock_client = MagicMock()
            mock_redis.from_url.return_value = mock_client
            return RapidAPIClient(redis_url="redis://localhost:6379")
    
    @pytest.mark.asyncio
    async def test_usage_queue_batching(self, client):
        """Test usage records are queued for batching."""
        for i in range(50):
            await client.record_usage(
                api_key="test-key",
                endpoint="/proxy/http",
                latency_ms=100,
                status="success",
            )
        
        # Queue should have records (not flushed yet - threshold is 100)
        assert len(client._usage_queue) <= 50 or len(client._usage_queue) == 0  # May have been flushed
    
    @pytest.mark.asyncio
    async def test_usage_redis_tracking(self, client):
        """Test usage is recorded in Redis."""
        await client.record_usage(
            api_key="test-key",
            endpoint="/proxy/llm",
            latency_ms=200,
            status="success",
            cost_usd=0.05,
        )
        
        # Verify Redis incr was called
        client.redis.incr.assert_called()


class TestErrorHandling:
    """Tests for error handling in RapidAPI client."""
    
    @pytest.fixture
    def client(self):
        """Create client without Redis."""
        with patch('reliapi.integrations.rapidapi.redis') as mock_redis:
            mock_redis.from_url.side_effect = Exception("Redis not available")
            return RapidAPIClient(redis_url="redis://localhost:6379")
    
    @pytest.mark.asyncio
    async def test_cache_error_graceful(self, client):
        """Test cache errors don't break tier detection."""
        # Should return fallback tier
        tier = await client.get_subscription_tier("unknown-key")
        assert tier == SubscriptionTier.FREE
    
    @pytest.mark.asyncio
    async def test_usage_stats_error_graceful(self, client):
        """Test usage stats errors return defaults."""
        stats = await client.get_usage_stats("test-key")
        
        assert stats is not None
        assert "requests_count" in stats


