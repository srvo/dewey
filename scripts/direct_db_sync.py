#!/usr/bin/env python
"""
    Direct DB sync using DuckDB Python API.
    Syncs tables from MotherDuck to local DuckDB database directly.
    Also syncs schema changes from local back to MotherDuck.
"""

import argparse
import logging
import os
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

# Ensure the project root is in the path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

import duckdb

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DBSyncer:
    """Class to handle synchronization between MotherDuck and local DuckDB."""

    def __init__(self, local_db_path: str, md_db_name: str, token: str):
    """
        Initialize the syncer with connection details.

        Args:
        -----
            local_db_path: Path to local DuckDB file
            md_db_name: MotherDuck database name
            token: MotherDuck authentication token

    """
        self.local_db_path = local_db_path
        self.md_db_name = md_db_name
        self.md_connection_string = f"md:{md_db_name}?motherduck_token={token}"
        self.batch_size = 10000
        self.max_retries = 5  # Increased from 3 to 5
        self.retry_delay_base = 2  # Base seconds for exponential backoff
        self.local_conn = None
        self.md_conn = None
        self.temp_db_path = None
        self.copy_created = False

    def connect(self, use_copy: bool = False) -> bool:
    """
        Establish connections to both databases.

        Args:
        -----
            use_copy: Whether to use a copy of the local database to avoid locks

        Returns:
        --------
            True if connections successful, False otherwise

    """
        try:
            # First connect to MotherDuck as it doesn't have locking issues
            self.md_conn = duckdb.connect(self.md_connection_string)
            logger.info("Successfully connected to MotherDuck")

            # If use_copy is True, create a temporary copy of the database
            if use_copy and os.path.exists(self.local_db_path):
                # Create a temporary file and copy the database
                fd, self.temp_db_path = tempfile.mkstemp(suffix=".duckdb")
                os.close(fd)  # Close the file descriptor

                logger.info(
                    f"Creating temporary copy of database at {self.temp_db_path}"
                )
                try:
                    shutil.copy2(self.local_db_path, self.temp_db_path)
                    logger.info(f"Successfully copied database to {self.temp_db_path}")
                    self.copy_created = True

                    # Connect to the copy instead
                    self.local_conn = duckdb.connect(self.temp_db_path)
                    logger.info("Connected to temporary database copy")

                    # Add metadata about where this copy came from
                    try:
                        self.local_conn.execute("""
                            CREATE TABLE IF NOT EXISTS dewey_db_copy_metadata (
                                original_path TEXT,
                                copy_time TIMESTAMP,
                                purpose TEXT
                            )
                        """)
                        self.local_conn.execute(
                            """
                            INSERT INTO dewey_db_copy_metadata VALUES (?, ?, ?)
                        """,
                            [
                                self.local_db_path,
                                time.strftime("%Y-%m-%d %H:%M:%S"),
                                "sync",
                            ],
                        )
                    except Exception as e:
                        logger.warning(f"Could not add metadata to copy: {e}")

                    # Initialize sync metadata table
                    self._init_sync_metadata()
                    return True

                except Exception as e:
                    logger.error(f"Failed to create database copy: {e}")
                    # Clean up the temp file
                    if os.path.exists(self.temp_db_path):
                        os.unlink(self.temp_db_path)
                    self.temp_db_path = None
                    # Fall back to direct connection
                    use_copy = False

            # If not using a copy, try connecting directly with retries
            if not use_copy:
                for attempt in range(self.max_retries):
                    try:
                        self.local_conn = duckdb.connect(self.local_db_path)
                        logger.info(
                            f"Successfully connected to local database on attempt {attempt+1}"
                        )
                        # Initialize sync metadata table
                        self._init_sync_metadata()
                        return True
                    except Exception as e:
                        if "lock" in str(e).lower() and attempt < self.max_retries - 1:
                            # Calculate backoff with exponential delay and jitter
                            delay = self.retry_delay_base * (2**attempt)
                            jitter = random.uniform(0.8, 1.2)  # 20% jitter
                            actual_delay = delay * jitter

                            logger.warning(
                                f"Database locked, retrying in {actual_delay:.2f} seconds "
                                f"(attempt {attempt+1}/{self.max_retries})"
                            )
                            time.sleep(actual_delay)
                        else:
                            logger.error(
                                f"Failed to connect to local database after {attempt+1} attempts: {e}"
                            )
                            # Try to get info about the locking process
                            self._check_lock_info()
                            return False

            return True
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def _check_lock_info(self):
        """Try to get information about what process is locking the database."""
        try:
            # Only works on Linux/macOS
            if sys.platform in ("linux", "darwin"):
                import subprocess

                # Check if lsof command exists
                try:
                    subprocess.run(["which", "lsof"], check=True, capture_output=True)

                    # Run lsof on the database file
                    result = subprocess.run(
                        ["lsof", self.local_db_path], capture_output=True, text=True
                    )

                    if result.returncode == 0:
                        logger.info(f"Database file is locked by:\n{result.stdout}")
                    else:
                        logger.warning("Could not determine locking process")
                except:
    pass  # Placeholder added by quick_fix.py
                    logger.warning("Could not check file locks (lsof not available)")
        except Exception as e:
            logger.warning(f"Error checking lock info: {e}")

    def _init_sync_metadata(self):
        """Initialize the sync metadata table in the local database."""
        try:
            # Try to drop the existing table if it's causing problems
            try:
                self.local_conn.execute("DROP TABLE IF EXISTS dewey_sync_metadata")
                logger.debug(
                    "Dropped existing sync metadata table due to schema issues"
                )
            except Exception as e:
                logger.warning(f"Failed to drop metadata table: {e}")

            # Create a new table with all required columns
            self.local_conn.execute("""
                CREATE TABLE dewey_sync_metadata (
                    table_name TEXT PRIMARY KEY,
                    last_sync_time TIMESTAMP,
                    last_sync_mode TEXT DEFAULT 'full',
                    status TEXT DEFAULT 'pending',
                    error_message TEXT DEFAULT '',
                    records_synced INTEGER DEFAULT 0
                )
            """)
            logger.debug("Created sync metadata table with full schema")

        except Exception as e:
            logger.error(f"Error initializing sync metadata: {e}")

    def _get_last_sync_time(self, table_name: str) -> str | None:
    """
        Get the last sync time for a table.

        Args:
        -----
            table_name: Name of the table

        Returns:
        --------
            Timestamp string of last sync or None if never synced

    """
        try:
            result = self.local_conn.execute(
                "SELECT last_sync_time FROM dewey_sync_metadata WHERE table_name = ?",
                [table_name],
            ).fetchone()

            if result and result[0]:
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Error getting last sync time: {e}")
            return None

    def _update_sync_metadata(
        self,
        table_name: str,
        sync_mode: str,
        status: str,
        error_message: str = "",
        records_synced: int = 0,
    ):
    """
        Update the sync metadata for a table.

        Args:
        -----
            table_name: Name of the table
            sync_mode: 'full' or 'incremental'
            status: 'completed' or 'failed'
            error_message: Error message if status is 'failed'
            records_synced: Number of records synced

    """
        try:
            now = time.strftime("%Y-%m-%d %H:%M:%S")

            # Get current records synced count if available
            current_count = 0
            try:
                result = self.local_conn.execute(
                    "SELECT records_synced FROM dewey_sync_metadata WHERE table_name = ?",
                    [table_name],
                ).fetchone()
                if result:
                    current_count = result[0] or 0
            except Exception as e:
                logger.debug(f"Error getting current records count, assuming 0: {e}")

            # Add new records to existing count
            total_records = current_count + records_synced

            # Try simple version first, if it fails we need to reinitialize
            try:
                self.local_conn.execute(
                    """
                    INSERT OR REPLACE INTO dewey_sync_metadata
                    (table_name, last_sync_time, last_sync_mode, status, error_message, records_synced)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    [table_name, now, sync_mode, status, error_message, total_records],
                )

                logger.debug(
                    f"Updated sync metadata for {table_name}, total records: {total_records:,}"
                )
                return
            except Exception as e:
                logger.warning(f"Error with metadata update: {e}, recreating table")
                self._init_sync_metadata()

            # Try again after reinitializing
            self.local_conn.execute(
                """
                INSERT OR REPLACE INTO dewey_sync_metadata
                (table_name, last_sync_time, last_sync_mode, status, error_message, records_synced)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                [table_name, now, sync_mode, status, error_message, total_records],
            )

            logger.debug(
                f"Updated sync metadata for {table_name}, total records: {total_records:,}"
            )
        except Exception as e:
            logger.error(f"Error updating sync metadata: {e}")

    def close(self):
        """Close database connections and clean up temporary files."""
        if self.md_conn:
            self.md_conn.close()
            self.md_conn = None

        if self.local_conn:
            self.local_conn.close()
            self.local_conn = None

        # If we created a temporary copy, clean it up
        if self.temp_db_path and os.path.exists(self.temp_db_path):
            try:
                logger.info(
                    f"Cleaning up temporary database copy at {self.temp_db_path}"
                )
                os.unlink(self.temp_db_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary database: {e}")

    def verify_table_data(self, table_name: str) -> bool:
    """
        Verify that data in both databases is consistent.

        Args:
        -----
            table_name: The table to verify

        Returns:
        --------
            True if verification passed, False otherwise

    """
        try:
            # Check if table exists in both databases
            md_exists = self.check_table_exists(table_name, self.md_conn)
            local_exists = self.check_table_exists(table_name, self.local_conn)

            if not md_exists:
                logger.warning(
                    f"Table {table_name} doesn't exist in MotherDuck, skipping verification"
                )
                return False

            if not local_exists:
                logger.warning(
                    f"Table {table_name} doesn't exist locally, skipping verification"
                )
                return False

            # Compare row counts
            md_count = self.md_conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]
            local_count = self.local_conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

            logger.info(
                f"Table {table_name} row counts: MotherDuck={md_count:,}, Local={local_count:,}"
            )

            if md_count != local_count:
                logger.warning(
                    f"Row count mismatch for {table_name}: MotherDuck={md_count:,}, Local={local_count:,}"
                )

                # Try to get details about the differences
                try:
                    # Check if table has a primary key
                    pk_cols = self.get_primary_key_columns(table_name, self.md_conn)

                    if pk_cols:
                        # We have a primary key, so we can check which records are different
                        pk_col = pk_cols[0]  # Use first primary key column

                        logger.info(
                            f"Checking for missing records using primary key {pk_col}"
                        )

                        # Check for records in MotherDuck but not in local
                        try:
                            md_only_query = f"""
                                SELECT COUNT(*) FROM (
                                    SELECT a.{pk_col} FROM
                                    (SELECT {pk_col} FROM {table_name}) a
                                    LEFT JOIN md.dewey.{table_name} b
                                    ON a.{pk_col} = b.{pk_col}
                                    WHERE b.{pk_col} IS NULL
                                )
                            """
                            md_only = self.local_conn.execute(md_only_query).fetchone()[
                                0
                            ]
                            logger.info(
                                f"Records in local but not in MotherDuck: {md_only:,}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Could not check for local-only records: {e}"
                            )

                        # Check for records in local but not in MotherDuck
                        try:
                            local_only_query = f"""
                                SELECT COUNT(*) FROM (
                                    SELECT a.{pk_col} FROM
                                    md.dewey.{table_name} a
                                    LEFT JOIN {table_name} b
                                    ON a.{pk_col} = b.{pk_col}
                                    WHERE b.{pk_col} IS NULL
                                )
                            """
                            local_only = self.local_conn.execute(
                                local_only_query
                            ).fetchone()[0]
                            logger.info(
                                f"Records in MotherDuck but not in local: {local_only:,}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Could not check for MotherDuck-only records: {e}"
                            )

                    return False
                except Exception as e:
                    logger.warning(f"Could not get detailed verification: {e}")
                    return False

            # Check a sample of rows for data integrity
            try:
                # Get schema to compare columns
                md_schema = self.get_table_schema(table_name, self.md_conn)
                local_schema = self.get_table_schema(table_name, self.local_conn)

                # Find common columns
                common_cols = set(md_schema.keys()).intersection(
                    set(local_schema.keys())
                )

                if common_cols:
                    # Get a sample of records
                    sample_size = min(10, md_count)
                    if sample_size > 0:
                        logger.info(
                            f"Checking sample of {sample_size} records for data integrity"
                        )

                        # Get primary key or another unique column for ordering
                        pk_result = self.md_conn.execute(f"""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_name = '{table_name}' AND is_primary_key
                            ORDER BY column_index
                        """).fetchall()

                        order_cols = (
                            [row[0] for row in pk_result]
                            if pk_result
                            else ["id", "msg_id", "email_id"]
                        )

                        # Find a usable order column
                        order_col = None
                        for col in order_cols:
                            if col in common_cols:
                                order_col = col
                                break

                        if order_col:
                            # Sample records with consistent ordering
                            md_sample = self.md_conn.execute(
                                f"SELECT * FROM {table_name} ORDER BY {order_col} LIMIT {sample_size}"
                            ).fetchall()

                            local_sample = self.local_conn.execute(
                                f"SELECT * FROM {table_name} ORDER BY {order_col} LIMIT {sample_size}"
                            ).fetchall()

                            # Compare samples
                            if len(md_sample) != len(local_sample):
                                logger.warning(
                                    f"Sample size mismatch: MD={len(md_sample)}, Local={len(local_sample)}"
                                )
                                return False

                            # Get column names for both connections
                            md_cols = [col[0] for col in self.md_conn.description]
                            local_cols = [col[0] for col in self.local_conn.description]

                            # Check each row in the sample
                            for i in range(len(md_sample)):
                                md_row = md_sample[i]
                                local_row = local_sample[i]

                                # Check values for each common column
                                for col in common_cols:
                                    md_idx = md_cols.index(col)
                                    local_idx = local_cols.index(col)

                                    if md_row[md_idx] != local_row[local_idx]:
                                        logger.warning(
                                            f"Data mismatch in row {i+1}, column {col}: "
                                            f"MD={md_row[md_idx]}, Local={local_row[local_idx]}"
                                        )
                                        return False

                            logger.info(
                                f"Sample data verification passed for {table_name}"
                            )
            except Exception as e:
                logger.warning(f"Could not verify sample data: {e}")

            return True

        except Exception as e:
            logger.error(f"Error verifying table {table_name}: {e}")
            return False

    def list_tables(self, connection) -> list[str]:
    """
        Get list of tables from a connection.

        Args:
        -----
            connection: Database connection

        Returns:
        --------
            List of table names

    """
        tables = connection.execute("SHOW TABLES").fetchall()
        table_names = [table[0] for table in tables]

        # Filter out system tables
        filtered_tables = [
            t
            for t in table_names
            if not t.startswith("sqlite_")
            and not t.startswith("dewey_sync_")
            and not t.startswith("information_schema")
        ]
        return filtered_tables

    def get_table_schema(self, table_name: str, connection) -> dict[str, str]:
    """
        Get the schema for a table.

        Args:
        -----
            table_name: Name of the table
            connection: Database connection

        Returns:
        --------
            Dictionary of column names to column types

    """
        schema_result = connection.execute(f"DESCRIBE {table_name}").fetchall()
        schema = {}

        for col in schema_result:
            col_name = col[0]
            col_type = col[1]
            schema[col_name] = col_type

        return schema

    def sync_schema_to_motherduck(
        self, table_name: str, local_schema: dict[str, str], md_schema: dict[str, str]
    ) -> bool:
    """
        Sync schema changes from local to MotherDuck.

        Args:
        -----
            table_name: Name of the table
            local_schema: Schema from local database
            md_schema: Schema from MotherDuck

        Returns:
        --------
            True if successful, False otherwise

    """
        # Find columns in local but not in MotherDuck
        new_columns = {
            col: dtype for col, dtype in local_schema.items() if col not in md_schema
        }

        if not new_columns:
            logger.info(f"  No schema changes to sync for {table_name}")
            return True

        logger.info(f"  Found {len(new_columns)} new columns to add to MotherDuck")

        try:
            for col_name, col_type in new_columns.items():
                logger.info(
                    f"  Adding column {col_name} ({col_type}) to {table_name} in MotherDuck"
                )
                self.md_conn.execute(
                    f'ALTER TABLE {table_name} ADD COLUMN "{col_name}" {col_type}'
                )
            return True
        except Exception as e:
            logger.error(f"  Error syncing schema for {table_name}: {e}")
            return False

    def create_table_in_motherduck(
        self, table_name: str, local_schema: dict[str, str]
    ) -> bool:
    """
        Create a table in MotherDuck based on local schema.

        Args:
        -----
            table_name: Name of the table
            local_schema: Schema from local database

        Returns:
        --------
            True if successful, False otherwise

    """
        try:
            create_stmt_parts = [
                f'"{col_name}" {col_type}'
                for col_name, col_type in local_schema.items()
            ]
            create_stmt = f'CREATE TABLE {table_name} ({", ".join(create_stmt_parts)})'

            logger.info(f"  Creating table {table_name} in MotherDuck")
            self.md_conn.execute(create_stmt)
            return True
        except Exception as e:
            logger.error(f"  Error creating table {table_name} in MotherDuck: {e}")
            return False

    def check_table_exists(self, table_name: str, connection) -> bool:
    """
        Check if a table exists in the database.

        Args:
        -----
            table_name: Name of the table
            connection: Database connection

        Returns:
        --------
            True if table exists, False otherwise

    """
        try:
            result = connection.execute(
                f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}')"
            ).fetchone()[0]
            return result
        except Exception:
            return False

    def get_primary_key_columns(self, table_name: str, connection) -> list[str]:
    """
        Get the primary key columns for a table.

        Args:
        -----
            table_name: Name of the table
            connection: Database connection

        Returns:
        --------
            List of primary key column names

    """
        try:
            # First try using is_primary_key which is available in newer DuckDB versions
            try:
                pk_result = connection.execute(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}' AND is_primary_key
                    ORDER BY column_index
                """).fetchall()

                if pk_result:
                    return [row[0] for row in pk_result]
            except Exception:
                # is_primary_key may not be available, try alternate approach
                pass

            # Try using constraint info if available
            try:
                constraint_result = connection.execute(f"""
                    SELECT column_name
                    FROM information_schema.key_column_usage
                    WHERE table_name = '{table_name}'
                    AND constraint_name LIKE '%primary%'
                    ORDER BY ordinal_position
                """).fetchall()

                if constraint_result:
                    return [row[0] for row in constraint_result]
            except Exception:
                # constraint info may not be available, try another approach
                pass

            # Fall back to common ID column names
            common_pk_names = ["id", "msg_id", "email_id", "message_id", "ID", "Id"]

            # Check which of these columns exist
            for col_name in common_pk_names:
                try:
                    result = connection.execute(f"""
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = '{table_name}'
                        AND column_name = '{col_name}'
                    """).fetchone()

                    if result:
                        return [col_name]
                except Exception:
                    continue

            # If no primary key found, return empty list
            return []

        except Exception as e:
            logger.error(f"Error getting primary key for {table_name}: {e}")
            return []

    def _sync_data_in_batches(
        self, table_name: str, incremental: bool, last_sync_time: str | None
    ) -> int:
    """
        Sync data in batches to avoid memory issues.

        Args:
        -----
            table_name: Name of the table
            incremental: Whether to sync incrementally
            last_sync_time: Last sync time for incremental sync

        Returns:
        --------
            Number of records synced

    """
        # Get primary key for incremental sync and ordering
        pk_cols = self.get_primary_key_columns(table_name, self.md_conn)

        # If no primary key, try to find an ID column to use for ordering
        order_by_cols = (
            pk_cols if pk_cols else ["id", "msg_id", "email_id", "ID", "Id", "iD"]
        )

        # Construct order by clause
        order_by = None
        for col in order_by_cols:
            try:
                # Check if column exists
                exists = self.md_conn.execute(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}' AND column_name = '{col}'
                """).fetchone()

                if exists:
                    order_by = col
                    break
            except:
                continue

        # Get total count for progress reporting
        try:
            if incremental and last_sync_time and order_by:
                count_query = f"""
                    SELECT COUNT(*) FROM {table_name}
                    WHERE last_updated >= '{last_sync_time}'
                    OR created_at >= '{last_sync_time}'
                """
            else:
                count_query = f"SELECT COUNT(*) FROM {table_name}"

            total_count = self.md_conn.execute(count_query).fetchone()[0]
            logger.info(f"  Total records to sync: {total_count:,}")
        except Exception as e:
            logger.warning(f"  Error getting total count: {e}")
            total_count = None

        # Sync in batches
        offset = 0
        batch_num = 1
        total_synced = 0

        while True:
            try:
                # Build query with proper WHERE clause for incremental sync
                if incremental and last_sync_time:
                    query = f"""
                        SELECT * FROM {table_name}
                        WHERE last_updated >= '{last_sync_time}'
                        OR created_at >= '{last_sync_time}'
                    """
                else:
                    query = f"SELECT * FROM {table_name}"

                # Add ORDER BY if we have a column to order by
                if order_by:
                    query += f" ORDER BY {order_by}"

                # Add LIMIT and OFFSET
                query += f" LIMIT {self.batch_size} OFFSET {offset}"

                # Execute query
                batch_df = self.md_conn.execute(query).fetch_df()

                # If no data returned, we're done
                if batch_df.empty:
                    break

                batch_count = len(batch_df)
                logger.info(
                    f"  Syncing batch {batch_num} with {batch_count:,} records (offset {offset:,})"
                )

                # Insert into local database
                self.local_conn.execute(
                    f"INSERT INTO {table_name} SELECT * FROM batch_df"
                )

                # Update progress
                total_synced += batch_count
                progress = (
                    100 * (total_synced / total_count) if total_count else "unknown"
                )
                if isinstance(progress, float):
                    progress = f"{progress:.1f}%"
                logger.info(
                    f"  Progress: {total_synced:,}/{total_count:,} records ({progress})"
                )

                # Increment for next batch
                offset += batch_count
                batch_num += 1

                # If this batch was smaller than the batch size, we're done
                if batch_count < self.batch_size:
                    break

            except Exception as e:
                logger.error(f"  Error syncing batch {batch_num}: {e}")
                if batch_num > 1:
                    # We've successfully synced some data, so continue
                    logger.warning("  Continuing with next batch...")
                    offset += self.batch_size
                    batch_num += 1
                else:
                    # First batch failed, so abort
                    logger.error("  First batch failed, aborting sync")
                    return 0

        logger.info(f"  Completed syncing {total_synced:,} records for {table_name}")
        return total_synced  # Return the total number of records synced

    def sync_table_from_md_to_local(
        self, table_name: str, incremental: bool = False
    ) -> bool:
    """
        Sync a table from MotherDuck to local.

        Args:
        -----
            table_name: Name of the table
            incremental: Whether to sync only new data since last sync

        Returns:
        --------
            True if successful, False otherwise

    """
        try:
            # Check if table exists in local database
            local_exists = self.check_table_exists(table_name, self.local_conn)

            # If table doesn't exist locally, get schema from MotherDuck and create it
            if not local_exists:
                logger.info(f"  Table {table_name} doesn't exist locally, creating...")

                # Get schema from MotherDuck
                md_schema = self.get_table_schema(table_name, self.md_conn)

                # Create table in local
                create_stmt_parts = [
                    f'"{col_name}" {col_type}'
                    for col_name, col_type in md_schema.items()
                ]
                create_stmt = (
                    f'CREATE TABLE {table_name} ({", ".join(create_stmt_parts)})'
                )
                self.local_conn.execute(create_stmt)
                logger.info(f"  Created table {table_name} in local database")

                # Do a full sync
                incremental = False
            else:
                # If it exists, check for schema differences
                logger.info(f"  Table {table_name} exists locally, checking schema...")
                local_schema = self.get_table_schema(table_name, self.local_conn)
                md_schema = self.get_table_schema(table_name, self.md_conn)

                # Find columns in MotherDuck but not in local
                new_columns = {
                    col: dtype
                    for col, dtype in md_schema.items()
                    if col not in local_schema
                }

                # Add any new columns to local
                if new_columns:
                    logger.info(
                        f"  Found {len(new_columns)} new columns to add to local database"
                    )
                    for col_name, col_type in new_columns.items():
                        logger.info(
                            f"  Adding column {col_name} ({col_type}) to {table_name} in local database"
                        )
                        try:
                            self.local_conn.execute(
                                f'ALTER TABLE {table_name} ADD COLUMN "{col_name}" {col_type}'
                            )
                        except Exception as e:
                            logger.warning(f"  Error adding column {col_name}: {e}")

            # Check if the table has a primary key for incremental sync
            if incremental:
                # Get primary key info
                pk_cols = self.get_primary_key_columns(table_name, self.md_conn)

                if not pk_cols:
                    logger.warning(
                        f"  Table {table_name} doesn't have a primary key, doing full sync"
                    )
                    incremental = False

            # If incremental, get the last sync time
            last_sync_time = None
            if incremental:
                last_sync_time = self._get_last_sync_time(table_name)
                if not last_sync_time:
                    logger.info(
                        f"  No previous sync found for {table_name}, doing full sync"
                    )
                    incremental = False
                else:
                    logger.info(f"  Last sync time for {table_name}: {last_sync_time}")

            # Clear the local table if doing a full sync
            if not incremental:
                logger.info(f"  Clearing local table {table_name} for full sync")
                self.local_conn.execute(f"DELETE FROM {table_name}")

            # Sync data in batches
            records_synced = self._sync_data_in_batches(
                table_name, incremental, last_sync_time
            )

            # Update sync metadata
            sync_mode = "incremental" if incremental else "full"
            self._update_sync_metadata(
                table_name, sync_mode, "completed", records_synced=records_synced
            )
            logger.info(f"  Successfully synced {table_name} from MotherDuck to local")

            return True

        except Exception as e:
            logger.error(f"  Error syncing {table_name} from MotherDuck to local: {e}")
            try:
                self._update_sync_metadata(table_name, "failed", "error", str(e))
            except Exception as e2:
                logger.error(f"  Error updating sync metadata: {e2}")
            return False

    def sync_table_to_motherduck(self, table_name: str) -> bool:
    """
        Sync a table from local to MotherDuck.

        Args:
        -----
            table_name: Name of the table

        Returns:
        --------
            True if successful, False otherwise

    """
        try:
            # Check if table exists in MotherDuck
            md_exists = self.check_table_exists(table_name, self.md_conn)

            # Get local schema
            local_schema = self.get_table_schema(table_name, self.local_conn)

            # If table doesn't exist in MotherDuck, create it
            if not md_exists:
                logger.info(
                    f"  Table {table_name} doesn't exist in MotherDuck, creating..."
                )
                success = self.create_table_in_motherduck(table_name, local_schema)
                if not success:
                    return False
            else:
                # If it exists, sync schema changes
                logger.info(
                    f"  Table {table_name} exists in MotherDuck, checking schema..."
                )
                md_schema = self.get_table_schema(table_name, self.md_conn)
                success = self.sync_schema_to_motherduck(
                    table_name, local_schema, md_schema
                )
                if not success:
                    return False

            # Sync data
            # For now, we'll just back up and replace the entire table
            # In the future, we could implement incremental sync with change tracking

            logger.info(f"  Backing up table {table_name} in MotherDuck")
            backup_table = f"{table_name}_backup_{int(time.time())}"
            self.md_conn.execute(
                f"CREATE TABLE {backup_table} AS SELECT * FROM {table_name}"
            )

            logger.info(f"  Clearing table {table_name} in MotherDuck")
            self.md_conn.execute(f"DELETE FROM {table_name}")

            logger.info("  Syncing data from local to MotherDuck")

            # Read local data in batches
            offset = 0
            batch_num = 1
            total_synced = 0

            # Get total count for progress reporting
            try:
                count_query = f"SELECT COUNT(*) FROM {table_name}"
                total_count = self.local_conn.execute(count_query).fetchone()[0]
                logger.info(f"  Total records to sync: {total_count:,}")
            except Exception as e:
                logger.warning(f"  Error getting total count: {e}")
                total_count = None

            while True:
                try:
                    query = f"SELECT * FROM {table_name} LIMIT {self.batch_size} OFFSET {offset}"
                    batch_df = self.local_conn.execute(query).fetch_df()

                    # If no data returned, we're done
                    if batch_df.empty:
                        break

                    batch_count = len(batch_df)
                    logger.info(
                        f"  Syncing batch {batch_num} with {batch_count:,} records (offset {offset:,})"
                    )

                    # Insert into MotherDuck
                    self.md_conn.execute(
                        f"INSERT INTO {table_name} SELECT * FROM batch_df"
                    )

                    # Update progress
                    total_synced += batch_count
                    progress = (
                        100 * (total_synced / total_count) if total_count else "unknown"
                    )
                    if isinstance(progress, float):
                        progress = f"{progress:.1f}%"
                    logger.info(
                        f"  Progress: {total_synced:,}/{total_count:,} records ({progress})"
                    )

                    # Increment for next batch
                    offset += batch_count
                    batch_num += 1

                    # If this batch was smaller than the batch size, we're done
                    if batch_count < self.batch_size:
                        break

                except Exception as e:
                    logger.error(f"  Error syncing batch {batch_num}: {e}")
                    if batch_num > 1:
                        # We've synced at least one batch, continue with next
                        offset += self.batch_size
                        batch_num += 1
                    else:
                        # First batch failed, restore from backup
                        logger.error("  Sync failed, restoring from backup")
                        self.md_conn.execute(f"DELETE FROM {table_name}")
                        self.md_conn.execute(
                            f"INSERT INTO {table_name} SELECT * FROM {backup_table}"
                        )
                        self.md_conn.execute(f"DROP TABLE {backup_table}")
                        return False

            # Drop backup table if sync was successful
            logger.info(f"  Dropping backup table {backup_table}")
            self.md_conn.execute(f"DROP TABLE {backup_table}")

            logger.info(f"  Successfully synced {table_name} from local to MotherDuck")
            return True

        except Exception as e:
            logger.error(f"  Error syncing {table_name} from local to MotherDuck: {e}")
            return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Sync tables between MotherDuck and local DuckDB"
    )
    parser.add_argument("--local-db", type=str, help="Path to local DuckDB file")
    parser.add_argument("--md-db", type=str, help="MotherDuck database name")
    parser.add_argument("--token", type=str, help="MotherDuck authentication token")
    parser.add_argument("--tables", type=str, help="Tables to sync (comma-separated)")
    parser.add_argument(
        "--exclude", type=str, help="Tables to exclude (comma-separated)"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Use incremental sync (where possible)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=10000, help="Batch size for data transfer"
    )
    parser.add_argument(
        "--max-retries", type=int, default=5, help="Max retries for database connection"
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=2,
        help="Base delay between retries (seconds)",
    )
    parser.add_argument(
        "--sync-direction",
        type=str,
        choices=["md-to-local", "local-to-md", "both"],
        default="both",
        help="Direction of sync",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--force-full",
        action="store_true",
        help="Force full sync even if incremental is specified",
    )
    parser.add_argument(
        "--copy-db",
        action="store_true",
        help="Copy local database before syncing to avoid lock issues",
    )
    parser.add_argument(
        "--verify", action="store_true", help="Verify data after sync (counts only)"
    )

    args = parser.parse_args()

    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Get local DB path
    local_db_path = args.local_db
    if not local_db_path:
        # Try to get from environment or use default
        local_db_path = os.environ.get("DEWEY_DB_PATH")
        if not local_db_path:
            default_path = os.path.join(
                os.path.expanduser("~"), "dewey", "dewey.duckdb"
            )
            if os.path.exists(default_path):
                local_db_path = default_path
            else:
                # Look in current directory
                current_dir = os.getcwd()
                default_path = os.path.join(current_dir, "dewey.duckdb")
                if os.path.exists(default_path):
                    local_db_path = default_path

    # Get MotherDuck DB name
    md_db_name = args.md_db
    if not md_db_name:
        md_db_name = os.environ.get("DEWEY_MD_DB", "dewey")

    # Get token
    token = args.token
    if not token:
        token = os.environ.get("MOTHERDUCK_TOKEN")
        if not token:
            logger.error(
                "MotherDuck token not provided. Set MOTHERDUCK_TOKEN environment variable or use --token."
            )
            return 1

    # Check local db path
    if not local_db_path:
        logger.error("Local database path not provided and could not be inferred.")
        return 1

    # Report connection details
    logger.info(f"Local DB path: {local_db_path}")
    logger.info(f"MotherDuck DB: {md_db_name}")

    # Check file size
    if os.path.exists(local_db_path):
        size_bytes = os.path.getsize(local_db_path)
        size_gb = size_bytes / (1024 * 1024 * 1024)
        logger.info(f"Local database size: {size_gb:.2f} GB")
    else:
        logger.warning(
            f"Local database file {local_db_path} does not exist. It will be created."
        )

    # Create syncer
    syncer = DBSyncer(local_db_path, md_db_name, token)

    # Set batch size
    syncer.batch_size = args.batch_size

    # Set retry parameters
    syncer.retry_delay_base = args.retry_delay
    syncer.max_retries = args.max_retries

    # Connect to databases
    if not syncer.connect(use_copy=args.copy_db):
        logger.error("Failed to connect to databases. Exiting.")
        return 1

    try:
        # Get tables
        if args.tables:
            tables_to_sync = args.tables.split(",")
            logger.info(f"Will sync tables: {', '.join(tables_to_sync)}")
        else:
            # Sync all tables from MotherDuck to local
            logger.info("Getting list of tables from MotherDuck...")
            md_tables = syncer.list_tables(syncer.md_conn)

            # Get tables from local
            logger.info("Getting list of tables from local...")
            local_tables = syncer.list_tables(syncer.local_conn)

            # Combine unique tables from both sources
            tables_to_sync = list(set(md_tables + local_tables))

            # Sort for consistent order
            tables_to_sync.sort()

            logger.info(f"Found {len(tables_to_sync)} tables to sync")

        # Apply exclusions
        if args.exclude:
            exclude_tables = args.exclude.split(",")
            tables_to_sync = [t for t in tables_to_sync if t not in exclude_tables]
            logger.info(f"Excluding tables: {', '.join(exclude_tables)}")

        total_tables = len(tables_to_sync)
        successful_tables = 0

        # Sync each table
        for idx, table_name in enumerate(tables_to_sync, 1):
            logger.info(f"Processing table {idx}/{total_tables}: {table_name}")

            try:
                # Sync from MotherDuck to local
                if args.sync_direction in ["md-to-local", "both"]:
                    incremental = args.incremental and not args.force_full

                    # Check if table exists in MotherDuck
                    if syncer.check_table_exists(table_name, syncer.md_conn):
                        logger.info(
                            f"Syncing {table_name} from MotherDuck to local (mode: {'incremental' if incremental else 'full'})"
                        )
                        if syncer.sync_table_from_md_to_local(table_name, incremental):
                            logger.info(
                                f"Successfully synced {table_name} from MotherDuck to local"
                            )
                        else:
                            logger.error(
                                f"Failed to sync {table_name} from MotherDuck to local"
                            )
                    else:
                        logger.warning(
                            f"Table {table_name} doesn't exist in MotherDuck, skipping md-to-local sync"
                        )

                # Sync schema from local to MotherDuck
                if args.sync_direction in ["local-to-md", "both"]:
                    # Check if table exists in local
                    if syncer.check_table_exists(table_name, syncer.local_conn):
                        # Get schemas
                        local_schema = syncer.get_table_schema(
                            table_name, syncer.local_conn
                        )

                        # Check if table exists in MotherDuck
                        if syncer.check_table_exists(table_name, syncer.md_conn):
                            # Get MotherDuck schema
                            md_schema = syncer.get_table_schema(
                                table_name, syncer.md_conn
                            )

                            # Sync schema changes
                            logger.info(
                                f"Syncing schema changes for {table_name} from local to MotherDuck"
                            )
                            if syncer.sync_schema_to_motherduck(
                                table_name, local_schema, md_schema
                            ):
                                logger.info(
                                    f"Successfully synced schema for {table_name}"
                                )
                            else:
                                logger.error(f"Failed to sync schema for {table_name}")
                        else:
                            # Create table in MotherDuck
                            logger.info(f"Creating table {table_name} in MotherDuck")
                            if syncer.create_table_in_motherduck(
                                table_name, local_schema
                            ):
                                logger.info(
                                    f"Successfully created table {table_name} in MotherDuck"
                                )
                            else:
                                logger.error(
                                    f"Failed to create table {table_name} in MotherDuck"
                                )
                    else:
                        logger.warning(
                            f"Table {table_name} doesn't exist locally, skipping local-to-md sync"
                        )

                # Verify data if requested
                if args.verify:
                    syncer.verify_table_data(table_name)

                successful_tables += 1

            except Exception as e:
                logger.error(f"Error processing table {table_name}: {e}")

        # Report summary
        logger.info(
            f"Sync completed. Successfully processed {successful_tables}/{total_tables} tables."
        )

        # If we created a copy of the database, offer to replace the original
        if args.copy_db and syncer.copy_created and os.path.exists(syncer.temp_db_path):
            logger.info(f"Temporary database copy created at {syncer.temp_db_path}")
            logger.info("The original database was not modified.")
            logger.info("To use the updated copy, run the following commands:")
            logger.info(f"cp {syncer.temp_db_path} {syncer.local_db_path}")

        return 0

    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Cleaning up...")
        return 130

    finally:
        # Close connections
        syncer.close()


if __name__ == "__main__":
    sys.exit(main())
