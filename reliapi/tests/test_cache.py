"""Tests for core/cache.py."""
import json
import pytest
from unittest.mock import Mock, patch

from reliapi.core.cache import Cache


@patch('reliapi.core.cache.redis')
def test_cache_get_set(mock_redis_module, mock_redis):
    """Test basic cache get/set operations."""
    mock_redis_module.from_url.return_value = mock_redis
    cache = Cache("redis://localhost:6379/0")
    
    # Test set
    cache.set("GET", "https://example.com", None, None, {"data": "test"}, ttl_s=60)
    mock_redis.setex.assert_called_once()
    
    # Test get with cached value
    mock_redis.get.return_value = json.dumps({"data": "test"})
    result = cache.get("GET", "https://example.com", None, None, None)
    assert result == {"data": "test"}


@patch('reliapi.core.cache.redis')
def test_cache_ttl(mock_redis_module, mock_redis):
    """Test TTL behavior."""
    mock_redis_module.from_url.return_value = mock_redis
    cache = Cache("redis://localhost:6379/0")
    
    cache.set("GET", "https://example.com", None, None, {"data": "test"}, ttl_s=300)
    
    # Verify TTL was set
    call_args = mock_redis.setex.call_args
    assert call_args[0][1] == 300  # TTL in seconds


def test_cache_disabled():
    """Test cache behavior when Redis is unavailable."""
    cache = Cache("redis://invalid:6379/0")
    assert cache.enabled is False
    
    result = cache.get("GET", "https://example.com", None, None, None)
    assert result is None
    
    cache.set("GET", "https://example.com", None, None, {"data": "test"}, ttl_s=60)
    # Should not crash, just silently fail


@patch('reliapi.core.cache.redis')
def test_cache_post_not_cached(mock_redis_module, mock_redis):
    """Test that POST requests are not cached by default."""
    mock_redis_module.from_url.return_value = mock_redis
    cache = Cache("redis://localhost:6379/0")
    
    cache.set("POST", "https://example.com", None, b"body", {"data": "test"}, ttl_s=60)
    # Should not call Redis
    mock_redis.setex.assert_not_called()

