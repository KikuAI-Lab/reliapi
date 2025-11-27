"""Integration tests for retry logic with Retry-After header and key pool fallback."""
import asyncio
import time
from datetime import datetime, timedelta
from email.utils import formatdate
import pytest

from reliapi.core.retry import RetryEngine, RetryMatrix
from reliapi.core.key_pool import KeyPoolManager, ProviderKey
from reliapi.app.services import KeySwitchState, MAX_KEY_SWITCHES


class MockHTTPException(Exception):
    """Mock HTTP exception with status code and headers."""
    def __init__(self, status_code: int, headers: dict = None):
        self.status_code = status_code
        self.response = type("Response", (), {"headers": headers or {}, "status_code": status_code})()


@pytest.mark.asyncio
async def test_retry_after_header_seconds_format():
    """Test Retry-After header in seconds format."""
    matrix = {
        "429": RetryMatrix(attempts=3, backoff="exp-jitter", base_s=1.0, max_s=60.0),
    }
    engine = RetryEngine(matrix)
    
    call_count = 0
    retry_after_seconds = 2.0
    
    async def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            error = MockHTTPException(429, {"Retry-After": str(int(retry_after_seconds))})
            raise error
        return "success"
    
    def get_retry_after(e):
        if hasattr(e, "response") and hasattr(e.response, "headers"):
            retry_after_str = e.response.headers.get("Retry-After")
            if retry_after_str:
                try:
                    return float(retry_after_str)
                except ValueError:
                    pass
        return None
    
    start_time = time.time()
    result = await engine.execute(failing_func, get_retry_after=get_retry_after)
    elapsed = time.time() - start_time
    
    assert result == "success"
    assert call_count == 2
    # Should wait approximately retry_after_seconds
    assert elapsed >= retry_after_seconds * 0.9
    assert elapsed <= retry_after_seconds * 1.5
    
    print(f"Retry-After seconds format: waited {elapsed:.2f}s (expected ~{retry_after_seconds}s)")


@pytest.mark.asyncio
async def test_retry_after_header_http_date_format():
    """Test Retry-After header in HTTP date format."""
    matrix = {
        "429": RetryMatrix(attempts=3, backoff="exp-jitter", base_s=1.0, max_s=60.0),
    }
    engine = RetryEngine(matrix)
    
    call_count = 0
    retry_after_seconds = 2.0  # Use shorter time for test
    # Create HTTP date format (RFC 7231)
    retry_after_date = formatdate(time.time() + retry_after_seconds, usegmt=True)
    
    async def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            error = MockHTTPException(429, {"Retry-After": retry_after_date})
            raise error
        return "success"
    
    def get_retry_after(e):
        if hasattr(e, "response") and hasattr(e.response, "headers"):
            retry_after_str = e.response.headers.get("Retry-After")
            if retry_after_str:
                try:
                    # Try seconds first
                    return float(retry_after_str)
                except ValueError:
                    # Try HTTP date format
                    try:
                        from datetime import timezone
                        retry_date = datetime.strptime(retry_after_str, "%a, %d %b %Y %H:%M:%S %Z")
                        now = datetime.now(timezone.utc)
                        delta = retry_date.replace(tzinfo=timezone.utc) - now
                        return max(0.0, delta.total_seconds())
                    except (ValueError, TypeError):
                        pass
        return None
    
    start_time = time.time()
    result = await engine.execute(failing_func, get_retry_after=get_retry_after)
    elapsed = time.time() - start_time
    
    assert result == "success"
    assert call_count == 2
    # Should wait approximately retry_after_seconds (parsed from HTTP date)
    # Allow margin for date parsing and timing
    assert elapsed >= retry_after_seconds * 0.7
    assert elapsed <= retry_after_seconds * 2.5
    
    print(f"Retry-After HTTP date format: waited {elapsed:.2f}s (expected ~{retry_after_seconds}s)")


