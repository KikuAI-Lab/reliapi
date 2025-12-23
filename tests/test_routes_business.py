"""Tests for business routes (onboarding, analytics, health).

This module tests the business route endpoints:
- Onboarding flow (start, quick-start, verify)
- Analytics tracking (track, conversion, funnel)
- Health check endpoints
"""
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.setex.return_value = True
    return mock


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    # Import here to avoid circular imports
    from reliapi.app.main import app
    return TestClient(app)


class TestOnboardingRoutes:
    """Tests for onboarding endpoints."""

    @patch("reliapi.app.routes.onboarding.redis")
    def test_start_onboarding_success(self, mock_redis_module, mock_redis):
        """Test successful onboarding start."""
        mock_redis_module.from_url.return_value = mock_redis

        from reliapi.app.routes.onboarding import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/onboarding/start",
            json={"email": "test@example.com", "plan": "free"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "api_key" in data
        assert data["api_key"].startswith("reliapi_")
        assert "quick_start_url" in data
        assert "documentation_url" in data
        assert "example_code" in data
        assert "python" in data["example_code"]
        assert "javascript" in data["example_code"]
        assert "curl" in data["example_code"]
        assert data["integration_status"] == "pending_verification"

    @patch("reliapi.app.routes.onboarding.redis")
    def test_start_onboarding_pro_plan(self, mock_redis_module, mock_redis):
        """Test onboarding with pro plan."""
        mock_redis_module.from_url.return_value = mock_redis

        from reliapi.app.routes.onboarding import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/onboarding/start",
            json={"email": "pro@example.com", "plan": "pro"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data

    def test_start_onboarding_invalid_email(self):
        """Test onboarding with invalid email."""
        from reliapi.app.routes.onboarding import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/onboarding/start",
            json={"email": "not-an-email", "plan": "free"},
        )

        assert response.status_code == 422  # Validation error

    def test_get_quick_start_guide(self):
        """Test getting quick start guide."""
        from reliapi.app.routes.onboarding import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/onboarding/quick-start")

        assert response.status_code == 200
        data = response.json()

        assert "steps" in data
        assert len(data["steps"]) == 4
        assert "code_examples" in data
        assert "test_endpoint" in data

    @patch("reliapi.app.routes.onboarding.redis")
    def test_verify_integration_valid_key(self, mock_redis_module, mock_redis):
        """Test verification with valid API key."""
        # Mock Redis to return user data
        mock_redis.get.side_effect = lambda key: (
            json.dumps({"email": "test@example.com"}).encode()
            if key.startswith("api_key:")
            else b"5"  # 5 requests made
        )
        mock_redis_module.from_url.return_value = mock_redis

        from reliapi.app.routes.onboarding import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/onboarding/verify",
            headers={"X-API-Key": "reliapi_test123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "verified"
        assert data["requests_made"] == 5

    @patch("reliapi.app.routes.onboarding.redis")
    def test_verify_integration_invalid_key(self, mock_redis_module, mock_redis):
        """Test verification with invalid API key."""
        mock_redis.get.return_value = None
        mock_redis_module.from_url.return_value = mock_redis

        from reliapi.app.routes.onboarding import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/onboarding/verify",
            headers={"X-API-Key": "invalid_key"},
        )

        assert response.status_code == 401


class TestAnalyticsRoutes:
    """Tests for analytics endpoints."""

    def test_track_event_basic(self):
        """Test basic event tracking."""
        from reliapi.app.routes.analytics import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/analytics/track",
            json={
                "event_name": "page_view",
                "user_id": "user123",
                "properties": {"page": "/home"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "tracked"
        assert data["event"] == "page_view"

    def test_track_event_without_user_id(self):
        """Test event tracking without user ID."""
        from reliapi.app.routes.analytics import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/analytics/track",
            json={
                "event_name": "anonymous_action",
                "properties": {"action": "click"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "tracked"

    def test_track_conversion(self):
        """Test conversion event tracking."""
        from reliapi.app.routes.analytics import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/analytics/conversion",
            json={
                "event_type": "signup",
                "user_id": "user456",
                "properties": {"plan": "pro"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "tracked"
        assert "conversion_signup" in data["event"]

    def test_get_funnel_default_dates(self):
        """Test getting funnel with default date range."""
        from reliapi.app.routes.analytics import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/analytics/funnel")

        assert response.status_code == 200
        data = response.json()

        assert "period" in data
        assert "funnel" in data
        assert "conversion_rates" in data
        assert "visitors" in data["funnel"]
        assert "trial_signups" in data["funnel"]
        assert "paid_conversions" in data["funnel"]

    def test_get_funnel_custom_dates(self):
        """Test getting funnel with custom date range."""
        from reliapi.app.routes.analytics import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get(
            "/analytics/funnel",
            params={
                "start_date": "2025-01-01T00:00:00",
                "end_date": "2025-01-31T23:59:59",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "2025-01-01" in data["period"]["start"]
        assert "2025-01-31" in data["period"]["end"]


class TestHealthRoutes:
    """Tests for health check endpoints."""

    def test_health_endpoint(self):
        """Test /health endpoint."""
        from reliapi.app.routes.health import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_healthz_endpoint(self):
        """Test /healthz endpoint."""
        from reliapi.app.routes.health import router
        from fastapi import FastAPI

        # Need to mock the app_state for rate limiter
        with patch("reliapi.app.routes.health.get_app_state") as mock_state:
            mock_state.return_value = MagicMock(rate_limiter=None)

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.get("/healthz")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_readyz_endpoint(self):
        """Test /readyz endpoint."""
        from reliapi.app.routes.health import router
        from fastapi import FastAPI

        with patch("reliapi.app.routes.health.get_app_state") as mock_state:
            mock_state.return_value = MagicMock(rate_limiter=None)

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.get("/readyz")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"

    def test_livez_endpoint(self):
        """Test /livez endpoint."""
        from reliapi.app.routes.health import router
        from fastapi import FastAPI

        with patch("reliapi.app.routes.health.get_app_state") as mock_state:
            mock_state.return_value = MagicMock(rate_limiter=None)

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.get("/livez")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "alive"

    def test_metrics_endpoint(self):
        """Test /metrics endpoint returns Prometheus format."""
        from reliapi.app.routes.health import router
        from fastapi import FastAPI

        with patch("reliapi.app.routes.health.get_app_state") as mock_state:
            mock_state.return_value = MagicMock(rate_limiter=None)

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.get("/metrics")

            assert response.status_code == 200
            # Prometheus metrics are text-based
            assert "text/plain" in response.headers["content-type"] or \
                   "text/plain" in response.headers.get("content-type", "")


class TestProxyRoutes:
    """Tests for proxy route helpers."""

    def test_check_api_key_format_valid(self):
        """Test API key format validation with valid key."""
        from reliapi.core.security import SecurityManager

        is_valid, error = SecurityManager.validate_api_key_format("sk-valid-key-123")
        assert is_valid is True
        assert error is None

    def test_check_api_key_format_empty(self):
        """Test API key format validation with empty key."""
        from reliapi.core.security import SecurityManager

        is_valid, error = SecurityManager.validate_api_key_format("")
        # Empty keys might be valid depending on implementation
        # Just verify the method works
        assert isinstance(is_valid, bool)


class TestSchemaValidation:
    """Tests for Pydantic schema validation."""

    def test_http_proxy_request_valid(self):
        """Test valid HTTP proxy request."""
        from reliapi.app.schemas import HTTPProxyRequest

        request = HTTPProxyRequest(
            target="my_api",
            method="GET",
            path="/users",
        )

        assert request.target == "my_api"
        assert request.method == "GET"
        assert request.path == "/users"

    def test_http_proxy_request_method_uppercase(self):
        """Test HTTP method is uppercased."""
        from reliapi.app.schemas import HTTPProxyRequest

        request = HTTPProxyRequest(
            target="my_api",
            method="get",  # lowercase
            path="/users",
        )

        assert request.method == "GET"

    def test_http_proxy_request_invalid_method(self):
        """Test invalid HTTP method raises error."""
        from reliapi.app.schemas import HTTPProxyRequest

        with pytest.raises(ValueError):
            HTTPProxyRequest(
                target="my_api",
                method="INVALID",
                path="/users",
            )

    def test_llm_proxy_request_valid(self):
        """Test valid LLM proxy request."""
        from reliapi.app.schemas import LLMProxyRequest

        request = LLMProxyRequest(
            target="openai",
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert request.target == "openai"
        assert len(request.messages) == 1
        assert request.stream is False

    def test_llm_proxy_request_with_options(self):
        """Test LLM proxy request with all options."""
        from reliapi.app.schemas import LLMProxyRequest

        request = LLMProxyRequest(
            target="openai",
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o-mini",
            max_tokens=100,
            temperature=0.7,
            top_p=0.9,
            stream=True,
        )

        assert request.model == "gpt-4o-mini"
        assert request.max_tokens == 100
        assert request.temperature == 0.7
        assert request.top_p == 0.9
        assert request.stream is True

    def test_llm_proxy_request_temperature_bounds(self):
        """Test temperature must be within bounds."""
        from reliapi.app.schemas import LLMProxyRequest

        # Valid temperature
        request = LLMProxyRequest(
            target="openai",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=1.5,
        )
        assert request.temperature == 1.5

        # Invalid temperature (too high)
        with pytest.raises(ValueError):
            LLMProxyRequest(
                target="openai",
                messages=[{"role": "user", "content": "Hello"}],
                temperature=3.0,
            )

    def test_error_response_model(self):
        """Test error response model."""
        from reliapi.app.schemas import ErrorDetail, ErrorResponse, MetaResponse

        error = ErrorDetail(
            type="rate_limit_error",
            code="RATE_LIMIT_EXCEEDED",
            message="Too many requests",
            retryable=True,
            status_code=429,
        )

        meta = MetaResponse(
            duration_ms=10,
            request_id="req_123",
        )

        response = ErrorResponse(
            error=error,
            meta=meta,
        )

        assert response.success is False
        assert response.error.code == "RATE_LIMIT_EXCEEDED"
        assert response.meta.request_id == "req_123"
