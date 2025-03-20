"""Tests for database connection management."""

import pytest
from unittest.mock import Mock, patch
import duckdb

from dewey.core.db.connection import ConnectionPool, DatabaseManager
from dewey.core.db.errors import ConnectionError


@pytest.fixture
def connection_pool():
    """Create a test connection pool."""
    pool = ConnectionPool("test.db", pool_size=2)
    yield pool
    pool.close_all()


@pytest.fixture
def db_manager():
    """Create a test database manager."""
    manager = DatabaseManager()
    yield manager
    manager.close()


def test_connection_pool_creation():
    """Test creating a connection pool."""
    pool = ConnectionPool("test.db", pool_size=3)
    assert pool.pool_size == 3
    assert len(pool.connections) == 0
    pool.close_all()


def test_get_connection():
    """Test getting a connection from the pool."""
    with patch("duckdb.connect") as mock_connect:
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        pool = ConnectionPool("test.db", pool_size=2)
        conn = pool.get_connection()

        assert conn == mock_conn
        assert len(pool.connections) == 1
        assert pool.in_use[conn] is True

        pool.close_all()


def test_connection_pool_exhaustion():
    """Test behavior when pool is exhausted."""
    with patch("duckdb.connect") as mock_connect:
        mock_connect.side_effect = [Mock(), Mock()]

        pool = ConnectionPool("test.db", pool_size=2)
        conn1 = pool.get_connection()
        conn2 = pool.get_connection()

        with pytest.raises(ConnectionError):
            pool.get_connection(timeout=0.1)

        pool.close_all()


def test_release_connection():
    """Test releasing a connection back to the pool."""
    with patch("duckdb.connect") as mock_connect:
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        pool = ConnectionPool("test.db", pool_size=2)
        conn = pool.get_connection()
        assert pool.in_use[conn] is True

        pool.release_connection(conn)
        assert pool.in_use[conn] is False

        pool.close_all()


def test_connection_health_check():
    """Test connection health checking."""
    with patch("duckdb.connect") as mock_connect:
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        pool = ConnectionPool("test.db", pool_size=2)
        conn = pool.get_connection()

        # Test healthy connection
        mock_conn.execute.return_value = True
        assert pool._test_connection(conn) is True

        # Test unhealthy connection
        mock_conn.execute.side_effect = Exception("Connection lost")
        assert pool._test_connection(conn) is False

        pool.close_all()


def test_db_manager_online_check():
    """Test MotherDuck online status checking."""
    with patch("dewey.core.db.connection.ConnectionPool") as mock_pool:
        manager = DatabaseManager()

        # Test online status
        mock_conn = Mock()
        mock_pool.return_value.get_connection.return_value = mock_conn
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.execute.return_value = True

        assert manager.is_online() is True
        assert manager.offline_mode is False

        # Test offline status
        mock_conn.execute.side_effect = Exception("Connection failed")
        assert manager.is_online() is False
        assert manager.offline_mode is True

        manager.close()


def test_db_manager_execute_query():
    """Test query execution through DatabaseManager."""
    with patch("dewey.core.db.connection.ConnectionPool") as mock_pool:
        manager = DatabaseManager()
        mock_conn = Mock()
        mock_pool.return_value.get_connection.return_value = mock_conn
        mock_conn.__enter__.return_value = mock_conn

        # Test successful query
        mock_conn.execute.return_value.fetchall.return_value = [(1, "test")]
        result = manager.execute_query("SELECT * FROM test")
        assert result == [(1, "test")]

        # Test failed query
        mock_conn.execute.side_effect = Exception("Query failed")
        with pytest.raises(ConnectionError):
            manager.execute_query("SELECT * FROM test")

        manager.close()


def test_write_connection_management():
    """Test write connection management."""
    with patch("dewey.core.db.connection.ConnectionPool") as mock_pool:
        manager = DatabaseManager()
        mock_conn = Mock()
        mock_pool.return_value.get_connection.return_value = mock_conn

        # Test write connection creation
        with manager.get_connection(for_write=True) as conn:
            assert conn == mock_conn
            assert manager.write_conn == mock_conn

        # Test write connection reuse
        with manager.get_connection(for_write=True) as conn:
            assert conn == mock_conn
            assert manager.write_conn == mock_conn

        manager.close()