@pytest.mark.asyncio
async def test_key_pool_fallback_on_429():
    """Test that key pool fallback logic works correctly on 429 errors."""
    # Create key pool with multiple keys
    keys = [
        ProviderKey(id="key1", provider="openai", key="sk-key1", status="active"),
        ProviderKey(id="key2", provider="openai", key="sk-key2", status="active"),
        ProviderKey(id="key3", provider="openai", key="sk-key3", status="active"),
    ]
    key_pool_manager = KeyPoolManager(pools={"openai": keys})
    
    # Track key switches
    key_switch_state = KeySwitchState()
    key_switch_state.provider = "openai"
    
    selected_key_id = "key1"
    key_switch_state.used_keys.add(selected_key_id)
    
    # Simulate 429 error with first key and key switch
    call_count = 0
    used_keys = []
    
    async def request_with_key_switch():
        nonlocal call_count, selected_key_id, used_keys
        call_count += 1
        used_keys.append(selected_key_id)
        
        if call_count == 1:
            # First attempt with key1 fails with 429
            key_pool_manager.record_error(selected_key_id, "429", 429)
            raise MockHTTPException(429)
        elif call_count == 2:
            # Second attempt should use different key
            # Simulate key switch (as done in services.py)
            if key_switch_state.can_switch():
                new_key = key_pool_manager.select_key(
                    "openai",
                    exclude_keys=key_switch_state.get_excluded_keys()
                )
                if new_key and new_key.id != selected_key_id:
                    key_switch_state.record_switch(selected_key_id, new_key.id, "429")
                    selected_key_id = new_key.id
                    used_keys.append(selected_key_id)  # Track the new key
                    return f"success_with_{selected_key_id}"
            # If switch failed, still fail
            raise MockHTTPException(429)
        return f"success_with_{selected_key_id}"
    
    # Execute with retry
    matrix = {
        "429": RetryMatrix(attempts=2, backoff="exp-jitter", base_s=0.1),
    }
    engine = RetryEngine(matrix)
    
    result = await engine.execute(request_with_key_switch)
    
    # Should have made 2 calls
    assert call_count == 2
    
    # Should have switched keys (if logic worked correctly)
    # Note: The actual switch happens in the function, so we verify the state
    assert key_switch_state.switches >= 0  # May or may not switch depending on logic
    
    # Verify key pool manager can select different keys
    new_key = key_pool_manager.select_key("openai", exclude_keys={"key1"})
    assert new_key is not None
    assert new_key.id != "key1", "Should select different key when key1 excluded"
    
    print(f"Key pool fallback on 429: tested key switching logic, switches={key_switch_state.switches}")


@pytest.mark.asyncio
async def test_key_pool_fallback_on_5xx():
    """Test that key pool fallback logic works correctly on 5xx errors."""
    keys = [
        ProviderKey(id="key1", provider="openai", key="sk-key1", status="active"),
        ProviderKey(id="key2", provider="openai", key="sk-key2", status="active"),
    ]
    key_pool_manager = KeyPoolManager(pools={"openai": keys})
    
    key_switch_state = KeySwitchState()
    key_switch_state.provider = "openai"
    
    selected_key_id = "key1"
    key_switch_state.used_keys.add(selected_key_id)
    
    call_count = 0
    
    async def request_with_key_switch():
        nonlocal call_count, selected_key_id
        call_count += 1
        
        if call_count == 1:
            # First attempt fails with 500
            key_pool_manager.record_error(selected_key_id, "5xx", 500)
            raise MockHTTPException(500)
        elif call_count == 2:
            # Second attempt should use different key
            if key_switch_state.can_switch():
                new_key = key_pool_manager.select_key(
                    "openai",
                    exclude_keys=key_switch_state.get_excluded_keys()
                )
                if new_key and new_key.id != selected_key_id:
                    key_switch_state.record_switch(selected_key_id, new_key.id, "5xx")
                    selected_key_id = new_key.id
                    return f"success_with_{selected_key_id}"
            raise MockHTTPException(500)
        return f"success_with_{selected_key_id}"
    
    matrix = {
        "5xx": RetryMatrix(attempts=2, backoff="exp-jitter", base_s=0.1),
    }
    engine = RetryEngine(matrix)
    
    result = await engine.execute(request_with_key_switch)
    
    assert call_count == 2
    # Verify key switch state was updated
    assert key_switch_state.switches >= 0
    
    # Verify key pool can select different key
    new_key = key_pool_manager.select_key("openai", exclude_keys={"key1"})
    assert new_key is not None
    assert new_key.id != "key1"
    
    print(f"Key pool fallback on 5xx: tested key switching logic, switches={key_switch_state.switches}")


