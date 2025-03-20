"""Database connection utilities for Dewey.

This module provides functions to establish and manage database connections
for DuckDB and MotherDuck instances used in the Dewey project.
"""

import os
import re
import time
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Set, Tuple

import duckdb
import pandas as pd

from dewey.core.base_script import BaseScript

DEFAULT_MOTHERDUCK_PREFIX = "md:"

# Regular expressions to detect write operations
INSERT_PATTERN = re.compile(r"^\s*INSERT\s+INTO", re.IGNORECASE)
UPDATE_PATTERN = re.compile(r"^\s*UPDATE\s+", re.IGNORECASE)
DELETE_PATTERN = re.compile(r"^\s*DELETE\s+FROM", re.IGNORECASE)
CREATE_PATTERN = re.compile(r"^\s*CREATE\s+TABLE", re.IGNORECASE)
DROP_PATTERN = re.compile(r"^\s*DROP\s+TABLE", re.IGNORECASE)
ALTER_PATTERN = re.compile(r"^\s*ALTER\s+TABLE", re.IGNORECASE)

# Set to track tables modified locally
_locally_modified_tables: Set[str] = set()

logger = logging.getLogger(__name__)

# Additional import for sync functionality
from datetime import datetime

class DatabaseConnection(BaseScript):
    """Database connection wrapper for DuckDB/MotherDuck.

    This class provides a unified interface for both local DuckDB and
    cloud MotherDuck database connections.

    Attributes:
        conn: DuckDB connection object
        is_motherduck: Whether this connection is to MotherDuck
        connection_string: Connection string used to establish the connection
        auto_sync: Whether to automatically sync modified tables
    """

    def __init__(self, connection_string: Optional[str] = None, **kwargs):
        """Initialize a database connection.

        Args:
            connection_string: Connection string for the database.
                For DuckDB, this is a path to the database file.
                For MotherDuck, this is a URL starting with "md:".
            **kwargs: Additional connection parameters to pass to DuckDB.

        Raises:
            RuntimeError: If the connection cannot be established.
        """
        super().__init__(config_section='database', requires_db=False)
        self.connection_string = connection_string
        self.is_motherduck = connection_string and self.connection_string.startswith(
            self.get_config_value('default_motherduck_prefix', 'md:')
        )
        self.conn = None
        self.auto_sync = kwargs.pop('auto_sync', True)
        self._connect(**kwargs)

    def _connect(self, **kwargs) -> None:
        """Establish a database connection.

        Args:
            **kwargs: Additional connection parameters to pass to DuckDB.

        Raises:
            RuntimeError: If the connection cannot be established.
        """
        try:
            self.conn = duckdb.connect(self.connection_string, **kwargs)
            if self.is_motherduck:
                self.logger.info(f"Connected to MotherDuck: {self.connection_string}")
            else:
                self.logger.info(f"Connected to DuckDB: {self.connection_string}")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise RuntimeError(f"Failed to connect to database: {e}")

    def execute(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Execute a SQL query.

        Args:
            query: SQL query to execute.
            parameters: Optional parameters for the query.

        Returns:
            Query result as a pandas DataFrame.

        Raises:
            RuntimeError: If the query execution fails.
        """
        try:
            # Track table modifications for sync
            if not self.is_motherduck:
                self._track_modified_table(query)
                
            # Execute the query and convert result to pandas DataFrame
            if parameters:
                result = self.conn.execute(query, parameters)
            else:
                result = self.conn.execute(query)
                
            # Convert result to pandas DataFrame
            try:
                # For DuckDB >= 0.8.0
                return result.to_df()
            except AttributeError:
                # For older DuckDB versions that might return DataFrame directly
                if isinstance(result, pd.DataFrame):
                    return result
                # Fallback
                return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Failed to execute query: {e}")
            raise RuntimeError(f"Failed to execute query: {e}")
    
    def _track_modified_table(self, query: str) -> None:
        """Track tables that are modified by write operations.
        
        This is used to automatically sync changes to MotherDuck.
        
        Args:
            query: SQL query to analyze
        """
        # Only proceed if not a MotherDuck connection
        if self.is_motherduck:
            return
            
        # Check if this is a write operation
        is_write = (
            INSERT_PATTERN.search(query) or
            UPDATE_PATTERN.search(query) or
            DELETE_PATTERN.search(query) or
            CREATE_PATTERN.search(query) or
            DROP_PATTERN.search(query) or
            ALTER_PATTERN.search(query)
        )
        
        if not is_write:
            return
            
        # Extract table name from different query types
        table_name = None
        
        if INSERT_PATTERN.search(query):
            # INSERT INTO [table_name]
            match = re.search(r"INSERT\s+INTO\s+([^\s\(]+)", query, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                
        elif UPDATE_PATTERN.search(query):
            # UPDATE [table_name]
            match = re.search(r"UPDATE\s+([^\s]+)", query, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                
        elif DELETE_PATTERN.search(query):
            # DELETE FROM [table_name]
            match = re.search(r"DELETE\s+FROM\s+([^\s]+)", query, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                
        elif CREATE_PATTERN.search(query):
            # CREATE TABLE [table_name]
            match = re.search(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s\(]+)", query, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                
        elif DROP_PATTERN.search(query):
            # DROP TABLE [table_name]
            match = re.search(r"DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?([^\s\(]+)", query, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                
        elif ALTER_PATTERN.search(query):
            # ALTER TABLE [table_name]
            match = re.search(r"ALTER\s+TABLE\s+([^\s\(]+)", query, re.IGNORECASE)
            if match:
                table_name = match.group(1)
        
        # Clean the table name
        if table_name:
            # Remove quotes, schema references, etc.
            clean_table = table_name.strip('"`[]\'')
            if '.' in clean_table:
                clean_table = clean_table.split('.')[-1]
                
            # Skip tracking for internal tables
            if (clean_table.startswith('sqlite_') or 
                clean_table.startswith('dewey_sync_') or
                clean_table.startswith('information_schema')):
                return
                
            # Add to the set of modified tables
            global _locally_modified_tables
            _locally_modified_tables.add(clean_table)
            
            self.logger.debug(f"Tracked modification to table: {clean_table}")
            
            # If auto-sync is enabled, trigger sync to MotherDuck
            if self.auto_sync:
                self._trigger_sync(clean_table)
    
    def _trigger_sync(self, table_name: str) -> None:
        """Trigger a sync for a modified table.
        
        This imports the sync module only when needed to avoid circular imports.
        
        Args:
            table_name: Name of the table to sync
        """
        try:
            # Import here to avoid circular imports
            from dewey.core.db.duckdb_sync import get_duckdb_sync
            
            # Mark table as modified
            sync_instance = get_duckdb_sync()
            sync_instance.mark_table_modified(table_name)
            
            self.logger.debug(f"Triggered sync for modified table: {table_name}")
        except Exception as e:
            self.logger.warning(f"Failed to trigger sync for table {table_name}: {e}")

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            try:
                if not self.is_motherduck and self.auto_sync and _locally_modified_tables:
                    # Trigger final sync before closing
                    self._sync_modified_tables()
                
                self.conn.close()
                self.logger.debug("Database connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing database connection: {e}")
            finally:
                self.conn = None
                
    def _sync_modified_tables(self) -> None:
        """Sync all modified tables to MotherDuck before closing."""
        try:
            # Import here to avoid circular imports
            from dewey.core.db.duckdb_sync import get_duckdb_sync
            
            sync_instance = get_duckdb_sync()
            
            if _locally_modified_tables:
                self.logger.info(f"Syncing {len(_locally_modified_tables)} modified tables before closing")
                sync_instance.sync_modified_to_motherduck()
        except Exception as e:
            self.logger.warning(f"Error syncing modified tables: {e}")

    def run(self) -> None:
        """Placeholder for abstract method."""
        pass


def get_connection(config: Dict[str, Any]) -> DatabaseConnection:
    """Get a database connection based on configuration.

    Args:
        config: Configuration dictionary with connection parameters.
            Expected keys:
            - connection_string: Connection string for the database
            - motherduck: Boolean indicating whether to use MotherDuck
            - token: MotherDuck token (if using MotherDuck)
            - database: Database name (if using MotherDuck)

    Returns:
        A DatabaseConnection instance.

    Raises:
        RuntimeError: If the connection cannot be established.
    """
    # Extract connection parameters
    connection_string = config.get('connection_string')
    use_motherduck = config.get('motherduck', False)
    motherduck_token = config.get('token') or os.environ.get('MOTHERDUCK_TOKEN')
    database = config.get('database', 'dewey')

    # Build connection string if not provided
    if not connection_string:
        if use_motherduck:
            if not motherduck_token:
                raise ValueError("MotherDuck token is required for MotherDuck connections")
            # Set token in environment
            os.environ['MOTHERDUCK_TOKEN'] = motherduck_token
            connection_string = f"{DEFAULT_MOTHERDUCK_PREFIX}{database}"
        else:
            # Use default local DuckDB path
            default_db_path = Path.home() / "dewey" / "dewey.duckdb"
            connection_string = str(default_db_path)

    # Get additional connection parameters
    kwargs = {}
    for k, v in config.items():
        if k not in ('connection_string', 'motherduck', 'token', 'database'):
            kwargs[k] = v

    return DatabaseConnection(connection_string, **kwargs)


def get_motherduck_connection(database: str, token: Optional[str] = None) -> DatabaseConnection:
    """Convenience function to get a MotherDuck connection.

    Args:
        database: MotherDuck database name.
        token: MotherDuck token. If not provided, will be read from
            MOTHERDUCK_TOKEN environment variable.

    Returns:
        A DatabaseConnection instance for MotherDuck.

    Raises:
        ValueError: If token is not provided and not in environment.
        RuntimeError: If the connection cannot be established.
    """
    token = token or os.environ.get('MOTHERDUCK_TOKEN')
    if not token:
        raise ValueError("MotherDuck token is required for MotherDuck connections")

    config = {
        'motherduck': True,
        'token': token,
        'database': database,
    }

    return get_connection(config)


def get_local_connection(db_path: Optional[Union[str, Path]] = None) -> DatabaseConnection:
    """Convenience function to get a local DuckDB connection.

    Args:
        db_path: Path to the DuckDB database file. If not provided,
            uses the default path.

    Returns:
        A DatabaseConnection instance for local DuckDB.

    Raises:
        RuntimeError: If the connection cannot be established.
    """
    config = {
        'motherduck': False,
        'connection_string': str(db_path or Path.home() / "dewey" / "dewey.duckdb"),
    }

    return get_connection(config)

def get_local_dewey_connection() -> DatabaseConnection:
    """Get a connection to the local dewey.duckdb in the repository root.
    
    This is a convenience function to make it easier to work with the
    repository's default database location.
    
    Returns:
        A DatabaseConnection instance for the local dewey.duckdb
    """
    # Try to find the repository root
    try:
        # Look for a repository root marker file like pyproject.toml
        repo_root = None
        current_dir = Path.cwd()
        
        # Look up to 5 levels for the repository root
        for _ in range(5):
            if (current_dir / "pyproject.toml").exists() or (current_dir / ".git").exists():
                repo_root = current_dir
                break
            if current_dir.parent == current_dir:  # Reached root directory
                break
            current_dir = current_dir.parent
        
        if repo_root:
            db_path = repo_root / "dewey.duckdb"
            return get_local_connection(db_path)
        else:
            # Fall back to default
            return get_local_connection()
    except Exception as e:
        # Fall back to default
        return get_local_connection()

def get_modified_tables() -> List[str]:
    """Get a list of tables that have been modified locally.
    
    Returns:
        List of modified table names
    """
    global _locally_modified_tables
    return list(_locally_modified_tables)
