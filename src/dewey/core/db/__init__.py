"""Database module initialization.

This module initializes the database system and provides a high-level interface
for database operations.
"""

import logging
import os
import threading
from typing import Dict, Optional

from .backup import (
    cleanup_old_backups,
    create_backup,
    export_table,
    get_backup_info,
    import_table,
    list_backups,
    restore_backup,
    verify_backup,
)
from .config import initialize_environment
from .connection import DatabaseConnection, DatabaseConnectionError, db_manager
from .monitor import monitor_database
from .operations import (
    bulk_insert,
    delete_record,
    execute_custom_query,
    get_record,
    insert_record,
    query_records,
    update_record,
)
from .schema import (
    initialize_schema,
    get_current_version,
    apply_migration,
    verify_schema_consistency,
)
from .sync import sync_all_tables

logger = logging.getLogger(__name__)


def get_connection(
    for_write: bool = False, local_only: bool = False
) -> DatabaseConnection:
    """Get a database connection.

    Args:
        for_write: Whether the connection is for write operations
        local_only: Whether to only try the local database

    Returns:
        A database connection

    """
    return db_manager


def get_motherduck_connection(for_write: bool = False) -> DatabaseConnection | None:
    """Get a connection to the MotherDuck cloud database.

    Args:
        for_write: Whether the connection is for write operations

    Returns:
        A database connection or None if connection fails

    """
    try:
        return db_manager.get_connection(for_write=for_write, local_only=False)
    except DatabaseConnectionError:
        logger.warning("Failed to get MotherDuck connection")
        return None


def get_duckdb_connection(for_write: bool = False) -> DatabaseConnection:
    """Get a connection to the local DuckDB database.

    Args:
        for_write: Whether the connection is for write operations

    Returns:
        A database connection

    """
    return db_manager.get_connection(for_write=for_write, local_only=True)


def initialize_database(motherduck_token: str | None = None) -> bool:
    """Initialize the database system.

    Args:
        motherduck_token: MotherDuck API token

    Returns:
        True if initialization successful, False otherwise

    """
    try:
        # Set up environment
        if motherduck_token:
            os.environ["MOTHERDUCK_TOKEN"] = motherduck_token

        if not initialize_environment(motherduck_token):
            logger.error("Failed to initialize environment")
            return False

        # Initialize schema
        try:
            initialize_schema()
            logger.info("Schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            return False

        # Start monitoring in background
        try:
            monitor_thread = threading.Thread(target=monitor_database, daemon=True)
            monitor_thread.start()
            logger.info("Database monitoring started")
        except Exception as e:
            logger.warning(f"Failed to start monitoring: {e}")

        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def get_database_info() -> dict:
    """Get information about the database system.

    Returns:
        Dictionary containing database information

    """
    try:
        # Get health check results
        from .monitor import run_health_check

        health = run_health_check(include_performance=True)

        # Get backup information
        backups = list_backups()
        latest_backup = backups[0] if backups else None

        # Get sync information
        from .sync import get_last_sync_time

        last_sync = get_last_sync_time()

        return {
            "health": health,
            "backups": {"count": len(backups), "latest": latest_backup},
            "sync": {"last_sync": last_sync.isoformat() if last_sync else None},
        }

    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {"error": str(e)}


def close_database() -> None:
    """Close all database connections."""
    try:
        db_manager.close()
        logger.info("Database connections closed")

        # Import monitor module at the top level to avoid circular imports
        import src.dewey.core.db.monitor as monitor

        monitor.stop_monitoring()

        logger.info("Database monitoring stopped")
    except Exception as e:
        logger.error(f"Failed to close database connections: {e}")


__all__ = [
    "initialize_database",
    "get_database_info",
    "close_database",
    "get_connection",
    "get_motherduck_connection",
    "get_duckdb_connection",
    "DatabaseConnection",
    "DatabaseConnectionError",
    "insert_record",
    "update_record",
    "delete_record",
    "get_record",
    "query_records",
    "bulk_insert",
    "execute_custom_query",
    "create_backup",
    "restore_backup",
    "list_backups",
    "cleanup_old_backups",
    "verify_backup",
    "get_backup_info",
    "export_table",
    "import_table",
    "initialize_schema",
    "get_current_version",
    "apply_migration",
    "verify_schema_consistency",
]
