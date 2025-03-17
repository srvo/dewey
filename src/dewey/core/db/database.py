"""Database utilities for the Dewey project.

This module provides centralized database connection and management functions.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import duckdb

logger = logging.getLogger(__name__)

# Default output directory for database files
DEFAULT_DATA_DIR = os.path.join(os.path.expanduser("~"), "input_data", "ActiveData")


def get_duckdb_connection(
    database_name: str = "dewey.duckdb",
    data_dir: Optional[str] = None,
    read_only: bool = False,
    config: Optional[Dict[str, Any]] = None
) -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection with retry logic.
    
    Args:
        database_name: Name of the database file
        data_dir: Directory to store the database file (defaults to ~/input_data/ActiveData)
        read_only: Whether to open the connection in read-only mode
        config: Additional DuckDB configuration options
        
    Returns:
        A DuckDB connection object
        
    Raises:
        RuntimeError: If the connection cannot be established after retries
    """
    # Use the provided data_dir or the default
    data_dir = data_dir or DEFAULT_DATA_DIR
    
    # Ensure the directory exists
    os.makedirs(data_dir, exist_ok=True)
    
    # Full path to the database file
    db_path = os.path.join(data_dir, database_name)
    
    # Default configuration
    default_config = {
        'access_mode': 'READ_ONLY' if read_only else 'READ_WRITE',
        'threads': 1,
        'memory_limit': '1GB'  # Make sure this has a unit
    }
    
    # Merge with provided config
    if config:
        default_config.update(config)
    
    # Try to connect with retries
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Convert config to proper format for DuckDB
            duckdb_config = {}
            for key, value in default_config.items():
                if key == 'memory_limit' and isinstance(value, str) and not any(unit in value for unit in ['KB', 'MB', 'GB', 'TB', 'KiB', 'MiB', 'GiB', 'TiB']):
                    # Ensure memory_limit has a unit
                    value = f"{value}B" if value[-1].isdigit() else value
                duckdb_config[key] = value
            
            conn = duckdb.connect(
                database=db_path,
                read_only=read_only,
                config=duckdb_config
            )
            
            # Use WAL mode for better concurrency if not read-only
            if not read_only:
                conn.execute("PRAGMA journal_mode=WAL")
                
            logger.debug(f"Connected to DuckDB database at {db_path}")
            return conn
            
        except Exception as e:
            last_error = e
            logger.warning(f"Connection attempt {attempt+1}/{max_retries} failed: {e}")
    
    # If we get here, all retries failed
    error_msg = f"Failed to connect to DuckDB database at {db_path} after {max_retries} attempts"
    logger.error(error_msg)
    raise RuntimeError(error_msg) from last_error


def ensure_table_exists(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    schema_sql: str
) -> None:
    """Ensure a table exists in the database.
    
    Args:
        conn: DuckDB connection
        table_name: Name of the table to check/create
        schema_sql: SQL statement to create the table if it doesn't exist
        
    Returns:
        None
    """
    try:
        # Check if table exists
        result = conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'").fetchone()
        
        # Create table if it doesn't exist
        if not result:
            conn.execute(schema_sql)
            logger.info(f"Created table {table_name}")
        else:
            logger.debug(f"Table {table_name} already exists")
            
    except Exception as e:
        logger.error(f"Error ensuring table {table_name} exists: {e}")
        raise 