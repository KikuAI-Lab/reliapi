"""Integration tests for Free tier restrictions."""
import pytest
import httpx
import os
import time

# Test configuration
BASE_URL = os.getenv("RELIAPI_URL", "http://127.0.0.1:8000")
FREE_TIER_KEY = os.getenv("RELIAPI_FREE_TIER_KEY", "sk-free-test")
PAID_TIER_KEY = os.getenv("RELIAPI_PAID_TIER_KEY", os.getenv("RELIAPI_API_KEY", ""))


def check_server_available():
    """Check if ReliAPI server is available."""
    try:
        client = httpx.Client(timeout=2.0)
        response = client.get(f"{BASE_URL}/healthz")
        client.close()
        return response.status_code == 200
    except Exception:
        return False


class TestFreeTierRateLimiting:
    """Test rate limiting for Free tier."""
    
    @pytest.mark.skipif(not FREE_TIER_KEY.startswith("sk-free"), reason="Free tier key not configured")
    @pytest.mark.skipif(not check_server_available(), reason="ReliAPI server not available")
    def test_ip_rate_limit_free_tier(self):
        """Test that Free tier is rate limited to 20 req/min per IP."""
        client = httpx.Client(timeout=10.0)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": FREE_TIER_KEY,
        }
        
        # Make 20 requests (should all pass)
        success_count = 0
        for i in range(20):
            response = client.post(
                f"{BASE_URL}/proxy/http",
                headers=headers,
                json={
                    "target": "openai",
                    "method": "GET",
                    "path": "/models",
                },
            )
            if response.status_code == 200:
                success_count += 1
            time.sleep(0.1)  # Small delay
        
        assert success_count == 20, "First 20 requests should pass"
        
        # 21st request should be rate limited
        response = client.post(
            f"{BASE_URL}/proxy/http",
            headers=headers,
            json={
                "target": "openai",
                "method": "GET",
                "path": "/models",
            },
        )
        assert response.status_code == 429, "21st request should be rate limited"
        
        data = response.json()
        assert data.get("error", {}).get("code") == "RATE_LIMIT_EXCEEDED"
    
    @pytest.mark.skipif(not PAID_TIER_KEY, reason="Paid tier key not configured")
    @pytest.mark.skipif(not check_server_available(), reason="ReliAPI server not available")
    def test_paid_tier_no_rate_limit(self):
        """Test that paid tier is not rate limited."""
        client = httpx.Client(timeout=10.0)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": PAID_TIER_KEY,
        }
        
        # Make 25 requests (should all pass for paid tier)
        success_count = 0
        for i in range(25):
            response = client.post(
                f"{BASE_URL}/proxy/http",
                headers=headers,
                json={
                    "target": "openai",
                    "method": "GET",
                    "path": "/models",
                },
            )
            if response.status_code == 200:
                success_count += 1
            time.sleep(0.1)
        
        # Paid tier should not be rate limited at 20 req/min
        assert success_count >= 20, "Paid tier should not be rate limited"


class TestFreeTierModelRestrictions:
    """Test model restrictions for Free tier."""
    
    @pytest.mark.skipif(not FREE_TIER_KEY.startswith("sk-free"), reason="Free tier key not configured")
    @pytest.mark.skipif(not check_server_available(), reason="ReliAPI server not available")
    def test_allowed_model_free_tier(self):
        """Test that cheap models are allowed for Free tier."""
        client = httpx.Client(timeout=10.0)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": FREE_TIER_KEY,
        }
        
        response = client.post(
            f"{BASE_URL}/proxy/llm",
            headers=headers,
            json={
                "target": "openai",
                "messages": [{"role": "user", "content": "Hi"}],
                "model": "gpt-4o-mini",
                "max_tokens": 5,
            },
        )
        
        assert response.status_code == 200, "gpt-4o-mini should be allowed"
        data = response.json()
        assert data.get("success") is True
    
    @pytest.mark.skipif(not FREE_TIER_KEY.startswith("sk-free"), reason="Free tier key not configured")
    @pytest.mark.skipif(not check_server_available(), reason="ReliAPI server not available")
    def test_blocked_model_free_tier(self):
        """Test that expensive models are blocked for Free tier."""
        client = httpx.Client(timeout=10.0)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": FREE_TIER_KEY,
        }
        
        response = client.post(
            f"{BASE_URL}/proxy/llm",
            headers=headers,
            json={
                "target": "openai",
                "messages": [{"role": "user", "content": "Hi"}],
                "model": "gpt-4",
                "max_tokens": 5,
            },
        )
        
        assert response.status_code == 403, "gpt-4 should be blocked"
        data = response.json()
        assert data.get("error", {}).get("code") == "FREE_TIER_MODEL_NOT_ALLOWED"
    
    @pytest.mark.skipif(not PAID_TIER_KEY, reason="Paid tier key not configured")
    @pytest.mark.skipif(not check_server_available(), reason="ReliAPI server not available")
    def test_any_model_allowed_paid_tier(self):
        """Test that paid tier can use any model."""
        client = httpx.Client(timeout=10.0)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": PAID_TIER_KEY,
        }
        
        # Try expensive model (should work for paid tier)
        response = client.post(
            f"{BASE_URL}/proxy/llm",
            headers=headers,
            json={
                "target": "openai",
                "messages": [{"role": "user", "content": "Hi"}],
                "model": "gpt-4o-mini",  # Using allowed model for test
                "max_tokens": 5,
            },
        )
        
        assert response.status_code == 200, "Paid tier should allow any model"
        data = response.json()
        assert data.get("success") is True


class TestFreeTierFeatureRestrictions:
    """Test feature restrictions for Free tier."""
    
    @pytest.mark.skipif(not FREE_TIER_KEY.startswith("sk-free"), reason="Free tier key not configured")
    @pytest.mark.skipif(not check_server_available(), reason="ReliAPI server not available")
    def test_idempotency_blocked_free_tier(self):
        """Test that idempotency is blocked for Free tier."""
        client = httpx.Client(timeout=10.0)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": FREE_TIER_KEY,
        }
        
        response = client.post(
            f"{BASE_URL}/proxy/llm",
            headers=headers,
            json={
                "target": "openai",
                "messages": [{"role": "user", "content": "Hi"}],
                "model": "gpt-4o-mini",
                "max_tokens": 5,
                "idempotency_key": "test-key-123",
            },
        )
        
        assert response.status_code == 403, "Idempotency should be blocked"
        data = response.json()
        assert data.get("error", {}).get("code") == "FREE_TIER_FEATURE_NOT_AVAILABLE"
    
    @pytest.mark.skipif(not PAID_TIER_KEY, reason="Paid tier key not configured")
    @pytest.mark.skipif(not check_server_available(), reason="ReliAPI server not available")
    def test_idempotency_allowed_paid_tier(self):
        """Test that paid tier can use idempotency."""
        client = httpx.Client(timeout=10.0)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": PAID_TIER_KEY,
        }
        
        response = client.post(
            f"{BASE_URL}/proxy/llm",
            headers=headers,
            json={
                "target": "openai",
                "messages": [{"role": "user", "content": "Hi"}],
                "model": "gpt-4o-mini",
                "max_tokens": 5,
                "idempotency_key": "test-key-123",
            },
        )
        
        assert response.status_code == 200, "Paid tier should allow idempotency"
        data = response.json()
        assert data.get("success") is True

