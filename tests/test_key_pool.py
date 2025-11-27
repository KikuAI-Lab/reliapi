"""Tests for provider key pool manager."""
import time
import pytest

from reliapi.core.key_pool import KeyPoolManager, ProviderKey


def test_key_selection_lowest_load_score():
    """Test that key with lowest load score is selected."""
    keys = [
        ProviderKey(id="key1", provider="openai", key="sk-1", qps_limit=10, current_qps=5.0),
        ProviderKey(id="key2", provider="openai", key="sk-2", qps_limit=10, current_qps=2.0),
        ProviderKey(id="key3", provider="openai", key="sk-3", qps_limit=10, current_qps=8.0),
    ]
    
    manager = KeyPoolManager(pools={"openai": keys})
    
    selected = manager.select_key("openai")
    assert selected is not None
    assert selected.id == "key2"  # Lowest load: 2.0/10 = 0.2


def test_key_selection_with_error_penalty():
    """Test that keys with error penalties have higher load scores."""
    keys = [
        ProviderKey(id="key1", provider="openai", key="sk-1", qps_limit=10, current_qps=5.0, recent_error_score=0.0),
        ProviderKey(id="key2", provider="openai", key="sk-2", qps_limit=10, current_qps=5.0, recent_error_score=0.3),
    ]
    
    manager = KeyPoolManager(pools={"openai": keys})
    
    selected = manager.select_key("openai")
    assert selected is not None
    assert selected.id == "key1"  # Lower error score


def test_key_selection_filters_inactive():
    """Test that only active keys are selected."""
    keys = [
        ProviderKey(id="key1", provider="openai", key="sk-1", status="active", qps_limit=10),
        ProviderKey(id="key2", provider="openai", key="sk-2", status="degraded", qps_limit=10),
        ProviderKey(id="key3", provider="openai", key="sk-3", status="exhausted", qps_limit=10),
    ]
    
    manager = KeyPoolManager(pools={"openai": keys})
    
    selected = manager.select_key("openai")
    assert selected is not None
    assert selected.id == "key1"
    assert selected.status == "active"


def test_key_selection_no_active_keys_fallback_to_degraded():
    """Test that degraded keys are used as fallback when no active keys available."""
    keys = [
        ProviderKey(id="key1", provider="openai", key="sk-1", status="degraded"),
        ProviderKey(id="key2", provider="openai", key="sk-2", status="exhausted"),
    ]
    
    manager = KeyPoolManager(pools={"openai": keys})
    
    # Should fallback to degraded key (key1)
    selected = manager.select_key("openai")
    assert selected is not None
    assert selected.id == "key1"
    assert selected.status == "degraded"


def test_key_selection_no_keys_available():
    """Test that None is returned when all keys are exhausted/banned."""
    keys = [
        ProviderKey(id="key1", provider="openai", key="sk-1", status="exhausted"),
        ProviderKey(id="key2", provider="openai", key="sk-2", status="banned"),
    ]
    
    manager = KeyPoolManager(pools={"openai": keys})
    
    selected = manager.select_key("openai")
    assert selected is None


def test_key_selection_no_pool():
    """Test that None is returned when provider has no pool."""
    manager = KeyPoolManager()
    
    selected = manager.select_key("openai")
    assert selected is None


def test_record_success_resets_consecutive_errors():
    """Test that successful request resets consecutive errors."""
    key = ProviderKey(id="key1", provider="openai", key="sk-1", consecutive_errors=3)
    manager = KeyPoolManager(pools={"openai": [key]})
    
    manager.record_success("key1")
    
    assert key.consecutive_errors == 0
    assert key.recent_error_score < 1.0  # Should decay


def test_record_error_429_increases_penalty():
    """Test that 429 errors increase error score by 0.1."""
    key = ProviderKey(id="key1", provider="openai", key="sk-1", recent_error_score=0.0)
    manager = KeyPoolManager(pools={"openai": [key]})
    
    manager.record_error("key1", "429", 429)
    
    assert key.recent_error_score == 0.1
    assert key.consecutive_errors == 1


