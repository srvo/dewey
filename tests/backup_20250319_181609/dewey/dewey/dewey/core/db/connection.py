"""Database connection utilities for Dewey.

This module provides functions to establish and manage database connections
for DuckDB and MotherDuck instances used in the Dewey project.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

import duckdb

from dewey.core.base_script import BaseScript

# Default connection parameters
DEFAULT_DB_PATH = Path.home() / "dewey" / "dewey.duckdb"
DEFAULT_MOTHERDUCK_PREFIX = "md:"


class DatabaseConnection(BaseScript):
    """Database connection wrapper for DuckDB/MotherDuck.

    This class provides a unified interface for both local DuckDB and
    cloud MotherDuck database connections.

    Attributes:
        conn: DuckDB connection object
        is_motherduck: Whether this connection is to MotherDuck
        connection_string: Connection string used to establish the connection
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
        super().__init__(config_section='db')
        self.connection_string = connection_string
        self.is_motherduck = connection_string and connection_string.startswith(DEFAULT_MOTHERDUCK_PREFIX)
        self.conn = None
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

    def execute(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a SQL query.

        Args:
            query: SQL query to execute.
            parameters: Optional parameters for the query.

        Returns:
            Query result.

        Raises:
            RuntimeError: If the query execution fails.
        """
        try:
            if parameters:
                return self.conn.execute(query, parameters).fetchdf()
            return self.conn.execute(query).fetchdf()
        except Exception as e:
            self.logger.error(f"Failed to execute query: {e}")
            raise RuntimeError(f"Failed to execute query: {e}")

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            try:
                self.conn.close()
                self.logger.debug("Database connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing database connection: {e}")
            finally:
                self.conn = None

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
            connection_string = str(DEFAULT_DB_PATH)

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
        'connection_string': str(db_path or DEFAULT_DB_PATH),
    }

    return get_connection(config)