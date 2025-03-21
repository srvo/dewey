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
from typing import Any, Dict, List, Optional, Union, TypeAlias

import duckdb
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Type aliases
DatabaseConnection: TypeAlias = duckdb.DuckDBPyConnection

# Constants
DEFAULT_POOL_SIZE = 5
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
MOTHERDUCK_TOKEN = os.getenv('MOTHERDUCK_TOKEN')
LOCAL_DB_PATH = os.path.expanduser('~/dewey/dewey.duckdb')
MOTHERDUCK_DB = 'md:dewey@motherduck/dewey.duckdb'

# Flag for testing - when True, disable dual-database writes
TEST_MODE = False

class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors."""
    pass

class ConnectionPool:
    """A simple connection pool for DuckDB connections."""
    
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
        
    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a connection from the pool.
        
        Returns:
            A DuckDB connection
            
        Raises:
            DatabaseConnectionError: If no connections are available
        """
        # Try to find an available connection
        for conn in self.connections:
            if not self.in_use[conn]:
                self.in_use[conn] = True
                return conn
                
        # If we have room for a new connection, create one
        if len(self.connections) < self.pool_size:
            try:
                if self.db_url.startswith('md:'):
                    conn = duckdb.connect(self.db_url, config={'motherduck_token': MOTHERDUCK_TOKEN})
                else:
                    conn = duckdb.connect(self.db_url)
                self.connections.append(conn)
                self.in_use[conn] = True
                return conn
            except Exception as e:
                raise DatabaseConnectionError(f"Failed to create new connection: {e}")
                
        raise DatabaseConnectionError("No connections available in the pool")
        
    def release_connection(self, conn: duckdb.DuckDBPyConnection):
        """Release a connection back to the pool.
        
        Args:
            conn: The connection to release
        """
        if conn in self.in_use:
            self.in_use[conn] = False
            
    def close_all(self):
        """Close all connections in the pool."""
        for conn in self.connections:
            try:
                conn.close()
            except:
                pass
        self.connections.clear()
        self.in_use.clear()

