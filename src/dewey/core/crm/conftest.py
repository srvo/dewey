"""Test configuration for database tests."""

import os
import pytest
from unittest.mock import Mock, patch
from dewey.core.base_script import BaseScript


class TestConfiguration(BaseScript):
    """Test configuration for database tests."""

    def __init__(self):
        """Initialize the test configuration."""
        super().__init__(config_section='test_config')

    def mock_env_vars(self):
        """Mock environment variables for testing."""
        with patch.dict(os.environ, {
            'MOTHERDUCK_TOKEN': self.config.get('motherduck_token', 'test_token'),
            'DEWEY_HOME': '/tmp/dewey_test'
        }):
            yield

    def setup_test_db(self):
        """Set up test database environment."""
        # Create test directory if it doesn't exist
        os.makedirs('/tmp/dewey_test', exist_ok=True)
        yield
        # Clean up test directory
        try:
            os.remove('/tmp/dewey_test/dewey.duckdb')
        except:
            pass

    def mock_duckdb(self):
        """Mock DuckDB connection."""
        with patch('duckdb.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            yield mock_conn


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Fixture to mock environment variables using TestConfiguration."""
    test_config = TestConfiguration()
    with test_config.mock_env_vars():
        yield


@pytest.fixture(autouse=True)
def setup_test_db():
    """Fixture to set up test database environment using TestConfiguration."""
    test_config = TestConfiguration()
    with test_config.setup_test_db():
        yield


@pytest.fixture
def mock_duckdb():
    """Fixture to mock DuckDB connection using TestConfiguration."""
    test_config = TestConfiguration()
    with test_config.mock_duckdb():
        yield