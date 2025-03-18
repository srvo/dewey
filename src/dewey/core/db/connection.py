"""Database connection management module.

This module provides a centralized way to manage database connections to both
MotherDuck cloud and local DuckDB instances, with automatic fallback and
connection pooling.
"""

import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import duckdb
from dotenv import load_dotenv

from .errors import ConnectionError, handle_error

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
DEFAULT_POOL_SIZE = 5
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
CONNECTION_TIMEOUT = 5.0  # seconds
HEALTH_CHECK_INTERVAL = 30.0  # seconds
MOTHERDUCK_TOKEN = os.getenv('MOTHERDUCK_TOKEN')
LOCAL_DB_PATH = os.path.expanduser('~/dewey/dewey.duckdb')
MOTHERDUCK_DB = 'md:dewey@motherduck/dewey.duckdb'

class ConnectionPool:
    """A connection pool for DuckDB connections with health monitoring."""
    
    def __init__(self, db_url: str, pool_size: int = DEFAULT_POOL_SIZE):
        """Initialize the connection pool.
        
        Args:
            db_url: Database URL (local path or MotherDuck URL)
            pool_size: Maximum number of connections in the pool
        """
        self.db_url = db_url
        self.pool_size = pool_size
        self.connections: List[duckdb.DuckDBPyConnection] = []
        self.in_use: Dict[duckdb.DuckDBPyConnection, bool] = {}
        self.last_health_check: Dict[duckdb.DuckDBPyConnection, float] = {}
        
    def _create_connection(self) -> duckdb.DuckDBPyConnection:
        """Create a new database connection.
        
        Returns:
            A new DuckDB connection
            
        Raises:
            ConnectionError: If connection creation fails
        """
        try:
            if self.db_url.startswith('md:'):
                conn = duckdb.connect(self.db_url, config={'motherduck_token': MOTHERDUCK_TOKEN})
            else:
                conn = duckdb.connect(self.db_url)
            return conn
        except Exception as e:
            raise ConnectionError(f"Failed to create connection: {e}")
            
    def _test_connection(self, conn: duckdb.DuckDBPyConnection) -> bool:
        """Test if a connection is healthy.
        
        Args:
            conn: Connection to test
            
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # Only test if enough time has passed since last check
            now = time.time()
            if now - self.last_health_check.get(conn, 0) < HEALTH_CHECK_INTERVAL:
                return True
                
            conn.execute("SELECT 1")
            self.last_health_check[conn] = now
            return True
        except:
            return False
            
    def _remove_connection(self, conn: duckdb.DuckDBPyConnection):
        """Remove a connection from the pool.
        
        Args:
            conn: Connection to remove
        """
        try:
            conn.close()
        except:
            pass
        if conn in self.connections:
            self.connections.remove(conn)
        self.in_use.pop(conn, None)
        self.last_health_check.pop(conn, None)
        
    def get_connection(self, timeout: float = CONNECTION_TIMEOUT) -> duckdb.DuckDBPyConnection:
        """Get a connection from the pool with timeout.
        
        Args:
            timeout: Maximum time to wait for a connection
            
        Returns:
            A DuckDB connection
            
        Raises:
            ConnectionError: If no connection is available within timeout
        """
        start_time = time.time()
        last_error = None
        
        while time.time() - start_time < timeout:
            # Try to find an available connection
            for conn in list(self.connections):  # Use list to avoid modification during iteration
                if not self.in_use[conn]:
                    if self._test_connection(conn):
                        self.in_use[conn] = True
                        return conn
                    else:
                        self._remove_connection(conn)
                        
            # If we have room for a new connection, create one
            if len(self.connections) < self.pool_size:
                try:
                    conn = self._create_connection()
                    self.connections.append(conn)
                    self.in_use[conn] = True
                    self.last_health_check[conn] = time.time()
                    return conn
                except Exception as e:
                    last_error = e
                    logger.warning(f"Failed to create connection: {e}")
                    
            time.sleep(0.1)
            
        error_msg = f"Connection timeout after {timeout} seconds"
        if last_error:
            error_msg += f": {last_error}"
        raise ConnectionError(error_msg)
        
    def release_connection(self, conn: duckdb.DuckDBPyConnection):
        """Release a connection back to the pool.
        
        Args:
            conn: The connection to release
        """
        if conn in self.in_use:
            # Test connection health before releasing
            if self._test_connection(conn):
                self.in_use[conn] = False
            else:
                self._remove_connection(conn)
                
    def close_all(self):
        """Close all connections in the pool."""
        for conn in list(self.connections):
            self._remove_connection(conn)
            
class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        """Initialize the database manager."""
        self.motherduck_pool = ConnectionPool(MOTHERDUCK_DB)
        self.local_pool = ConnectionPool(LOCAL_DB_PATH)
        self.write_conn = None
        self.offline_mode = False
        self.last_online_check = 0
        
    def is_online(self) -> bool:
        """Check if MotherDuck is accessible.
        
        Returns:
            True if MotherDuck is accessible, False otherwise
        """
        # Check connection status at most once every 30 seconds
        if time.time() - self.last_online_check < HEALTH_CHECK_INTERVAL:
            return not self.offline_mode
            
        try:
            with self.get_connection(local_only=False) as conn:
                conn.execute("SELECT 1")
                self.offline_mode = False
                return True
        except:
            self.offline_mode = True
            return False
        finally:
            self.last_online_check = time.time()
            
    @contextmanager
    def get_connection(self, for_write: bool = False, local_only: bool = False) -> duckdb.DuckDBPyConnection:
        """Get a database connection with automatic fallback.
        
        Args:
            for_write: Whether the connection is for write operations
            local_only: Whether to only try the local database
            
        Yields:
            A database connection
        """
        conn = None
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                if for_write:
                    # For writes, always use the single write connection
                    if not self.write_conn or not self._test_write_connection():
                        self.write_conn = self.local_pool.get_connection()
                    conn = self.write_conn
                    yield conn
                    return
                    
                if not local_only and not self.offline_mode:
                    try:
                        # Try MotherDuck first
                        conn = self.motherduck_pool.get_connection()
                        yield conn
                        return
                    except Exception as e:
                        logger.warning(f"Failed to connect to MotherDuck: {e}")
                        if retry_count < MAX_RETRIES - 1:
                            retry_count += 1
                            time.sleep(RETRY_DELAY * (2 ** retry_count))  # Exponential backoff
                            continue
                        self.offline_mode = True
                
                # Fallback to local or if local_only was specified
                conn = self.local_pool.get_connection()
                yield conn
                return
                
            except Exception as e:
                error_id = handle_error(e, {
                    'for_write': for_write,
                    'local_only': local_only,
                    'retry_count': retry_count
                })
                raise ConnectionError(f"Failed to get database connection (Error ID: {error_id})")
                
            finally:
                if conn:
                    if for_write and conn == self.write_conn:
                        # Don't release the write connection
                        pass
                    elif conn in self.motherduck_pool.connections:
                        self.motherduck_pool.release_connection(conn)
                    elif conn in self.local_pool.connections:
                        self.local_pool.release_connection(conn)
                        
    def _test_write_connection(self) -> bool:
        """Test if the write connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.write_conn:
            return False
            
        try:
            self.write_conn.execute("SELECT 1")
            return True
        except:
            return False
            
    def close(self):
        """Close all database connections."""
        if self.write_conn:
            try:
                self.write_conn.close()
            except:
                pass
            self.write_conn = None
            
        self.motherduck_pool.close_all()
        self.local_pool.close_all()
        
    def execute_query(self, query: str, params: Optional[List[Any]] = None,
                     for_write: bool = False, local_only: bool = False) -> List[Any]:
        """Execute a query with retry logic.
        
        Args:
            query: The SQL query to execute
            params: Query parameters
            for_write: Whether this is a write operation
            local_only: Whether to only try the local database
            
        Returns:
            Query results
        """
        with self.get_connection(for_write=for_write, local_only=local_only) as conn:
            try:
                if params:
                    result = conn.execute(query, params).fetchall()
                else:
                    result = conn.execute(query).fetchall()
                return result
            except Exception as e:
                error_id = handle_error(e, {
                    'query': query,
                    'for_write': for_write,
                    'local_only': local_only
                })
                raise ConnectionError(f"Query execution failed (Error ID: {error_id})")

# Global instance
db_manager = DatabaseManager() 