"""Tests for database connection management."""

import pytest
from unittest.mock import patch
import duckdb
import time

from dewey.core.db.connection import (
    ConnectionPool,
    DatabaseManager,
    DatabaseConnectionError,
    get_connection,
)


class TestConnectionPool:
    """Test suite for ConnectionPool."""

    @pytest.fixture
    def pool(self):
        """Create a test connection pool."""
        pool = ConnectionPool(":memory:", pool_size=2)
        yield pool
        pool.close_all()

    def test_initialization(self, pool):
        """Test pool initialization."""
        assert pool.db_url == ":memory:"
        assert pool.pool_size == 2
        assert len(pool.connections) == 0
        assert len(pool.in_use) == 0

    def test_create_connection(self, pool):
        """Test connection creation."""
        conn = pool._create_connection()
        assert isinstance(conn, duckdb.DuckDBPyConnection)
        conn.close()

    def test_test_connection(self, pool):
        """Test connection health check."""
        conn = pool._create_connection()
        assert pool._test_connection(conn) is True
        conn.close()
        assert pool._test_connection(conn) is False

    def test_remove_connection(self, pool):
        """Test connection removal."""
        conn = pool._create_connection()
        pool.connections.append(conn)
        pool.in_use[conn] = False
        pool._remove_connection(conn)
        assert len(pool.connections) == 0
        assert conn not in pool.in_use

    def test_get_connection(self, pool):
        """Test getting a connection."""
        conn = pool.get_connection()
        assert isinstance(conn, duckdb.DuckDBPyConnection)
        assert conn in pool.connections
        assert pool.in_use[conn] is True

    def test_release_connection(self, pool):
        """Test releasing a connection."""
        conn = pool.get_connection()
        pool.release_connection(conn)
        assert pool.in_use[conn] is False

    def test_connection_timeout(self, pool):
        """Test connection timeout."""
        # Fill the pool
        conns = [pool.get_connection() for _ in range(pool.pool_size)]

        # Try to get another connection
        with pytest.raises(DatabaseConnectionError):
            pool.get_connection(timeout=0.1)

    def test_close_all(self, pool):
        """Test closing all connections."""
        conns = [pool.get_connection() for _ in range(pool.pool_size)]
        pool.close_all()
        assert len(pool.connections) == 0
        assert len(pool.in_use) == 0


class TestDatabaseManager:
    """Test suite for DatabaseManager."""

    @pytest.fixture
    def manager(self):
        """Create a test database manager."""
        manager = DatabaseManager()
        yield manager
        manager.close()

    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager.motherduck_pool is not None
        assert manager.local_pool is not None
        assert manager.write_conn is None
        assert manager.offline_mode is False

    def test_is_online(self, manager):
        """Test online status checking."""
        # Test online status
        assert manager.is_online() is True
        assert manager.offline_mode is False

        # Test offline status
        with patch.object(manager, "get_connection", side_effect=Exception):
            assert manager.is_online() is False
            assert manager.offline_mode is True

    def test_get_connection(self, manager):
        """Test connection acquisition."""
        with manager.get_connection() as conn:
            assert isinstance(conn, duckdb.DuckDBPyConnection)

    def test_write_connection(self, manager):
        """Test write connection management."""
        with manager.get_connection(for_write=True) as conn:
            assert isinstance(conn, duckdb.DuckDBPyConnection)
            assert manager.write_conn == conn

    def test_execute_query(self, manager):
        """Test query execution."""
        # Test successful query
        result = manager.execute_query("SELECT 1")
        assert result == [(1,)]

        # Test failed query
        with pytest.raises(DatabaseConnectionError):
            manager.execute_query("INVALID SQL")

    def test_close(self, manager):
        """Test manager cleanup."""
        # Get a write connection
        with manager.get_connection(for_write=True):
            pass

        # Close manager
        manager.close()
        assert manager.write_conn is None


class TestConnectionContextManager:
    """Test suite for connection context manager."""

    def test_get_connection_context(self):
        """Test connection context manager."""
        with get_connection() as conn:
            assert isinstance(conn, duckdb.DuckDBPyConnection)
            result = conn.execute("SELECT 1").fetchall()
            assert result == [(1,)]

    def test_get_connection_write(self):
        """Test write connection context manager."""
        with get_connection(for_write=True) as conn:
            assert isinstance(conn, duckdb.DuckDBPyConnection)
            # Test write operation
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.execute("INSERT INTO test VALUES (1)")
            result = conn.execute("SELECT * FROM test").fetchall()
            assert result == [(1,)]

    def test_get_connection_local_only(self):
        """Test local-only connection."""
        with get_connection(local_only=True) as conn:
            assert isinstance(conn, duckdb.DuckDBPyConnection)
            result = conn.execute("SELECT 1").fetchall()
            assert result == [(1,)]


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database components."""

    def test_full_connection_workflow(self):
        """Test complete connection workflow."""
        manager = DatabaseManager()

        try:
            # Test online mode
            assert manager.is_online() is True

            # Test write operations
            with manager.get_connection(for_write=True) as conn:
                conn.execute("CREATE TABLE test (id INTEGER, value TEXT)")
                conn.execute("INSERT INTO test VALUES (1, 'test')")

            # Test read operations
            with manager.get_connection() as conn:
                result = conn.execute("SELECT * FROM test").fetchall()
                assert result == [(1, "test")]

            # Test batch operations
            queries = [
                ("INSERT INTO test VALUES (?, ?)", [2, "test2"]),
                ("UPDATE test SET value = ? WHERE id = ?", ["updated", 1]),
            ]

            for query, params in queries:
                manager.execute_query(query, params, for_write=True)

            # Verify results
            result = manager.execute_query("SELECT * FROM test ORDER BY id")
            assert len(result) == 2
            assert result[0][1] == "updated"
            assert result[1][1] == "test2"

        finally:
            manager.close()
