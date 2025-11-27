"""Pytest configuration and fixtures."""
import pytest
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = Mock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.setex.return_value = True
    mock.setnx.return_value = True
    mock.exists.return_value = 0
    mock.delete.return_value = 1
    mock.keys.return_value = []
    return mock


@pytest.fixture
def mock_redis_pipeline():
    """Mock Redis pipeline."""
    mock = Mock()
    mock.execute.return_value = [True, True]
    return mock

