"""Tests for client profile manager."""
import pytest

from reliapi.core.client_profile import ClientProfile, ClientProfileManager


def test_client_profile_default():
    """Test default client profile."""
    profile = ClientProfile()
    
    assert profile.max_parallel_requests == 10
    assert profile.max_qps_per_tenant is None
    assert profile.max_qps_per_provider_key is None
    assert profile.burst_size == 5
    assert profile.default_timeout_s is None


def test_client_profile_custom():
    """Test custom client profile."""
    profile = ClientProfile(
        max_parallel_requests=4,
        max_qps_per_tenant=3.0,
        max_qps_per_provider_key=2.0,
        burst_size=2,
        default_timeout_s=60,
    )
    
    assert profile.max_parallel_requests == 4
    assert profile.max_qps_per_tenant == 3.0
    assert profile.max_qps_per_provider_key == 2.0
    assert profile.burst_size == 2
    assert profile.default_timeout_s == 60


def test_client_profile_manager_get_profile_header_priority():
    """Test that X-Client header has highest priority."""
    profiles = {
        "cursor_default": ClientProfile(max_parallel_requests=4),
        "api_default": ClientProfile(max_parallel_requests=10),
        "default": ClientProfile(max_parallel_requests=20),
    }
    manager = ClientProfileManager(profiles)
    
    # Header should win over tenant profile
    profile = manager.get_profile(profile_name="cursor_default", tenant_profile="api_default")
    assert profile.max_parallel_requests == 4


def test_client_profile_manager_get_profile_tenant_fallback():
    """Test that tenant profile is used when header absent."""
    profiles = {
        "api_default": ClientProfile(max_parallel_requests=10),
        "default": ClientProfile(max_parallel_requests=20),
    }
    manager = ClientProfileManager(profiles)
    
    # Tenant profile should be used
    profile = manager.get_profile(profile_name=None, tenant_profile="api_default")
    assert profile.max_parallel_requests == 10


def test_client_profile_manager_get_profile_default_fallback():
    """Test that default profile is used when header and tenant absent."""
    profiles = {
        "default": ClientProfile(max_parallel_requests=20),
    }
    manager = ClientProfileManager(profiles)
    
    # Default should be used
    profile = manager.get_profile(profile_name=None, tenant_profile=None)
    assert profile.max_parallel_requests == 20


def test_client_profile_manager_has_profile():
    """Test has_profile method."""
    profiles = {
        "cursor_default": ClientProfile(),
        "default": ClientProfile(),
    }
    manager = ClientProfileManager(profiles)
    
    assert manager.has_profile("cursor_default") is True
    assert manager.has_profile("api_default") is False
    assert manager.has_profile("default") is True


def test_client_profile_manager_default_always_exists():
    """Test that default profile always exists."""
    manager = ClientProfileManager()
    
    assert manager.has_profile("default") is True
    profile = manager.get_profile()
    assert profile.max_parallel_requests == 10  # Default value

