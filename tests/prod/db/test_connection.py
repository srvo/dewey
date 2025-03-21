"""Tests for database connection module.

This module tests the ConnectionPool and DatabaseManager classes.
"""

import os
import unittest
from unittest.mock import patch, MagicMock, call

import duckdb
import pytest

from src.dewey.core.db.connection import (
    ConnectionPool,
    DatabaseManager,
    DatabaseConnectionError,
    set_test_mode
)

class TestConnectionPool(unittest.TestCase):
    """Test ConnectionPool class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock duckdb.connect
        self.connect_patcher = patch('src.dewey.core.db.connection.duckdb.connect')
        self.mock_connect = self.connect_patcher.start()
        
        # Create mock connection
        self.mock_conn = MagicMock()
        self.mock_connect.return_value = self.mock_conn
        
        # Create ConnectionPool instance
        self.pool = ConnectionPool('test_db', pool_size=3)
        
    def tearDown(self):
        """Tear down test fixtures."""
        self.connect_patcher.stop()
    
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.pool.db_url, 'test_db')
        self.assertEqual(self.pool.pool_size, 3)
        self.assertEqual(self.pool.connections, [])
        self.assertEqual(self.pool.in_use, {})
    
    def test_get_connection(self):
        """Test getting a connection."""
        # Get a connection
        conn = self.pool.get_connection()
        
        # Check that connection was created
        self.mock_connect.assert_called_once_with('test_db')
        
        # Check that connection was added to pool
        self.assertEqual(self.pool.connections, [self.mock_conn])
        
        # Check that connection is marked as in use
        self.assertEqual(self.pool.in_use, {self.mock_conn: True})
        
        # Check that connection was returned
        self.assertEqual(conn, self.mock_conn)
    
    def test_release_connection(self):
        """Test releasing a connection."""
        # Get a connection
        conn = self.pool.get_connection()
        
        # Release the connection
        self.pool.release_connection(conn)
        
        # Check that connection is marked as not in use
        self.assertEqual(self.pool.in_use, {self.mock_conn: False})
        
        # Get another connection - should reuse the existing one
        conn2 = self.pool.get_connection()
        self.assertEqual(conn2, self.mock_conn)
        self.assertEqual(self.mock_connect.call_count, 1)
    
    def test_close_all(self):
        """Test closing all connections."""
        # Get some connections
        conn1 = self.pool.get_connection()
        self.pool.release_connection(conn1)
        
        conn2 = self.pool.get_connection()
        
        # Close all connections
        self.pool.close_all()
        
        # Check that connections were closed
        self.mock_conn.close.assert_called()
        
        # Check that pool was cleared
        self.assertEqual(self.pool.connections, [])
        self.assertEqual(self.pool.in_use, {})
    
    def test_pool_exhaustion(self):
        """Test pool exhaustion."""
        # Get max number of connections
        for _ in range(3):
            self.pool.get_connection()
            
        # Try to get one more connection - should raise error
        with self.assertRaises(DatabaseConnectionError):
            self.pool.get_connection()
    
    def test_reuse_connection(self):
        """Test connection reuse."""
        # Create multiple connections
        conn1 = self.pool.get_connection()
        conn2 = self.pool.get_connection()
        conn3 = self.pool.get_connection()
        
        # Release a connection
        self.pool.release_connection(conn2)
        
        # Get a new connection - should reuse conn2
        conn4 = self.pool.get_connection()
        
        # Check that conn4 is actually conn2
        self.assertEqual(conn4, conn2)
        self.assertEqual(self.mock_connect.call_count, 3)
        
        # Check that connections are marked correctly
        self.assertEqual(self.pool.in_use, {
            conn1: True,
            conn2: True,
            conn3: True
        })

class TestDatabaseManager(unittest.TestCase):
    """Test DatabaseManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Enable test mode to disable dual-database writes
        set_test_mode(True)
        
        # Create mocks
        self.mock_md_pool = MagicMock()
        self.mock_local_pool = MagicMock()
        self.mock_conn = MagicMock()
        
        # Create DatabaseManager instance and replace its pools with mocks
        self.manager = DatabaseManager()
        self.manager.motherduck_pool = self.mock_md_pool
        self.manager.local_pool = self.mock_local_pool
        
    def tearDown(self):
        """Tear down test fixtures."""
        # Disable test mode
        set_test_mode(False)
    
    def test_init(self):
        """Test initialization."""
        # Create a fresh manager to test init
        with patch('src.dewey.core.db.connection.ConnectionPool') as mock_pool_class:
            # Create mock pools
            mock_md_pool = MagicMock()
            mock_local_pool = MagicMock()
            mock_pool_class.side_effect = [mock_md_pool, mock_local_pool]
            
            # Create a new manager
            manager = DatabaseManager()
            
            # Check that pools were created with correct arguments
            mock_pool_class.assert_has_calls([
                call('md:dewey@motherduck/dewey.duckdb'),
                call(unittest.mock.ANY)  # Don't specify exact path, as it depends on the environment
            ])
            
            # Check that pools were assigned
            self.assertEqual(manager.motherduck_pool, mock_md_pool)
            self.assertEqual(manager.local_pool, mock_local_pool)
            
            # Check that write connections are None
            self.assertIsNone(manager.write_conn)
            self.assertIsNone(manager.md_write_conn)
    
    def test_get_write_connection(self):
        """Test getting write connection."""
        # Create mock duckdb.connect
        with patch('src.dewey.core.db.connection.duckdb.connect') as mock_connect:
            mock_connect.return_value = self.mock_conn
            
            # Get local write connection
            conn = self.manager._get_write_connection()
            
            # Check that connection was created and returned
            self.assertEqual(conn, self.mock_conn)
            self.assertEqual(self.manager.write_conn, self.mock_conn)
            
            # Get MotherDuck write connection
            md_conn = self.manager._get_write_connection(motherduck=True)
            
            # Check that connection was created and returned
            self.assertEqual(md_conn, self.mock_conn)
            self.assertEqual(self.manager.md_write_conn, self.mock_conn)
    
    def test_close(self):
        """Test closing manager."""
        # Set up mock connections
        self.manager.write_conn = self.mock_conn
        self.manager.md_write_conn = self.mock_conn
        
        # Close manager
        self.manager.close()
        
        # Check that connections were closed
        self.assertEqual(self.mock_conn.close.call_count, 2)
        
        # Check that pools were closed
        self.mock_md_pool.close_all.assert_called_once()
        self.mock_local_pool.close_all.assert_called_once()
        
    @patch('src.dewey.core.db.connection.time.sleep')
    def test_get_connection_motherduck_failure(self, mock_sleep):
        """Test fallback to local when MotherDuck connection fails."""
        # Make MotherDuck pool raise an exception
        self.mock_md_pool.get_connection.side_effect = Exception("Connection failed")
        
        # Set up local pool to return a connection
        local_conn = MagicMock()
        self.mock_local_pool.get_connection.return_value = local_conn
        
        # Get a connection
        with self.manager.get_connection() as conn:
            # Check that connection is from local pool
            self.assertEqual(conn, local_conn)
            
        # Check that MotherDuck pool was tried first
        self.mock_md_pool.get_connection.assert_called_once()
        
        # Check that local pool was used as fallback
        self.mock_local_pool.get_connection.assert_called_once()
        
    def test_execute_query(self):
        """Test executing a query."""
        # Set up mock connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, 2, 3)]
        self.mock_conn.execute.return_value = mock_cursor
        
        # Make get_connection return our mock connection
        with patch.object(self.manager, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = self.mock_conn
            
            # Execute a query
            result = self.manager.execute_query("SELECT 1", [42], for_write=True)
            
            # Check that execute was called with correct arguments
            self.mock_conn.execute.assert_called_once_with("SELECT 1", [42])
            
            # Check that result was returned
            self.assertEqual(result, [(1, 2, 3)])

if __name__ == '__main__':
    unittest.main() 