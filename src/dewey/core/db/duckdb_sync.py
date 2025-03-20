"""DuckDB Sync functionality.

This module provides functionality to sync data between a local DuckDB
instance and a MotherDuck (cloud) instance.
"""

import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import duckdb
import pandas as pd

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_local_connection, get_motherduck_connection, DatabaseConnection, get_connection
from dewey.core.db import utils


class DuckDBSync(BaseScript):
    """Handles synchronization between local DuckDB and MotherDuck (cloud).

    This class provides functionality to:
    1. Sync data from MotherDuck to local DuckDB
    2. Sync data from local DuckDB to MotherDuck
    3. Keep track of sync status and timestamps
    4. Set up automatic sync on a schedule

    Attributes:
        local_conn: Connection to local DuckDB.
        motherduck_conn: Connection to MotherDuck.
        local_db_path: Path to local DuckDB file.
        motherduck_db: MotherDuck database name.
        sync_interval: Time between automatic syncs (in seconds).
        max_sync_age: Maximum time to allow before forcing a sync (in seconds).
        _sync_thread: Background thread for automatic syncing.
        _stop_sync_thread: Flag to signal the sync thread to stop.
        _last_sync_time: Timestamp of the last successful sync.
        _tables_modified_locally: Set of tables modified locally since last sync.
    """

    def __init__(
        self,
        name: Optional[str] = "DuckDBSync",
        description: Optional[str] = "Synchronizes data between local DuckDB and MotherDuck.",
        config_section: Optional[str] = "test_config",
        requires_db: bool = True,
        enable_llm: bool = False,
        local_db_path: Optional[str] = None,
        motherduck_db: Optional[str] = None,
        motherduck_token: Optional[str] = None,
        sync_interval: Optional[int] = None,
        max_sync_age: Optional[int] = None,
        auto_sync: bool = True,
    ) -> None:
        """Initialize the DuckDBSync with local and cloud connections.

        Args:
            name: Name of the script (used for logging).
            description: Description of the script.
            config_section: Section in dewey.yaml to load for this script.
            requires_db: Whether this script requires database access.
            enable_llm: Whether this script requires LLM access.
            local_db_path: Path to the local DuckDB file. If None, uses the default path.
            motherduck_db: MotherDuck database name to sync with.
            motherduck_token: MotherDuck token. If None, uses the MOTHERDUCK_TOKEN env var.
            sync_interval: Time between automatic syncs in seconds (default: 6 hours).
            max_sync_age: Maximum time to allow before forcing a sync (default: 7 days).
            auto_sync: Whether to start automatic sync thread (default: True).
        """
        super().__init__(
            name=name,
            description=description,
            config_section=config_section,
            requires_db=requires_db,
            enable_llm=enable_llm,
        )

        # Initialize paths and connections
        self.local_db_path = local_db_path or self.get_config_value("local_db_path") or str(Path.home() / "dewey" / "dewey.duckdb")
        self.motherduck_db = motherduck_db or self.get_config_value("motherduck_db") or "dewey"
        self.sync_interval = sync_interval or self.get_config_value("sync_interval") or 6 * 60 * 60
        self.max_sync_age = max_sync_age or self.get_config_value("max_sync_age") or 7 * 24 * 60 * 60

        # Initialize state tracking
        self._last_sync_time = None
        self._tables_modified_locally = set()
        self._sync_lock = threading.RLock()
        self._stop_sync_thread = threading.Event()
        self._sync_thread = None

        # Set up connections
        self.logger.info(f"Initializing DuckDBSync with local DB: {self.local_db_path}")
        self.logger.info(f"MotherDuck database: {self.motherduck_db}")

        try:
            self.local_conn = get_local_connection(self.local_db_path)
            self.logger.info("Connected to local DuckDB")

            motherduck_token_effective = motherduck_token or os.environ.get("MOTHERDUCK_TOKEN")
            self.motherduck_conn = get_motherduck_connection(self.motherduck_db, motherduck_token_effective)
            self.logger.info(f"Connected to MotherDuck: {self.motherduck_db}")

            # Initialize sync metadata table in local DB
            self._init_sync_metadata()

            # Start automatic sync thread if requested
            self.auto_sync = auto_sync
            if self.auto_sync:
                self.start_auto_sync()
        except Exception as e:
            self.logger.error(f"Error initializing DuckDBSync: {e}")
            raise

    def _init_sync_metadata(self) -> None:
        """Initialize the sync metadata table in local DB."""
        try:
            # Create sync metadata table if it doesn't exist
            self.local_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dewey_sync_metadata (
                    table_name TEXT PRIMARY KEY,
                    last_sync_time TIMESTAMP,
                    last_direction TEXT,
                    sync_status TEXT,
                    error_message TEXT
                )
            """
            )

            # Create a table to track overall sync status
            self.local_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dewey_sync_status (
                    sync_id INTEGER PRIMARY KEY,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    status TEXT,
                    error_message TEXT,
                    tables_synced INTEGER,
                    records_synced INTEGER
                )
            """
            )

            # Load the last sync time
            result = self.local_conn.execute(
                """
                SELECT MAX(end_time) AS last_sync
                FROM dewey_sync_status
                WHERE status = 'completed'
            """
            )

            # The result is already a DataFrame in newer DuckDB versions
            if not result.empty and "last_sync" in result.columns and result["last_sync"][0]:
                self._last_sync_time = result["last_sync"][0]
                self.logger.info(f"Last successful sync: {self._last_sync_time}")
            else:
                self.logger.info("No previous sync records found.")
        except Exception as e:
            self.logger.error(f"Error initializing sync metadata: {e}")
            raise

    def list_tables(self, connection: DatabaseConnection) -> List[str]:
        """Get a list of all tables in the database.

        Args:
            connection: Database connection to use.

        Returns:
            List of table names.
        """
        try:
            # Get the underlying DuckDB connection
            duckdb_conn = connection.conn

            # Execute directly on the DuckDB connection
            result = duckdb_conn.execute("SHOW TABLES")
            rows = result.fetchall()

            # Extract table names from the result
            tables = [row[0] for row in rows if row]

            # Filter out internal tables
            filtered_tables = [
                t
                for t in tables
                if not t.startswith("sqlite_")
                and not t.startswith("pg_")
                and not t.startswith("information_schema")
            ]

            self.logger.info(f"Found {len(filtered_tables)} tables: {filtered_tables}")
            return filtered_tables
        except Exception as e:
            self.logger.error(f"Error listing tables: {e}")
            return []

    def table_exists(self, table_name: str, connection: DatabaseConnection) -> bool:
        """Check if a table exists in the database.

        Args:
            table_name: Name of the table to check.
            connection: Database connection to use.

        Returns:
            True if the table exists, False otherwise.
        """
        try:
            tables = self.list_tables(connection)
            return table_name in tables
        except Exception as e:
            self.logger.error(f"Error checking if table exists: {e}")
            return False

    def get_table_schema(self, table_name: str, connection: DatabaseConnection) -> str:
        """Get the schema for a table.

        Args:
            table_name: Name of the table.
            connection: Database connection to use.

        Returns:
            CREATE TABLE statement for the table.
        """
        try:
            # Get the underlying DuckDB connection
            duckdb_conn = connection.conn

            # Execute directly on the DuckDB connection
            result = duckdb_conn.execute(f"SHOW CREATE TABLE {table_name}")
            schema_row = result.fetchone()

            if schema_row and len(schema_row) > 0:
                return schema_row[0]
            return ""
        except Exception as e:
            self.logger.error(f"Error getting table schema: {e}")
            return ""

    def get_table_row_count(self, table_name: str, connection: DatabaseConnection) -> int:
        """Get the number of rows in a table.

        Args:
            table_name: Name of the table.
            connection: Database connection to use.

        Returns:
            Number of rows in the table.
        """
        try:
            # Get the underlying DuckDB connection
            duckdb_conn = connection.conn

            # Execute directly on the DuckDB connection
            result = duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            count_row = result.fetchone()

            if count_row and len(count_row) > 0:
                return count_row[0]
            return 0
        except Exception as e:
            self.logger.error(f"Error getting table row count: {e}")
            return 0

    def sync_table_to_local(self, table_name: str) -> bool:
        """Sync a table from MotherDuck to local DuckDB.

        Args:
            table_name: Name of the table to sync.

        Returns:
            True if sync was successful, False otherwise.
        """
        with self._sync_lock:
            try:
                # Check if table exists in MotherDuck
                if not self.table_exists(table_name, self.motherduck_conn):
                    self.logger.warning(f"Table {table_name} does not exist in MotherDuck.")
                    return False

                # Get schema from MotherDuck
                schema = self.get_table_schema(table_name, self.motherduck_conn)
                if not schema:
                    self.logger.error(f"Could not get schema for table {table_name} from MotherDuck.")
                    return False

                # If table doesn't exist locally, create it
                if not self.table_exists(table_name, self.local_conn):
                    self.logger.info(f"Creating table {table_name} in local DuckDB.")
                    self.local_conn.execute(schema)

                # Get row count from MotherDuck
                md_row_count = self.get_table_row_count(table_name, self.motherduck_conn)

                # Copy data from MotherDuck to local
                self.logger.info(f"Syncing {md_row_count} rows from MotherDuck to local for table {table_name}.")

                # Drop and recreate the table (full sync strategy)
                self.local_conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                self.local_conn.execute(schema)

                # Copy all data
                self.local_conn.execute(f"INSERT INTO {table_name} SELECT * FROM motherduck.{table_name}")

                # Update sync metadata
                self._update_sync_metadata(table_name, "down", "completed")

                self.logger.info(f"Successfully synced table {table_name} from MotherDuck to local.")
                return True
            except Exception as e:
                self.logger.error(f"Error syncing table {table_name} to local: {e}")
                self._update_sync_metadata(table_name, "down", "failed", str(e))
                return False

    def sync_table_to_motherduck(self, table_name: str) -> bool:
        """Sync a table from local DuckDB to MotherDuck.

        Args:
            table_name: Name of the table to sync.

        Returns:
            True if sync was successful, False otherwise.
        """
        with self._sync_lock:
            try:
                # Check if table exists locally
                if not self.table_exists(table_name, self.local_conn):
                    self.logger.warning(f"Table {table_name} does not exist in local DuckDB.")
                    return False

                # Get schema from local
                schema = self.get_table_schema(table_name, self.local_conn)
                if not schema:
                    self.logger.error(f"Could not get schema for table {table_name} from local DuckDB.")
                    return False

                # If table doesn't exist in MotherDuck, create it
                if not self.table_exists(table_name, self.motherduck_conn):
                    self.logger.info(f"Creating table {table_name} in MotherDuck.")
                    self.motherduck_conn.execute(schema)

                # Get row count from local
                local_row_count = self.get_table_row_count(table_name, self.local_conn)

                # Copy data from local to MotherDuck
                self.logger.info(f"Syncing {local_row_count} rows from local to MotherDuck for table {table_name}.")

                # Drop and recreate the table (full sync strategy)
                self.motherduck_conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                self.motherduck_conn.execute(schema)

                # Copy all data
                self.motherduck_conn.execute(f"INSERT INTO {table_name} SELECT * FROM {table_name}")

                # Update sync metadata
                self._update_sync_metadata(table_name, "up", "completed")

                # Remove from modified tables set
                if table_name in self._tables_modified_locally:
                    self._tables_modified_locally.remove(table_name)

                self.logger.info(f"Successfully synced table {table_name} from local to MotherDuck.")
                return True
            except Exception as e:
                self.logger.error(f"Error syncing table {table_name} to MotherDuck: {e}")
                self._update_sync_metadata(table_name, "up", "failed", str(e))
                return False

    def _update_sync_metadata(
        self, table_name: str, direction: str, status: str, error_message: str = ""
    ) -> None:
        """Update the sync metadata for a table.

        Args:
            table_name: Name of the table.
            direction: 'up' for local to MotherDuck, 'down' for MotherDuck to local.
            status: 'completed' or 'failed'.
            error_message: Error message if status is 'failed'.
        """
        try:
            now = datetime.now()
            self.local_conn.execute(
                """
                INSERT OR REPLACE INTO dewey_sync_metadata
                (table_name, last_sync_time, last_direction, sync_status, error_message)
                VALUES (?, ?, ?, ?, ?)
            """,
                parameters=[table_name, now, direction, status, error_message],
            )
        except Exception as e:
            self.logger.error(f"Error updating sync metadata: {e}")

    def _record_sync_start(self) -> int:
        """Record the start of a sync operation.

        Returns:
            ID of the sync record.
        """
        try:
            now = datetime.now()
            result = self.local_conn.execute(
                """
                INSERT INTO dewey_sync_status
                (start_time, status, tables_synced, records_synced)
                VALUES (?, 'in_progress', 0, 0)
                RETURNING sync_id
            """,
                parameters=[now],
            )

            # Get the last insert ID
            if not result.empty and "sync_id" in result.columns:
                return result["sync_id"][0]

            # Fallback to getting last insert rowid
            result = self.local_conn.execute("SELECT last_insert_rowid() as sync_id")
            return result["sync_id"][0] if not result.empty else 0
        except Exception as e:
            self.logger.error(f"Error recording sync start: {e}")
            return 0

    def _record_sync_end(
        self,
        sync_id: int,
        status: str,
        tables_synced: int,
        records_synced: int,
        error_message: str = "",
    ) -> None:
        """Record the end of a sync operation.

        Args:
            sync_id: ID of the sync record.
            status: 'completed' or 'failed'.
            tables_synced: Number of tables synced.
            records_synced: Number of records synced.
            error_message: Error message if status is 'failed'.
        """
        try:
            now = datetime.now()
            self.local_conn.execute(
                """
                UPDATE dewey_sync_status
                SET end_time = ?, status = ?, tables_synced = ?, records_synced = ?, error_message = ?
                WHERE sync_id = ?
            """,
                parameters=[now, status, tables_synced, records_synced, error_message, sync_id],
            )

            if status == "completed":
                self._last_sync_time = now
        except Exception as e:
            self.logger.error(f"Error recording sync end: {e}")

    def mark_table_modified(self, table_name: str) -> None:
        """Mark a table as modified locally, scheduling it for sync to MotherDuck.

        Args:
            table_name: Name of the table.
        """
        with self._sync_lock:
            self.logger.debug(f"Marking table {table_name} as modified locally")
            self._tables_modified_locally.add(table_name)

    def sync_all_to_local(self) -> bool:
        """Sync all tables from MotherDuck to local DuckDB.

        Returns:
            True if all tables were synced successfully, False otherwise.
        """
        with self._sync_lock:
            sync_id = self._record_sync_start()
            tables_synced = 0
            records_synced = 0
            success = True

            try:
                # Get list of tables from MotherDuck
                md_tables = self.list_tables(self.motherduck_conn)
                self.logger.info(f"Found {len(md_tables)} tables in MotherDuck.")

                # Sync each table
                for table_name in md_tables:
                    # Skip system tables and sync metadata tables
                    if table_name.startswith("sqlite_") or table_name.startswith("dewey_sync_"):
                        continue

                    # Sync table to local
                    table_success = self.sync_table_to_local(table_name)
                    success = success and table_success

                    if table_success:
                        tables_synced += 1
                        records_synced += self.get_table_row_count(table_name, self.local_conn)

                # Record sync completion
                status = "completed" if success else "partial"
                self._record_sync_end(sync_id, status, tables_synced, records_synced)

                self.logger.info(
                    f"Sync from MotherDuck to local completed. {tables_synced}/{len(md_tables)} tables synced."
                )
                return success
            except Exception as e:
                self.logger.error(f"Error syncing all tables to local: {e}")
                self._record_sync_end(sync_id, "failed", tables_synced, records_synced, str(e))
                return False

    def sync_modified_to_motherduck(self) -> bool:
        """Sync all locally modified tables to MotherDuck.

        Returns:
            True if all tables were synced successfully, False otherwise.
        """
        with self._sync_lock:
            sync_id = self._record_sync_start()
            tables_synced = 0
            records_synced = 0
            success = True

            try:
                # Get list of modified tables
                modified_tables = list(self._tables_modified_locally)
                self.logger.info(f"Found {len(modified_tables)} locally modified tables to sync.")

                # Sync each modified table
                for table_name in modified_tables:
                    # Sync table to MotherDuck
                    table_success = self.sync_table_to_motherduck(table_name)
                    success = success and table_success

                    if table_success:
                        tables_synced += 1
                        records_synced += self.get_table_row_count(table_name, self.motherduck_conn)

                # Record sync completion
                status = "completed" if success else "partial"
                self._record_sync_end(sync_id, status, tables_synced, records_synced)

                self.logger.info(
                    f"Sync from local to MotherDuck completed. {tables_synced}/{len(modified_tables)} tables synced."
                )
                return success
            except Exception as e:
                self.logger.error(f"Error syncing modified tables to MotherDuck: {e}")
                self._record_sync_end(sync_id, "failed", tables_synced, records_synced, str(e))
                return False

    def sync_all(self) -> bool:
        """Perform a full bidirectional sync.

        This first syncs from MotherDuck to local, then from local back to MotherDuck
        for any modified tables.

        Returns:
            True if sync was successful, False otherwise.
        """
        # First sync from MotherDuck to local
        success = self.sync_all_to_local()

        # Then sync modified tables back to MotherDuck
        if success and self._tables_modified_locally:
            success = self.sync_modified_to_motherduck()

        return success

    def start_auto_sync(self) -> None:
        """Start the automatic sync thread.

        This starts a background thread that syncs data periodically
        based on the sync_interval.
        """
        if self._sync_thread and self._sync_thread.is_alive():
            self.logger.info("Automatic sync already running.")
            return

        self._stop_sync_thread.clear()
        self._sync_thread = threading.Thread(
            target=self._auto_sync_worker, daemon=True, name="DuckDBSync-AutoSync"
        )
        self._sync_thread.start()
        self.logger.info(f"Automatic sync started with interval of {self.sync_interval} seconds.")

    def stop_auto_sync(self) -> None:
        """Stop the automatic sync thread."""
        if self._sync_thread and self._sync_thread.is_alive():
            self.logger.info("Stopping automatic sync...")
            self._stop_sync_thread.set()
            # Don't join here to avoid blocking
        else:
            self.logger.info("Automatic sync was not running.")

    def _auto_sync_worker(self) -> None:
        """Worker function for the automatic sync thread."""
        self.logger.info("Auto-sync worker thread started.")

        while not self._stop_sync_thread.is_set():
            try:
                # Check if sync is needed
                sync_needed = self._sync_needed()

                if sync_needed:
                    self.logger.info("Automatic sync triggered.")
                    self.sync_all()

                # Sleep until next check, but check for stop signal every second
                for _ in range(min(60, self.sync_interval)):
                    if self._stop_sync_thread.is_set():
                        break
                    time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in auto-sync worker: {e}")
                # Sleep a bit before retrying
                time.sleep(10)

    def _sync_needed(self) -> bool:
        """Check if a sync is needed based on time and modified tables.

        Returns:
            True if sync is needed, False otherwise.
        """
        # If we have locally modified tables, sync is needed
        if self._tables_modified_locally:
            return True

        # If we've never synced before, sync is needed
        if not self._last_sync_time:
            return True

        # If we're past the sync interval, sync is needed
        now = datetime.now()
        sync_age = now - self._last_sync_time

        if sync_age.total_seconds() > self.sync_interval:
            return True

        # No need to sync
        return False

    def close(self) -> None:
        """Close connections and stop background threads."""
        self.stop_auto_sync()

        # Wait for sync thread to terminate
        if self._sync_thread and self._sync_thread.is_alive():
            self.logger.info("Waiting for sync thread to terminate...")
            self._sync_thread.join(timeout=5)

        # Close connections
        try:
            if hasattr(self, "local_conn") and self.local_conn:
                self.local_conn.close()
                self.logger.info("Local connection closed.")

            if hasattr(self, "motherduck_conn") and self.motherduck_conn:
                self.motherduck_conn.close()
                self.logger.info("MotherDuck connection closed.")
        except Exception as e:
            self.logger.error(f"Error closing connections: {e}")

    def __del__(self) -> None:
        """Destructor to ensure resources are cleaned up."""
        self.close()

    def run(self) -> None:
        """Run the DuckDB synchronization."""
        self.sync_all()


# Singleton instance
_duckdb_sync_instance = None


def get_duckdb_sync(
    local_db_path: Optional[str] = None,
    motherduck_db: Optional[str] = None,
    motherduck_token: Optional[str] = None,
    sync_interval: Optional[int] = None,
    max_sync_age: Optional[int] = None,
    auto_sync: bool = True,
) -> DuckDBSync:
    """Get or create the DuckDBSync singleton instance.

    Args:
        local_db_path: Path to the local DuckDB file.
        motherduck_db: MotherDuck database name.
        motherduck_token: MotherDuck token.
        sync_interval: Time between automatic syncs (in seconds).
        max_sync_age: Maximum time to allow before forcing a sync (in seconds).
        auto_sync: Whether to start automatic sync thread.

    Returns:
        DuckDBSync instance.
    """
    global _duckdb_sync_instance

    if _duckdb_sync_instance is None:
        _duckdb_sync_instance = DuckDBSync(
            local_db_path=local_db_path,
            motherduck_db=motherduck_db,
            motherduck_token=motherduck_token,
            sync_interval=sync_interval,
            max_sync_age=max_sync_age,
            auto_sync=auto_sync,
        )

    return _duckdb_sync_instance
