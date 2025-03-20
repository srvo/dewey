"""Test configuration for database tests."""

import os
import pytest
from unittest.mock import Mock, patch
import sys

# Import compatibility classes from the root conftest
from tests.unit.conftest import ConnectionPool, DatabaseManager, ConnectionError

# Override the imports for these classes to use our compatibility versions
sys.modules["dewey.core.db.connection"] = type(
    "ConnectionModule",
    (),
    {
        "ConnectionPool": ConnectionPool,
        "DatabaseManager": DatabaseManager,
    },
)

# Add errors module to namespace
sys.modules["dewey.core.db.errors"] = type(
    "ErrorsModule",
    (),
    {
        "ConnectionError": ConnectionError,
    },
)


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(
        os.environ, {"MOTHERDUCK_TOKEN": "test_token", "DEWEY_HOME": "/tmp/dewey_test"}
    ):
        yield


@pytest.fixture(autouse=True)
def setup_test_db():
    """Set up test database environment."""
    # Create test directory if it doesn't exist
    os.makedirs("/tmp/dewey_test", exist_ok=True)
    yield
    # Clean up test directory
    try:
        os.remove("/tmp/dewey_test/dewey.duckdb")
    except Exception:
        pass


@pytest.fixture
def mock_duckdb_connect():
    """Mock DuckDB connect function."""
    with patch("duckdb.connect") as mock_connect:
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        yield mock_connect, mock_conn


@pytest.fixture
def mock_database_connection():
    """Mock DatabaseConnection instance."""
    mock_conn = Mock()
    mock_conn.execute.return_value.fetchdf.return_value = Mock()
    mock_conn.execute.return_value.fetchall.return_value = [(1, "test")]
    yield mock_conn
