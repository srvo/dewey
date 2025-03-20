"""Test configuration for database tests."""

import os
import pytest
from unittest.mock import Mock, patch

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'MOTHERDUCK_TOKEN': 'test_token',
        'DEWEY_HOME': '/tmp/dewey_test'
    }):
        yield

@pytest.fixture(autouse=True)
def setup_test_db():
    """Set up test database environment."""
    # Create test directory if it doesn't exist
    os.makedirs('/tmp/dewey_test', exist_ok=True)
    yield
    # Clean up test directory
    try:
        os.remove('/tmp/dewey_test/dewey.duckdb')
    except:
        pass

@pytest.fixture
def mock_duckdb():
    """Mock DuckDB connection."""
    with patch('duckdb.connect') as mock_connect:
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        yield mock_conn 