"""Database backup module.

This module handles database backup and restore operations for both
local DuckDB and MotherDuck cloud databases.
"""

import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .config import BACKUP_DIR, BACKUP_RETENTION_DAYS, LOCAL_DB_PATH
from .connection import db_manager
from .schema import TABLES

logger = logging.getLogger(__name__)


class BackupError(Exception):
    """Exception raised for backup/restore errors."""

    pass


def get_backup_path(timestamp: datetime | None = None) -> str:
    """Get the path for a backup file.

    Args:
        timestamp: Timestamp for the backup, defaults to current time

    Returns:
        Path to the backup file

    """
    if not timestamp:
        timestamp = datetime.now()

    backup_name = f"dewey_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.duckdb"
    return os.path.join(BACKUP_DIR, backup_name)


def create_backup(include_data: bool = True) -> str:
    """Create a backup of the local database.

    Args:
        include_data: Whether to include table data in the backup

    Returns:
        Path to the created backup file

    """
    try:
        backup_path = get_backup_path()

        # Copy database file
        shutil.copy2(LOCAL_DB_PATH, backup_path)
        logger.info(f"Created backup at {backup_path}")

        if not include_data:
            # Connect to backup database and truncate tables
            backup_conn = db_manager.get_connection(backup_path)
            try:
                for table_name in TABLES:
                    backup_conn.execute(f"TRUNCATE TABLE {table_name}")
                logger.info("Removed data from schema-only backup")
            finally:
                db_manager.release_connection(backup_conn)

        return backup_path

    except Exception as e:
        error_msg = f"Failed to create backup: {e}"
        logger.error(error_msg)
        raise BackupError(error_msg)


def restore_backup(backup_path: str, restore_data: bool = True) -> None:
    """Restore database from a backup file.

    Args:
        backup_path: Path to the backup file
        restore_data: Whether to restore table data

    """
    try:
        if not os.path.exists(backup_path):
            raise BackupError(f"Backup file not found: {backup_path}")

        # Create backup of current database
        current_backup = create_backup()
        logger.info(f"Created backup of current database at {current_backup}")

        try:
            # Stop any active connections
            db_manager.close_all_connections()

            # Restore database file
            shutil.copy2(backup_path, LOCAL_DB_PATH)
            logger.info(f"Restored database from {backup_path}")

            if not restore_data:
                # Connect to restored database and truncate tables
                conn = db_manager.get_connection(LOCAL_DB_PATH)
                try:
                    for table_name in TABLES:
                        conn.execute(f"TRUNCATE TABLE {table_name}")
                    logger.info("Removed data from schema-only restore")
                finally:
                    db_manager.release_connection(conn)

        except Exception as e:
            # Attempt to rollback to previous state
            shutil.copy2(current_backup, LOCAL_DB_PATH)
            logger.warning(f"Restored previous state from {current_backup}")
            raise e

    except Exception as e:
        error_msg = f"Failed to restore backup: {e}"
        logger.error(error_msg)
        raise BackupError(error_msg)


def list_backups() -> list[dict[str, str]]:
    """List available database backups.

    Returns:
        List of dictionaries containing backup information

    """
    try:
        backups = []

        for filename in os.listdir(BACKUP_DIR):
            if filename.startswith("dewey_backup_") and filename.endswith(".duckdb"):
                path = os.path.join(BACKUP_DIR, filename)

                # Extract timestamp portion from filename
                # Format: dewey_backup_YYYYMMDD_HHMMSS.duckdb
                # Starting at position 13 (after "dewey_backup_") and ending before ".duckdb"
                timestamp_str = filename[13:-7]

                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                backups.append(
                    {
                        "filename": filename,
                        "path": path,
                        "timestamp": timestamp.isoformat(),
                        "size": os.path.getsize(path),
                    }
                )

        return sorted(backups, key=lambda x: x["timestamp"], reverse=True)

    except Exception as e:
        error_msg = f"Failed to list backups: {e}"
        logger.error(error_msg)
        raise BackupError(error_msg)


def cleanup_old_backups() -> int:
    """Remove backups older than retention period.

    Returns:
        Number of backups removed

    """
    try:
        retention_date = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
        removed = 0

        for backup in list_backups():
            timestamp = datetime.fromisoformat(backup["timestamp"])
            if timestamp < retention_date:
                os.remove(backup["path"])
                removed += 1
                logger.info(f"Removed old backup: {backup['filename']}")

        return removed

    except Exception as e:
        error_msg = f"Failed to cleanup old backups: {e}"
        logger.error(error_msg)
        raise BackupError(error_msg)