class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        """Initialize the database manager."""
        self.motherduck_pool = ConnectionPool(MOTHERDUCK_DB)
        self.local_pool = ConnectionPool(LOCAL_DB_PATH)
        self.write_conn = None  # Single connection for writes to local DB
        self.md_write_conn = None  # Single connection for writes to MotherDuck
        
    def _get_write_connection(self, motherduck: bool = False) -> duckdb.DuckDBPyConnection:
        """Get the single write connection, creating it if necessary.
        
        Args:
            motherduck: Whether to get the MotherDuck write connection
            
        Returns:
            The write connection
        """
        if motherduck:
            if not self.md_write_conn:
                try:
                    self.md_write_conn = duckdb.connect(MOTHERDUCK_DB, config={'motherduck_token': MOTHERDUCK_TOKEN})
                except Exception as e:
                    raise DatabaseConnectionError(f"Failed to create MotherDuck write connection: {e}")
            return self.md_write_conn
        else:
            if not self.write_conn:
                try:
                    self.write_conn = duckdb.connect(LOCAL_DB_PATH)
                except Exception as e:
                    raise DatabaseConnectionError(f"Failed to create local write connection: {e}")
            return self.write_conn
        
    @contextmanager
    def get_connection(self, for_write: bool = False, local_only: bool = False) -> duckdb.DuckDBPyConnection:
        """Get a database connection.
        
        Args:
            for_write: Whether the connection is for write operations
            local_only: Whether to only try the local database
            
        Yields:
            A database connection
        """
        conn = None
        
        try:
            if for_write:
                if local_only:
                    # For local-only writes, use the local write connection
                    conn = self._get_write_connection(motherduck=False)
                    yield conn
                    return
                else:
                    # For regular writes, use MotherDuck by default
                    try:
                        conn = self._get_write_connection(motherduck=True)
                        yield conn
                        return
                    except Exception as e:
                        logger.warning(f"Failed to connect to MotherDuck for write: {e}")
                        # Fallback to local if MotherDuck fails
                        conn = self._get_write_connection(motherduck=False)
                        yield conn
                        return
                
            if not local_only:
                try:
                    # Try MotherDuck first for reads
                    conn = self.motherduck_pool.get_connection()
                    yield conn
                    return
                except Exception as e:
                    logger.warning(f"Failed to connect to MotherDuck: {e}")
                    # No retries in get_connection, moved to execute_query
            
            # Fallback to local or if local_only was specified
            conn = self.local_pool.get_connection()
            yield conn
            
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to get database connection: {e}")
            
        finally:
            if conn:
                if for_write:
                    if conn == self.write_conn or conn == self.md_write_conn:
                        # Don't release the write connections
                        pass
                    else:
                        # This shouldn't happen, but just in case
                        if conn in self.motherduck_pool.connections:
                            self.motherduck_pool.release_connection(conn)
                        elif conn in self.local_pool.connections:
                            self.local_pool.release_connection(conn)
                else:
                    if conn in self.motherduck_pool.connections:
                        self.motherduck_pool.release_connection(conn)
                    elif conn in self.local_pool.connections:
                        self.local_pool.release_connection(conn)
                        
    def close(self):
        """Close all database connections."""
        if self.write_conn:
            try:
                self.write_conn.close()
            except:
                pass
            self.write_conn = None
            
        if self.md_write_conn:
            try:
                self.md_write_conn.close()
            except:
                pass
            self.md_write_conn = None
            
        self.motherduck_pool.close_all()
        self.local_pool.close_all()
        
    def execute_query(self, query: str, params: Optional[List[Any]] = None, 
                     for_write: bool = False, local_only: bool = False) -> List[Any]:
        """Execute a query and return the results.
        
        Args:
            query: The SQL query to execute
            params: Query parameters
            for_write: Whether this is a write operation
            local_only: Whether to only try the local database
            
        Returns:
            Query results
        """
        # In test mode, disable dual-database writes
        if TEST_MODE:
            with self.get_connection(for_write=for_write, local_only=local_only) as conn:
                try:
                    if params:
                        result = conn.execute(query, params).fetchall()
                    else:
                        result = conn.execute(query).fetchall()
                    return result
                except Exception as e:
                    raise DatabaseConnectionError(f"Query execution failed: {e}")
        
        # Normal mode (non-test)
        if for_write and not local_only:
            # For write operations, we want to write to both databases by default
            # First try MotherDuck
            md_result = None
            try:
                with self.get_connection(for_write=True, local_only=False) as md_conn:
                    if params:
                        md_result = md_conn.execute(query, params).fetchall()
                    else:
                        md_result = md_conn.execute(query).fetchall()
            except Exception as e:
                logger.warning(f"Failed to execute write query on MotherDuck, falling back to local: {e}")
                
            # Then always write to local DB (even if MotherDuck succeeded)
            try:
                with self.get_connection(for_write=True, local_only=True) as local_conn:
                    if params:
                        local_result = local_conn.execute(query, params).fetchall()
                    else:
                        local_result = local_conn.execute(query).fetchall()
                    
                # Return the MotherDuck result if available, otherwise local result
                return md_result if md_result is not None else local_result
            except Exception as e:
                # If both failed, raise error
                if md_result is None:
                    raise DatabaseConnectionError(f"Query execution failed on both databases: {e}")
                # If MotherDuck succeeded but local failed, log warning and return MotherDuck result
                logger.warning(f"Failed to execute write query on local DB, but succeeded on MotherDuck: {e}")
                return md_result
        else:
            # For read operations or local_only, use the standard connection
            with self.get_connection(for_write=for_write, local_only=local_only) as conn:
                try:
                    if params:
                        result = conn.execute(query, params).fetchall()
                    else:
                        result = conn.execute(query).fetchall()
                    return result
                except Exception as e:
                    raise DatabaseConnectionError(f"Query execution failed: {e}")
                
    def sync_to_motherduck(self):
        """Synchronize the local database to MotherDuck."""
        try:
            # Get the last sync timestamp
            last_sync = self.execute_query("""
                SELECT MAX(sync_time) FROM sync_status 
                WHERE status = 'success'
            """, local_only=True)
            
            last_sync_time = last_sync[0][0] if last_sync and last_sync[0][0] else datetime.min
            
            # Get changes since last sync
            changes = self.execute_query("""
                SELECT table_name, operation, record_id, changed_at
                FROM change_log
                WHERE changed_at > ?
                ORDER BY changed_at
            """, [last_sync_time], local_only=True)
            
            if not changes:
                logger.info("No changes to sync")
                return
                
            # Apply changes to MotherDuck
            with self.get_connection(for_write=True, local_only=False) as md_conn:
                for table, operation, record_id, changed_at in changes:
                    try:
                        if operation == 'INSERT' or operation == 'UPDATE':
                            # Get the record from local
                            record = self.execute_query(
                                f"SELECT * FROM {table} WHERE id = ?",
                                [record_id],
                                local_only=True
                            )
                            if record:
                                # Apply to MotherDuck
                                columns = ', '.join(record[0].keys())
                                placeholders = ', '.join(['?' for _ in record[0]])
                                md_conn.execute(f"""
                                    INSERT OR REPLACE INTO {table} ({columns})
                                    VALUES ({placeholders})
                                """, list(record[0].values()))
                                
                        elif operation == 'DELETE':
                            md_conn.execute(f"""
                                DELETE FROM {table} WHERE id = ?
                            """, [record_id])
                            
                    except Exception as e:
                        logger.error(f"Failed to sync change to {table}: {e}")
                        # Log the conflict
                        self.execute_query("""
                            INSERT INTO sync_conflicts (
                                table_name, record_id, operation, 
                                error_message, sync_time
                            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, [table, record_id, operation, str(e)], for_write=True)
                        
            # Update sync status
            self.execute_query("""
                INSERT INTO sync_status (sync_time, status, message)
                VALUES (CURRENT_TIMESTAMP, 'success', 'Sync completed successfully')
            """, for_write=True)
            
            logger.info(f"Successfully synced {len(changes)} changes to MotherDuck")
            
        except Exception as e:
            error_msg = f"Sync to MotherDuck failed: {e}"
            logger.error(error_msg)
            # Log the sync failure
            self.execute_query("""
                INSERT INTO sync_status (sync_time, status, message)
                VALUES (CURRENT_TIMESTAMP, 'failed', ?)
            """, [error_msg], for_write=True)
            raise DatabaseConnectionError(error_msg)

# Global instance
db_manager = DatabaseManager()

# Initialize the db_manager in utils to break circular dependencies
from .utils import set_db_manager
set_db_manager(db_manager)

# Direct connection functions for backward compatibility
@contextmanager
def get_connection(config: Optional[Dict] = None) -> duckdb.DuckDBPyConnection:
    """Get a direct connection to the local DuckDB database.
    
    This is provided for backward compatibility. Prefer using db_manager.
    
    Args:
        config: Optional configuration for the connection
        
    Yields:
        DuckDB connection
    """
    try:
        conn = duckdb.connect(LOCAL_DB_PATH, config=config)
        yield conn
    finally:
        if conn:
            conn.close()

@contextmanager
def get_motherduck_connection(config: Optional[Dict] = None) -> duckdb.DuckDBPyConnection:
    """Get a direct connection to the MotherDuck cloud database.
    
    This is provided for backward compatibility. Prefer using db_manager.
    
    Args:
        config: Optional configuration for the connection
        
    Yields:
        DuckDB connection
    """
    try:
        md_config = {'motherduck_token': MOTHERDUCK_TOKEN}
        if config:
            md_config.update(config)
        conn = duckdb.connect(MOTHERDUCK_DB, config=md_config)
        yield conn
    finally:
        if conn:
            conn.close()

@contextmanager
def get_duckdb_connection(db_path: Optional[str] = None, config: Optional[Dict] = None) -> duckdb.DuckDBPyConnection:
    """Get a direct connection to a DuckDB database.
    
    This is provided for backward compatibility. Prefer using db_manager.
    
    Args:
        db_path: Path to the DuckDB database file
        config: Optional configuration for the connection
        
    Yields:
        DuckDB connection
    """
    try:
        path = db_path or LOCAL_DB_PATH
        conn = duckdb.connect(path, config=config)
        yield conn
    finally:
        if conn:
            conn.close()

# Alias for backward compatibility with UI modules
DatabaseConnection = DatabaseManager

# For testing purposes - enables test mode
def set_test_mode(enabled: bool = True) -> None:
    """Set test mode to skip dual-database writes during tests.
    
    Args:
        enabled: Whether to enable test mode
    """
    global TEST_MODE
    TEST_MODE = enabled