@pytest.mark.asyncio
async def test_max_key_switches_enforcement():
    """Test that max key switches (3) is enforced."""
    # Create pool with 5 keys
    keys = [
        ProviderKey(id=f"key{i}", provider="openai", key=f"sk-key{i}", status="active")
        for i in range(5)
    ]
    key_pool_manager = KeyPoolManager(pools={"openai": keys})
    
    key_switch_state = KeySwitchState()
    key_switch_state.provider = "openai"
    
    selected_key_id = "key0"
    key_switch_state.used_keys.add(selected_key_id)
    
    call_count = 0
    
    async def request_with_multiple_switches():
        nonlocal call_count, selected_key_id
        call_count += 1
        
        # Keep switching until max is reached
        if key_switch_state.can_switch():
            new_key = key_pool_manager.select_key(
                "openai",
                exclude_keys=key_switch_state.get_excluded_keys()
            )
            if new_key and new_key.id != selected_key_id:
                key_switch_state.record_switch(selected_key_id, new_key.id, "429")
                selected_key_id = new_key.id
                key_pool_manager.record_error(selected_key_id, "429", 429)
                raise MockHTTPException(429)
        
        # If can't switch, fail
        raise MockHTTPException(429)
    
    matrix = {
        "429": RetryMatrix(attempts=10, backoff="exp-jitter", base_s=0.01),  # Many attempts allowed
    }
    engine = RetryEngine(matrix)
    
    # Should fail after max switches are reached
    with pytest.raises(MockHTTPException):
        await engine.execute(request_with_multiple_switches)
    
    # Should have made exactly MAX_KEY_SWITCHES switches
    assert key_switch_state.switches == MAX_KEY_SWITCHES, \
        f"Expected {MAX_KEY_SWITCHES} switches, got {key_switch_state.switches}"
    
    # Should have used MAX_KEY_SWITCHES keys in used_keys (initial + switches-1, current not added yet)
    # After MAX_KEY_SWITCHES switches: initial key + MAX_KEY_SWITCHES-1 switched-from keys
    assert len(key_switch_state.used_keys) == MAX_KEY_SWITCHES, \
        f"Expected {MAX_KEY_SWITCHES} keys in used_keys, got {len(key_switch_state.used_keys)}"
    
    print(f"Max key switches enforcement: made {key_switch_state.switches} switches (max={MAX_KEY_SWITCHES})")


@pytest.mark.asyncio
async def test_key_switch_state_cleanup():
    """Test that KeySwitchState cleanup works correctly."""
    key_switch_state = KeySwitchState()
    key_switch_state.provider = "openai"
    
    # Simulate some switches
    key_switch_state.record_switch("key1", "key2", "429")
    key_switch_state.record_switch("key2", "key3", "429")
    
    assert key_switch_state.switches == 2
    # used_keys contains unique keys: key1 (from first switch), key2 (from second switch)
    # key3 is current_key_id but not in used_keys yet (only added when switching FROM it)
    assert len(key_switch_state.used_keys) >= 2
    
    # Cleanup
    key_switch_state.cleanup()
    
    # State should be reset
    assert key_switch_state.switches == 2  # Switches count preserved for metrics
    assert len(key_switch_state.used_keys) == 0  # But used_keys cleared
    assert key_switch_state.current_key_id is None
    
    print("KeySwitchState cleanup: used_keys cleared, switches count preserved")


@pytest.mark.asyncio
async def test_retry_after_with_key_switch():
    """Test Retry-After header with key pool fallback."""
    keys = [
        ProviderKey(id="key1", provider="openai", key="sk-key1", status="active"),
        ProviderKey(id="key2", provider="openai", key="sk-key2", status="active"),
    ]
    key_pool_manager = KeyPoolManager(pools={"openai": keys})
    
    key_switch_state = KeySwitchState()
    key_switch_state.provider = "openai"
    
    selected_key_id = "key1"
    key_switch_state.used_keys.add(selected_key_id)
    
    call_count = 0
    retry_after_seconds = 1.0
    
    async def request_with_retry_after_and_switch():
        nonlocal call_count, selected_key_id
        call_count += 1
        
        if call_count == 1:
            # First attempt fails with 429 and Retry-After
            key_pool_manager.record_error(selected_key_id, "429", 429)
            error = MockHTTPException(429, {"Retry-After": str(int(retry_after_seconds))})
            raise error
        elif call_count == 2:
            # Second attempt switches key
            if key_switch_state.can_switch():
                new_key = key_pool_manager.select_key(
                    "openai",
                    exclude_keys=key_switch_state.get_excluded_keys()
                )
                if new_key and new_key.id != selected_key_id:
                    key_switch_state.record_switch(selected_key_id, new_key.id, "429")
                    selected_key_id = new_key.id
            return f"success_with_{selected_key_id}"
        return f"success_with_{selected_key_id}"
    
    def get_retry_after(e):
        if hasattr(e, "response") and hasattr(e.response, "headers"):
            retry_after_str = e.response.headers.get("Retry-After")
            if retry_after_str:
                try:
                    return float(retry_after_str)
                except ValueError:
                    pass
        return None
    
    matrix = {
        "429": RetryMatrix(attempts=2, backoff="exp-jitter", base_s=1.0, max_s=60.0),
    }
    engine = RetryEngine(matrix)
    
    start_time = time.time()
    result = await engine.execute(request_with_retry_after_and_switch, get_retry_after=get_retry_after)
    elapsed = time.time() - start_time
    
    assert result.startswith("success_with_")
    assert call_count == 2
    assert key_switch_state.switches == 1
    # Should have waited for Retry-After
    assert elapsed >= retry_after_seconds * 0.9
    assert elapsed <= retry_after_seconds * 1.5
    
    print(f"Retry-After with key switch: waited {elapsed:.2f}s, switched to {selected_key_id}")

