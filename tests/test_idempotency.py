"""Tests for core/idempotency.py."""
import json
import pytest
import asyncio
from unittest.mock import Mock, patch

from reliapi.core.idempotency import IdempotencyManager


@patch('reliapi.core.idempotency.redis')
def test_idempotency_single_request(mock_redis_module, mock_redis):
    """Test single idempotency request registration."""
    mock_redis_module.from_url.return_value = mock_redis
    manager = IdempotencyManager("redis://localhost:6379/0")
    
    # Mock SETNX to return True (first caller)
    mock_redis.pipeline.return_value.execute.return_value = [True, True]
    mock_redis.pipeline.return_value.setnx.return_value = mock_redis.pipeline.return_value
    mock_redis.pipeline.return_value.expire.return_value = mock_redis.pipeline.return_value
    
    is_new, existing_id, existing_hash = manager.register_request(
        "key-123", "POST", "https://example.com", None, b"body", "req-1"
    )
    
    assert is_new is True
    assert existing_id is None
    assert existing_hash is None


@patch('reliapi.core.idempotency.redis')
def test_idempotency_existing_request(mock_redis_module, mock_redis):
    """Test idempotency with existing request."""
    mock_redis_module.from_url.return_value = mock_redis
    manager = IdempotencyManager("redis://localhost:6379/0")
    
    # Mock existing request
    existing_data = {
        "request_id": "req-1",
        "request_hash": "hash-123",
        "created_at": 1234567890
    }
    mock_redis.get.return_value = json.dumps(existing_data)
    
    is_new, existing_id, existing_hash = manager.register_request(
        "key-123", "POST", "https://example.com", None, b"body", "req-2"
    )
    
    assert is_new is False
    assert existing_id == "req-1"
    assert existing_hash == "hash-123"


@pytest.mark.asyncio
@patch('reliapi.core.idempotency.redis')
async def test_idempotency_concurrent_requests(mock_redis_module, mock_redis):
    """Test concurrent requests with same idempotency key."""
    mock_redis_module.from_url.return_value = mock_redis
    manager = IdempotencyManager("redis://localhost:6379/0")
    
    # First caller succeeds with SETNX
    # Second caller gets False from SETNX
    pipeline_mock = Mock()
    pipeline_mock.setnx.return_value = pipeline_mock
    pipeline_mock.expire.return_value = pipeline_mock
    
    # First call: SETNX returns True
    pipeline_mock.execute.return_value = [True, True]
    mock_redis.pipeline.return_value = pipeline_mock
    
    async def register_first():
        return manager.register_request("key-123", "POST", "https://example.com", None, b"body", "req-1")
    
    async def register_second():
        # Second call: SETNX returns False (already exists)
        pipeline_mock.execute.return_value = [False, True]
        mock_redis.get.return_value = json.dumps({
            "request_id": "req-1",
            "request_hash": "hash-123",
            "created_at": 1234567890
        })
        return manager.register_request("key-123", "POST", "https://example.com", None, b"body", "req-2")
    
    result1, result2 = await asyncio.gather(register_first(), register_second())
    
    # First should be new, second should see existing
    assert result1[0] is True  # First caller owns the request
    assert result2[0] is False  # Second caller sees existing


def test_idempotency_disabled():
    """Test idempotency behavior when Redis is unavailable."""
    manager = IdempotencyManager("redis://invalid:6379/0")
    assert manager.enabled is False
    
    is_new, existing_id, existing_hash = manager.register_request(
        "key-123", "POST", "https://example.com", None, b"body", "req-1"
    )
    
    # Should gracefully degrade
    assert is_new is True
    assert existing_id is None

