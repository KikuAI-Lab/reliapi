"""Tests for Free tier restrictions and rate limiting."""
import pytest
from unittest.mock import patch
from reliapi.core.free_tier_restrictions import FreeTierRestrictions, FREE_TIER_ALLOWED_MODELS
from reliapi.core.rate_limiter import RateLimiter


class TestFreeTierRestrictions:
    """Test Free tier model and feature restrictions."""
    
    def test_allowed_models_free_tier(self):
        """Test that cheap models are allowed for Free tier."""
        # OpenAI
        allowed, _ = FreeTierRestrictions.is_model_allowed("openai", "gpt-4o-mini", "free")
        assert allowed is True
        
        allowed, _ = FreeTierRestrictions.is_model_allowed("openai", "gpt-3.5-turbo", "free")
        assert allowed is True
        
        # Anthropic
        allowed, _ = FreeTierRestrictions.is_model_allowed("anthropic", "claude-3-haiku-20240307", "free")
        assert allowed is True
        
        # Mistral
        allowed, _ = FreeTierRestrictions.is_model_allowed("mistral", "mistral-small", "free")
        assert allowed is True
    
    def test_blocked_models_free_tier(self):
        """Test that expensive models are blocked for Free tier."""
        # OpenAI expensive models
        allowed, error = FreeTierRestrictions.is_model_allowed("openai", "gpt-4", "free")
        assert allowed is False
        assert error == "FREE_TIER_MODEL_NOT_ALLOWED"
        
        allowed, _ = FreeTierRestrictions.is_model_allowed("openai", "gpt-4-turbo", "free")
        assert allowed is False
        
        # Anthropic expensive models
        allowed, _ = FreeTierRestrictions.is_model_allowed("anthropic", "claude-3-opus", "free")
        assert allowed is False
        
        allowed, _ = FreeTierRestrictions.is_model_allowed("anthropic", "claude-3-sonnet", "free")
        assert allowed is False
    
    def test_all_models_allowed_paid_tiers(self):
        """Test that paid tiers can use any model."""
        for tier in ["developer", "pro"]:
            allowed, _ = FreeTierRestrictions.is_model_allowed("openai", "gpt-4", tier)
            assert allowed is True
            
            allowed, _ = FreeTierRestrictions.is_model_allowed("anthropic", "claude-3-opus", tier)
            assert allowed is True
    
    def test_idempotency_blocked_free_tier(self):
        """Test that idempotency is blocked for Free tier."""
        allowed, error = FreeTierRestrictions.is_feature_allowed("idempotency", "free")
        assert allowed is False
        assert error == "FREE_TIER_FEATURE_NOT_AVAILABLE"
    
    def test_soft_caps_blocked_free_tier(self):
        """Test that soft caps are blocked for Free tier."""
        allowed, error = FreeTierRestrictions.is_feature_allowed("soft_caps", "free")
        assert allowed is False
        assert error == "FREE_TIER_FEATURE_NOT_AVAILABLE"
    
    def test_features_allowed_paid_tiers(self):
        """Test that paid tiers have access to all features."""
        for tier in ["developer", "pro"]:
            allowed, _ = FreeTierRestrictions.is_feature_allowed("idempotency", tier)
            assert allowed is True
            
            allowed, _ = FreeTierRestrictions.is_feature_allowed("soft_caps", tier)
            assert allowed is True
    
    def test_max_retries(self):
        """Test max retries per tier."""
        assert FreeTierRestrictions.get_max_retries("free") == 1
        assert FreeTierRestrictions.get_max_retries("developer") == 3
        assert FreeTierRestrictions.get_max_retries("pro") == 5
    
    def test_max_fallback_chain_length(self):
        """Test max fallback chain length per tier."""
        assert FreeTierRestrictions.get_max_fallback_chain_length("free") == 1
        assert FreeTierRestrictions.get_max_fallback_chain_length("developer") == 2
        assert FreeTierRestrictions.get_max_fallback_chain_length("pro") == 5
    
    def test_validate_request_free_tier(self):
        """Test request validation for Free tier."""
        # Valid request
        allowed, _ = FreeTierRestrictions.validate_request(
            "openai",
            "gpt-4o-mini",
            {},
            "free"
        )
        assert allowed is True
        
        # Invalid: expensive model
        allowed, error = FreeTierRestrictions.validate_request(
            "openai",
            "gpt-4",
            {},
            "free"
        )
        assert allowed is False
        assert error == "FREE_TIER_MODEL_NOT_ALLOWED"
        
        # Invalid: idempotency key
        allowed, error = FreeTierRestrictions.validate_request(
            "openai",
            "gpt-4o-mini",
            {"idempotency_key": "test-key"},
            "free"
        )
        assert allowed is False
        assert error == "FREE_TIER_FEATURE_NOT_AVAILABLE"
        
        # Invalid: soft cap
        allowed, error = FreeTierRestrictions.validate_request(
            "openai",
            "gpt-4o-mini",
            {"soft_cost_cap_usd": 0.1},
            "free"
        )
        assert allowed is False
        assert error == "FREE_TIER_FEATURE_NOT_AVAILABLE"
        
        # Invalid: too many fallbacks
        allowed, error = FreeTierRestrictions.validate_request(
            "openai",
            "gpt-4o-mini",
            {"fallback_targets": ["anthropic", "mistral"]},  # 2 fallbacks = 3 total
            "free"
        )
        assert allowed is False
        assert error == "FREE_TIER_FEATURE_NOT_AVAILABLE"


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """Create rate limiter instance with mocked Redis."""
        from unittest.mock import patch
        # Patch redis modules before creating RateLimiter
        with patch('reliapi.core.rate_limiter.redis') as mock_redis_module, \
             patch('reliapi.core.security.redis') as mock_security_redis_module:
            mock_redis_module.from_url.return_value = mock_redis
            mock_security_redis_module.from_url.return_value = mock_redis
            # Mock ping to succeed
            mock_redis.ping.return_value = True
            # Mock incr to return sequential values (for rate limiting tests)
            call_count = [0]
            def incr_side_effect(key):
                call_count[0] += 1
                return call_count[0]
            mock_redis.incr.side_effect = incr_side_effect
            mock_redis.expire.return_value = True
            # Mock zadd, zremrangebyscore, zcard for burst detection
            mock_redis.zadd.return_value = 1
            mock_redis.zremrangebyscore.return_value = 0
            mock_redis.zcard.return_value = 0
            # Mock hset, hgetall for fingerprint
            mock_redis.hset.return_value = 1
            mock_redis.hgetall.return_value = {}
            mock_redis.exists.return_value = 0
            # Mock get for abuse detection
            mock_redis.get.return_value = None
            limiter = RateLimiter("redis://localhost:6379/0")
            # Keep patches alive by storing them
            limiter._patches = (mock_redis_module, mock_security_redis_module)
            return limiter
    
    def test_ip_rate_limit(self, rate_limiter, mock_redis):
        """Test IP-based rate limiting."""
        ip = "192.168.1.1"
        
        # Reset call count for this test
        call_count = [0]
        def incr_side_effect(key):
            call_count[0] += 1
            return call_count[0]
        mock_redis.incr.side_effect = incr_side_effect
        
        # First 20 requests should pass
        for i in range(20):
            allowed, error = rate_limiter.check_ip_rate_limit(ip, limit_per_minute=20)
            assert allowed is True
            assert error is None
        
        # 21st request should be blocked
        allowed, error = rate_limiter.check_ip_rate_limit(ip, limit_per_minute=20)
        assert allowed is False
        assert error == "RATE_LIMIT_EXCEEDED"
    
    def test_account_burst_limit(self, rate_limiter, mock_redis):
        """Test per-account burst limiting."""
        account_id = "test-account-123"
        
        # Reset call count for this test
        call_count = [0]
        def incr_side_effect(key):
            call_count[0] += 1
            return call_count[0]
        mock_redis.incr.side_effect = incr_side_effect
        
        # First 500 requests should pass
        for i in range(500):
            allowed, error = rate_limiter.check_account_burst_limit(account_id, limit_per_minute=500)
            assert allowed is True
            assert error is None
        
        # 501st request should be blocked
        allowed, error = rate_limiter.check_account_burst_limit(account_id, limit_per_minute=500)
        assert allowed is False
        assert error == "FREE_TIER_ABUSE"
    
    def test_fingerprint_limit(self, rate_limiter, mock_redis):
        """Test fingerprint-based rate limiting."""
        ip = "192.168.1.1"
        user_agent = "Mozilla/5.0"
        api_key = "sk-test-123"
        
        # Reset call count for this test
        call_count = [0]
        def incr_side_effect(key):
            call_count[0] += 1
            return call_count[0]
        mock_redis.incr.side_effect = incr_side_effect
        
        # First 20 requests should pass
        for i in range(20):
            allowed, error = rate_limiter.check_fingerprint_limit(ip, user_agent, api_key, limit_per_minute=20)
            assert allowed is True
        
        # 21st request should be blocked
        allowed, error = rate_limiter.check_fingerprint_limit(ip, user_agent, api_key, limit_per_minute=20)
        assert allowed is False
        assert error == "FINGERPRINT_RATE_LIMIT_EXCEEDED"
    
    def test_fingerprint_sticky(self, rate_limiter, mock_redis):
        """Test that fingerprint is sticky across different IPs."""
        ip1 = "192.168.1.1"
        ip2 = "192.168.1.2"
        user_agent = "Mozilla/5.0"
        api_key = "sk-test-123"
        
        # Reset call count for this test
        call_count = [0]
        def incr_side_effect(key):
            call_count[0] += 1
            return call_count[0]
        mock_redis.incr.side_effect = incr_side_effect
        
        # Use same fingerprint from different IPs
        for i in range(10):
            allowed, _ = rate_limiter.check_fingerprint_limit(ip1, user_agent, api_key, limit_per_minute=20)
            assert allowed is True
        
        # Switch IP but keep same fingerprint components
        for i in range(10):
            allowed, _ = rate_limiter.check_fingerprint_limit(ip2, user_agent, api_key, limit_per_minute=20)
            assert allowed is True
        
        # Should be blocked now (20 total)
        allowed, error = rate_limiter.check_fingerprint_limit(ip2, user_agent, api_key, limit_per_minute=20)
        assert allowed is False
    
    def test_get_account_tier(self, rate_limiter):
        """Test account tier detection."""
        # Test tier detection (placeholder implementation)
        assert rate_limiter.get_account_tier("sk-free-test") == "free"
        assert rate_limiter.get_account_tier("sk-dev-test") == "developer"
        assert rate_limiter.get_account_tier("sk-pro-test") == "pro"
        assert rate_limiter.get_account_tier("unknown-key") == "free"  # Default

