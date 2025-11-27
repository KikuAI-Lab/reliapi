"""Tests for app/services.py handle_llm_proxy."""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from reliapi.app.services import handle_llm_proxy
from reliapi.app.schemas import SuccessResponse, ErrorResponse
from reliapi.core.cache import Cache
from reliapi.core.idempotency import IdempotencyManager


@pytest.fixture
def mock_targets():
    """Mock targets configuration."""
    return {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "timeout_ms": 20000,
            "circuit": {"error_threshold": 5, "cooldown_s": 60},
            "cache": {"enabled": True, "ttl_s": 3600},
            "llm": {
                "provider": "openai",
                "default_model": "gpt-4o-mini",
                "max_tokens": 1024,
                "hard_cost_cap_usd": 0.05,
            },
            "auth": {"type": "bearer_env", "env_var": "OPENAI_API_KEY"},
        }
    }


@pytest.fixture
def mock_cache():
    """Mock cache."""
    cache = Mock(spec=Cache)
    cache.enabled = True
    cache.get.return_value = None
    cache.set.return_value = None
    return cache


@pytest.fixture
def mock_idempotency():
    """Mock idempotency manager."""
    manager = Mock(spec=IdempotencyManager)
    manager.enabled = True
    manager.register_request.return_value = (True, None, None)
    manager.get_result.return_value = None
    manager.is_in_progress.return_value = False
    manager.mark_in_progress.return_value = None
    manager.clear_in_progress.return_value = None
    return manager


@pytest.mark.asyncio
async def test_llm_proxy_budget_cap_rejection(mock_targets, mock_cache, mock_idempotency):
    """Test that budget cap rejection works."""
    with patch("reliapi.app.services.CostEstimator") as mock_cost:
        mock_cost.estimate_from_messages.return_value = 0.1  # Exceeds hard cap of 0.05
        
        result = await handle_llm_proxy(
            target_name="openai",
            messages=[{"role": "user", "content": "Hello"}],
            model=None,
            max_tokens=None,
            temperature=None,
            top_p=None,
            stop=None,
            stream=False,
            idempotency_key=None,
            cache_ttl=None,
            targets=mock_targets,
            cache=mock_cache,
            idempotency=mock_idempotency,
            request_id="test-123",
            tenant=None,
        )
        
        assert isinstance(result, ErrorResponse)
        assert result.error.code == "BUDGET_EXCEEDED"
        assert result.meta.cost_policy_applied == "hard_cap_rejected"


@pytest.mark.asyncio
async def test_llm_proxy_target_not_found(mock_cache, mock_idempotency):
    """Test error when target is not found."""
    result = await handle_llm_proxy(
        target_name="nonexistent",
        messages=[{"role": "user", "content": "Hello"}],
        model=None,
        max_tokens=None,
        temperature=None,
        top_p=None,
        stop=None,
        stream=False,
        idempotency_key=None,
        cache_ttl=None,
        targets={},
        cache=mock_cache,
        idempotency=mock_idempotency,
        request_id="test-123",
        tenant=None,
    )
    
    assert isinstance(result, ErrorResponse)
    assert result.error.code == "NOT_FOUND"