def test_record_error_5xx_increases_penalty():
    """Test that 5xx errors increase error score by 0.05."""
    key = ProviderKey(id="key1", provider="openai", key="sk-1", recent_error_score=0.0)
    manager = KeyPoolManager(pools={"openai": [key]})
    
    manager.record_error("key1", "5xx", 500)
    
    assert key.recent_error_score == 0.05
    assert key.consecutive_errors == 1


def test_status_transition_active_to_degraded():
    """Test that key transitions to degraded after 5 consecutive errors."""
    key = ProviderKey(id="key1", provider="openai", key="sk-1", status="active")
    manager = KeyPoolManager(pools={"openai": [key]})
    
    for _ in range(5):
        manager.record_error("key1", "429", 429)
    
    assert key.status == "degraded"
    assert key.consecutive_errors == 5


def test_status_transition_degraded_to_exhausted():
    """Test that key transitions to exhausted after 10 consecutive errors."""
    key = ProviderKey(id="key1", provider="openai", key="sk-1", status="active")
    manager = KeyPoolManager(pools={"openai": [key]})
    
    for _ in range(10):
        manager.record_error("key1", "429", 429)
    
    assert key.status == "exhausted"
    assert key.consecutive_errors == 10


def test_status_recovery_degraded_to_active():
    """Test that degraded key recovers to active after success."""
    key = ProviderKey(id="key1", provider="openai", key="sk-1", status="degraded", recent_error_score=0.2)
    manager = KeyPoolManager(pools={"openai": [key]})
    
    manager.record_success("key1")
    
    # Should recover if error score < 0.3
    assert key.status == "active"
    assert key.consecutive_errors == 0


def test_health_score_calculation():
    """Test that health score is calculated correctly."""
    key = ProviderKey(id="key1", provider="openai", key="sk-1", recent_error_score=0.5)
    key.update_health()
    
    # health_score = 1.0 - (error_score / max_error_score)
    # max_error_score = 1.0
    # health_score = 1.0 - 0.5 = 0.5
    assert key.health_score == 0.5


def test_load_score_calculation():
    """Test that load score includes both QPS and error penalty."""
    key = ProviderKey(
        id="key1",
        provider="openai",
        key="sk-1",
        qps_limit=10,
        current_qps=5.0,
        recent_error_score=0.2,
    )
    
    load_score = key.calculate_load_score()
    # load_score = current_qps / qps_limit + penalty
    # load_score = 5.0 / 10 + 0.2 = 0.5 + 0.2 = 0.7
    assert load_score == 0.7


def test_load_score_inactive_key():
    """Test that inactive keys have infinite load score."""
    key = ProviderKey(id="key1", provider="openai", key="sk-1", status="degraded")
    
    load_score = key.calculate_load_score()
    assert load_score == float("inf")


def test_has_pool():
    """Test has_pool method."""
    keys = [ProviderKey(id="key1", provider="openai", key="sk-1")]
    manager = KeyPoolManager(pools={"openai": keys})
    
    assert manager.has_pool("openai") is True
    assert manager.has_pool("anthropic") is False


def test_get_key_status():
    """Test get_key_status method."""
    key = ProviderKey(id="key1", provider="openai", key="sk-1", status="degraded")
    manager = KeyPoolManager(pools={"openai": [key]})
    
    assert manager.get_key_status("key1") == "degraded"
    assert manager.get_key_status("nonexistent") is None


def test_qps_tracking():
    """Test that QPS is tracked correctly."""
    key = ProviderKey(id="key1", provider="openai", key="sk-1")
    manager = KeyPoolManager(pools={"openai": [key]})
    
    # Simulate multiple requests
    for _ in range(5):
        manager._update_qps("key1")
        time.sleep(0.1)
    
    # QPS should be calculated over 10 second window
    # With 5 requests in ~0.5 seconds, QPS should be around 10
    assert key.current_qps > 0


def test_backward_compatibility_no_pool():
    """Test backward compatibility: no pool means fallback to targets.auth."""
    manager = KeyPoolManager()
    
    assert manager.has_pool("openai") is False
    assert manager.select_key("openai") is None

