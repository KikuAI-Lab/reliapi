"""Tests for core/circuit_breaker.py."""
import time
import pytest

from reliapi.core.circuit_breaker import CircuitBreaker


def test_circuit_breaker_closed_to_open():
    """Test circuit breaker transitions: closed → open."""
    cb = CircuitBreaker(failures_to_open=3, open_ttl_s=60)
    
    # Start closed
    assert cb.is_open("upstream1") is False
    assert cb.get_state("upstream1") == "closed"
    
    # Record failures
    cb.record_failure("upstream1")
    assert cb.get_state("upstream1") == "half-open"
    
    cb.record_failure("upstream1")
    cb.record_failure("upstream1")  # Third failure opens circuit
    
    assert cb.is_open("upstream1") is True
    assert cb.get_state("upstream1") == "open"


def test_circuit_breaker_open_to_closed():
    """Test circuit breaker auto-closes after TTL."""
    cb = CircuitBreaker(failures_to_open=2, open_ttl_s=1)  # Short TTL for testing
    
    # Open circuit
    cb.record_failure("upstream1")
    cb.record_failure("upstream1")
    assert cb.is_open("upstream1") is True
    
    # Wait for TTL
    time.sleep(1.1)
    
    # Should auto-close
    assert cb.is_open("upstream1") is False
    assert cb.get_state("upstream1") == "closed"


def test_circuit_breaker_success_resets():
    """Test that success resets failure count."""
    cb = CircuitBreaker(failures_to_open=3, open_ttl_s=60)
    
    # Record failures
    cb.record_failure("upstream1")
    cb.record_failure("upstream1")
    assert cb.get_state("upstream1") == "half-open"
    
    # Success resets
    cb.record_success("upstream1")
    assert cb.get_state("upstream1") == "closed"
    assert cb.is_open("upstream1") is False