def verify_backup(backup_path: str) -> bool:
    """Verify the integrity of a backup file.

    Args:
        backup_path: Path to the backup file

    Returns:
        True if backup is valid, False otherwise

    """
    try:
        if not os.path.exists(backup_path):
            raise BackupError(f"Backup file not found: {backup_path}")

        # Try to connect to backup database
        conn = db_manager.get_connection(backup_path)
        try:
            # Check if all tables exist
            for table_name in TABLES:
                result = conn.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
                if result is None:
                    raise BackupError(f"Table {table_name} not found in backup")

            logger.info(f"Verified backup integrity: {backup_path}")
            return True

        finally:
            db_manager.release_connection(conn)

    except Exception as e:
        logger.error(f"Backup verification failed: {e}")
        return False


def get_backup_info(backup_path: str) -> dict:
    """Get information about a backup file.

    Args:
        backup_path: Path to the backup file

    Returns:
        Dictionary containing backup information

    """
    try:
        if not os.path.exists(backup_path):
            raise BackupError(f"Backup file not found: {backup_path}")

        # Get basic file info
        filename = os.path.basename(backup_path)
        timestamp = datetime.strptime(
            filename[12:-7],  # Extract timestamp from filename
            "%Y%m%d_%H%M%S",
        )

        info = {
            "filename": filename,
            "path": backup_path,
            "timestamp": timestamp.isoformat(),
            "size": os.path.getsize(backup_path),
            "tables": {},
        }

        # Connect to backup database
        conn = db_manager.get_connection(backup_path)
        try:
            # Get table information
            for table_name in TABLES:
                result = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = result.fetchone()[0] if result else 0

                info["tables"][table_name] = {"row_count": row_count}

        finally:
            db_manager.release_connection(conn)

        return info

    except Exception as e:
        error_msg = f"Failed to get backup info: {e}"
        logger.error(error_msg)
        raise BackupError(error_msg)


def export_table(table_name: str, output_path: str, format: str = "csv") -> None:
    """Export a table to a file.

    Args:
        table_name: Name of the table to export
        output_path: Path to save the exported file
        format: Export format ('csv' or 'parquet')

    """
    try:
        # Create output directory if needed
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Export table
        if format.lower() == "csv":
            db_manager.execute_query(f"""
                COPY {table_name} TO '{output_path}'
                WITH (FORMAT CSV, HEADER TRUE)
            """)
        elif format.lower() == "parquet":
            db_manager.execute_query(f"""
                COPY {table_name} TO '{output_path}'
                (FORMAT PARQUET)
            """)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        logger.info(f"Exported {table_name} to {output_path}")

    except Exception as e:
        error_msg = f"Failed to export {table_name}: {e}"
        logger.error(error_msg)
        raise BackupError(error_msg)


def import_table(table_name: str, input_path: str, format: str = "csv") -> int:
    """Import data into a table from a file.

    Args:
        table_name: Name of the table to import into
        input_path: Path to the input file
        format: Import format ('csv' or 'parquet')

    Returns:
        Number of rows imported

    """
    try:
        if not os.path.exists(input_path):
            raise BackupError(f"Input file not found: {input_path}")

        # Import data
        if format.lower() == "csv":
            db_manager.execute_query(
                f"""
                COPY {table_name} FROM '{input_path}'
                WITH (FORMAT CSV, HEADER TRUE)
            """,
                for_write=True,
            )
        elif format.lower() == "parquet":
            db_manager.execute_query(
                f"""
                COPY {table_name} FROM '{input_path}'
                (FORMAT PARQUET)
            """,
                for_write=True,
            )
        else:
            raise ValueError(f"Unsupported import format: {format}")

        # Get number of rows imported
        result = db_manager.execute_query(f"""
            SELECT COUNT(*) FROM {table_name}
        """)
        row_count = result[0][0] if result else 0

        logger.info(f"Imported {row_count} rows into {table_name}")
        return row_count

    except Exception as e:
        error_msg = f"Failed to import {table_name}: {e}"
        logger.error(error_msg)
        raise BackupError(error_msg)
