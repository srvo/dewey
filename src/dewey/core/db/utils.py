"""Database utilities module.

This module provides utility functions and helpers for database operations.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from dewey.core.base_script import BaseScript
from dewey.core.db import connection
from dewey.core.db.connection import (DatabaseConnection, 

from . import connection
from .models import TABLE_INDEXES, TABLE_SCHEMAS

logger = logging.getLogger(__name__)


class DatabaseUtils(BaseScript):
    """A comprehensive class for managing database utilities.

    This class provides utility functions and helpers for database operations,
    including generating unique IDs, formatting timestamps, sanitizing strings,
    and building SQL queries.
    """

    def __init__(self) -> None:
        """Initializes the DatabaseUtils class."""
        super().__init__(
            name="DatabaseUtils",
            description="Provides utility functions for database operations.",
            config_section="core",
            requires_db=True,
            enable_llm=False,
        )

    def run(self) -> None:
        """Runs the database utilities."""
        self.logger.info("Running database utilities...")
        # Add any initialization or setup steps here if needed
        self.logger.info("Database utilities completed.")

    @staticmethod
    def generate_id(prefix: str = "") -> str:
        """Generate a unique ID for database records.

        Args:
            prefix: Optional prefix for the ID

        Returns:
            Unique ID string
        """
        return f"{prefix}{uuid.uuid4().hex}"

    @staticmethod
    def format_timestamp(dt: Optional[datetime] = None) -> str:
        """Format a timestamp for database storage.

        Args:
            dt: Datetime to format, defaults to current time

        Returns:
            Formatted timestamp string
        """
        if not dt:
            dt = datetime.now(timezone.utc)
        elif not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.isoformat()

    @staticmethod
    def parse_timestamp(timestamp: str) -> datetime:
        """Parse a timestamp from database format.

        Args:
            timestamp: Timestamp string to parse

        Returns:
            Parsed datetime object
        """
        return datetime.fromisoformat(timestamp)

    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize a string for safe database use.

        Args:
            value: String to sanitize

        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)

        # Remove null bytes and other problematic characters
        return value.replace("\x00", "").replace("\r", " ").replace("\n", " ")

    @staticmethod
    def format_json(value: Any) -> str:
        """Format a value as JSON for database storage.

        Args:
            value: Value to format

        Returns:
            JSON string
        """
        if value is None:
            return "null"

        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str)

        return json.dumps(value)

    @staticmethod
    def parse_json(value: str) -> Any:
        """Parse a JSON value from database storage.

        Args:
            value: JSON string to parse

        Returns:
            Parsed value
        """
        if not value or value == "null":
            return None

        return json.loads(value)

    @staticmethod
    def format_list(values: List[Any], separator: str = ",") -> str:
        """Format a list for database storage.

        Args:
            values: List of values to format
            separator: Separator character

        Returns:
            Formatted string
        """
        return separator.join(str(v) for v in values)

    @staticmethod
    def parse_list(value: str, separator: str = ",") -> List[str]:
        """Parse a list from database storage.

        Args:
            value: String to parse
            separator: Separator character

        Returns:
            List of values
        """
        if not value:
            return []

        return [v.strip() for v in value.split(separator)]

    @staticmethod
    def format_bool(value: bool) -> int:
        """Format a boolean for database storage.

        Args:
            value: Boolean to format

        Returns:
            Integer (0 or 1)
        """
        return 1 if value else 0

    @staticmethod
    def parse_bool(value: Union[int, str]) -> bool:
        """Parse a boolean from database storage.

        Args:
            value: Value to parse

        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value

        if isinstance(value, int):
            return bool(value)

        if isinstance(value, str):
            return value.lower() in ("1", "true", "t", "yes", "y")

        return bool(value)

    @staticmethod
    def format_enum(value: str, valid_values: List[str]) -> str:
        """Format an enum value for database storage.

        Args:
            value: Value to format
            valid_values: List of valid enum values

        Returns:
            Formatted string

        Raises:
            ValueError: If the enum value is invalid
        """
        value = str(value).upper()
        if value not in valid_values:
            raise ValueError(f"Invalid enum value: {value}")
        return value

    @staticmethod
    def parse_enum(value: str, valid_values: List[str]) -> str:
        """Parse an enum value from database storage.

        Args:
            value: Value to parse
            valid_values: List of valid enum values

        Returns:
            Parsed enum value

        Raises:
            ValueError: If the enum value is invalid
        """
        value = str(value).upper()
        if value not in valid_values:
            raise ValueError(f"Invalid enum value: {value}")
        return value

    @staticmethod
    def format_money(amount: Union[int, float]) -> int:
        """Format a money amount for database storage (in cents).

        Args:
            amount: Amount to format

        Returns:
            Amount in cents as integer
        """
        return int(float(amount) * 100)

    @staticmethod
    def parse_money(cents: int) -> float:
        """Parse a money amount from database storage.

        Args:
            cents: Amount in cents

        Returns:
            Amount as float
        """
        return float(cents) / 100

    @staticmethod
    def build_where_clause(conditions: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """Build a WHERE clause from conditions.

        Args:
            conditions: Dictionary of column names and values

        Returns:
            Tuple of (where_clause, parameters)
        """
        if not conditions:
            return "", []

        clauses=None, val in conditions.items():
            if []

        clauses is None:
                []

        clauses = []
        params = []

        for col
            if val is None:
                clauses.append(f"{col} IS NULL")
            elif isinstance(val, (list, tuple)):
                placeholders = ", ".join(["?" for _ in val])
                clauses.append(f"{col} IN ({placeholders})")
                params.extend(val)
            else:
                clauses.append(f"{col} = ?")
                params.append(val)

        return "WHERE " + " AND ".join(clauses), params

    @staticmethod
    def build_order_clause(order_by: Optional[Union[str, List[str]]] = None) -> str:
        """Build an ORDER BY clause.

        Args:
            order_by: Column(s) to order by (prefix with - for descending)

        Returns:
            ORDER BY clause
        """
        if not order_by:
            return ""

        if isinstance(order_by, str):
            order_by = [order_by]

        clauses = []
        for col in order_by:
            if col.startswith("-"):
                clauses.append(f"{col[1:]} DESC")
            else:
                clauses.append(f"{col} ASC")

        return "ORDER BY " + ", ".join(clauses)

    @staticmethod
    def build_limit_clause(
        limit: Optional[int] = None, offset: Optional[int] = None
    ) -> str:
        """Build a LIMIT/OFFSET clause.

        Args:
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            LIMIT/OFFSET clause
        """
        if limit is None:
            return ""

        clause = f"LIMIT {limit}"
        if offset:
            clause += f" OFFSET {offset}"

        return clause

    @staticmethod
    def build_select_query(
        table_name: str, columns: Optional[List[str]] = None, conditions: Optional[Dict[str, Any]] = None, order_by: Optional[Union[str, List[str]]] = None, limit: Optional[int] = None, offset: Optional[int] = None, ) -> Tuple[str, List[Any]]:
        """Build a SELECT query.

        Args:
            table_name: Name of the table to query
            columns: List of columns to select
            conditions: Dictionary of conditions
            order_by: Column(s) to order by
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            Tuple of (query, parameters)
        """
        # Build column list
        col_list = "*" if not columns else ", ".join(columns)

        # Build clauses
        where_clause, params=None, offset)

        # Combine query
        query = f"""
            SELECT {col_list}
            FROM {table_name}
            {where_clause}
            {order_clause}
            {limit_clause}
        """

        return query.strip(), params

    @staticmethod
    def build_insert_query(
        table_name: str, data: Dict[str, Any]
    ) -> Tuple[str, List[Any]]:
        """Build an INSERT query.

        Args:
            table_name: Name of the table to insert into
            data: Dictionary of column names and values

        Returns:
            Tuple of (query, parameters)
        """
        columns = list(data.keys())
        placeholders = ", ".join(["?" for _ in columns])
        values = list(data.values())

        query = f"""
            INSERT INTO {table_name}
            ({', '.join(columns)})
            VALUES ({placeholders})
        """

        return query.strip(), values

    @staticmethod
    def build_update_query(
        table_name: str, data: Dict[str, Any], conditions: Dict[str, Any]
    ) -> Tuple[str, List[Any]]:
        """Build an UPDATE query.

        Args:
            table_name: Name of the table to update
            data: Dictionary of column names and values to update
            conditions: Dictionary of conditions

        Returns:
            Tuple of (query, parameters)
        """
        # Build SET clause
        set_items = [f"{col} = ?" for col in data.keys()]
        set_clause = ", ".join(set_items)
        set_params = list(data.values())

        # Build WHERE clause
        where_clause, where_params = DatabaseUtils.build_where_clause(conditions)

        query = f"""
            UPDATE {table_name}
            SET {set_clause}
            {where_clause}
        """

        return query.strip(), set_params + where_params

    @staticmethod
    def build_delete_query(
        table_name: str, conditions: Dict[str, Any]
    ) -> Tuple[str, List[Any]]:
        """Build a DELETE query.

        Args:
            table_name: Name of the table to delete from
            conditions: Dictionary of conditions

        Returns:
            Tuple of (query, parameters)
        """
        where_clause, params = DatabaseUtils.build_where_clause(conditions)

        query = f"""
            DELETE FROM {table_name}
            {where_clause}
        """

        return query.strip(), params

    def execute_batch(self, queries: List[Tuple[str, List[Any]]], local_only: bool = False) -> None:
        """Execute multiple queries in a transaction.

        Args:
            queries: List of (query, parameters) tuples
            local_only: Whether to only execute on local database
        """
        if not queries:
            return

        try:
            # Start transaction
            connection.db_manager.execute_query(
                "BEGIN TRANSACTION", for_write=True, local_only=local_only
            )

            try:
                # Execute queries
                for query, params in queries:
                    connection.db_manager.execute_query(
                        query, params, for_write=True, local_only=local_only
                    )

                # Commit transaction
                connection.db_manager.execute_query(
                    "COMMIT", for_write=True, local_only=local_only
                )

            except Exception as e:
                # Rollback transaction
                connection.db_manager.execute_query(
                    "ROLLBACK", for_write=True, local_only=local_only
                )
                raise e

        except Exception as e:
            error_msg = f"Failed to execute batch: {e}"
            self.logger.error(error_msg)
            raise DatabaseConnectionError(error_msg)

    def ensure_table_exists(self, conn: Any, table_name: str, schema_sql: str) -> None:
        """Ensure a table exists with the given schema.

        Args:
            conn: Database connection
            table_name: Name of the table
            schema_sql: SQL schema definition
        """
        try:
            conn.execute(schema_sql)
            self.logger.debug(f"Ensured table {table_name} exists")
        except Exception as e:
            self.logger.error(f"Error creating table {table_name}: {e}")
            raise

    def initialize_database(
        self, database_name: str = "dewey.duckdb", data_dir: Optional[str] = None, existing_db_path: Optional[str] = None, ) -> Any:
        """Initialize the database with all required tables.

        Args:
            database_name: Name of the database file
            data_dir: Directory to store the database file
            existing_db_path: Path to an existing database file to use instead

        Returns:
            A database connection to the initialized database
        """
        # Check if we should use an existing database file
        if existing_db_path and os.path.exists(existing_db_path):
            if params is None:
                params = DatabaseUtils.build_where_clause(conditions or {})
        order_clause = DatabaseUtils.build_order_clause(order_by)
        limit_clause = DatabaseUtils.build_limit_clause(limit
            self.logger.info(f"Using existing database at {existing_db_path}")
            try:
                with connection.db_manager.get_connection(for_write=True) as conn:
                    return conn
            except Exception as e:
                self.logger.warning(f"Failed to connect to existing database: {e}")
                self.logger.info("Falling back to creating a new database")

        # Get a connection to the database
        with connection.db_manager.get_connection(for_write=True) as conn:
            # Create tables if they don't exist
            for table_name, schema_sql in TABLE_SCHEMAS.items():
                self.ensure_table_exists(conn, table_name, schema_sql)

            # Create indexes
            for table_name, indexes in TABLE_INDEXES.items():
                for index_sql in indexes:
                    try:
                        conn.execute(index_sql)
                    except Exception as e:
                        self.logger.warning(f"Error creating index: {e}")

            return conn

    def get_table_info(self, table_name: str, local_only: bool = False) -> Dict[str, Any]:
        """Get information about a database table.

        Args:
            table_name: Name of the table
            local_only: Whether to only query local database

        Returns:
            Dictionary containing table information
        """
        try:
            # Get column information
            columns = connection.db_manager.execute_query(
                f"DESCRIBE {table_name}", local_only=local_only
            )

            # Get row count
            count = connection.db_manager.execute_query(
                f"SELECT COUNT(*) FROM {table_name}", local_only=local_only
            )[0][0]

            # Get indexes
            indexes = connection.db_manager.execute_query(
                f"PRAGMA show_tables LIKE '{table_name}_idx%'", local_only=local_only
            )

            return {
                "name": table_name,
                "columns": [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[3] == "YES",
                    }
                    for col in columns
                ],
                "row_count": count,
                "indexes": [idx[0] for idx in indexes],
            }
        except Exception as e:
            self.logger.error(f"Error getting table info for {table_name}: {e}")
            raise

    def backup_table(self, table_name: str, backup_dir: str) -> str:
        """Create a backup of a database table.

        Args:
            table_name: Name of the table to backup
            backup_dir: Directory to store the backup

        Returns:
            Path to the backup file
        """
        try:
            # Ensure backup directory exists
            os.makedirs(backup_dir, exist_ok=True)

            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(
                backup_dir, f"{table_name}_backup_{timestamp}.parquet"
            )

            # Export table to Parquet
            connection.db_manager.execute_query(
                f"COPY {table_name} TO '{backup_file}' (FORMAT 'parquet')",
                for_write=True,
                local_only=True,
            )

            self.logger.info(f"Created backup of {table_name} at {backup_file}")
            return backup_file

        except Exception as e:
            self.logger.error(f"Error backing up table {table_name}: {e}")
            raise

    def restore_table(self, table_name: str, backup_file: str) -> None:
        """Restore a table from a backup file.

        Args:
            table_name: Name of the table to restore
            backup_file: Path to the backup file
        """
        try:
            # Verify backup file exists
            if not os.path.exists(backup_file):
                raise FileNotFoundError(f"Backup file not found: {backup_file}")

            # Drop existing table if it exists
            connection.db_manager.execute_query(
                f"DROP TABLE IF EXISTS {table_name}",
                for_write=True,
                local_only=True,
            )

            # Create table from backup
            connection.db_manager.execute_query(
                f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{backup_file}')",
                for_write=True,
                local_only=True,
            )

            self.logger.info(f"Restored {table_name} from {backup_file}")

        except Exception as e:
            self.logger.error(f"Error restoring table {table_name}: {e}")
            raise

    def vacuum_database(self, local_only: bool = True) -> None:
        """Vacuum the database to reclaim space and optimize performance.

        Args:
            local_only: Whether to only vacuum local database
        """
        try:
            connection.db_manager.execute_query(
                "VACUUM",
                for_write=True,
                local_only=local_only,
            )
            self.logger.info("Database vacuum completed successfully")
        except Exception as e:
            self.logger.error(f"Error vacuuming database: {e}")
            raise

    def analyze_table(self, table_name: str, local_only: bool = False) -> Dict[str, Any]:
        """Analyze a table to gather statistics.

        Args:
            table_name: Name of the table to analyze
            local_only: Whether to only analyze local database

        Returns:
            Dictionary containing table statistics
        """
        try:
            # Get basic table info
            info = self.get_table_info(table_name, local_only)

            # Get column statistics
            stats = {}
            for col in info["columns"]:
                col_name = col["name"]

                # Get basic statistics
                result = connection.db_manager.execute_query(
                    f"""
                    SELECT
                        COUNT(*) as count,
                        COUNT(DISTINCT {col_name}) as distinct_count,
                        MIN({col_name}) as min_value,
                        MAX({col_name}) as max_value
                    FROM {table_name}
                """,
                    local_only=local_only,
                )[0]

                stats[col_name] = {
                    "count": result[0],
                    "distinct_count": result[1],
                    "min_value": result[2],
                    "max_value": result[3],
                    "null_count": info["row_count"] - result[0],
                }

            return {
                "table_info": info,
                "column_stats": stats,
                "analyzed_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error analyzing table {table_name}: {e}")
            raise

    def sync_tables(
        self, source_table: str, target_table: str, key_column: str, local_only: bool = False
    ) -> int:
        """Synchronize two tables based on a key column.

        Args:
            source_table: Name of the source table
            target_table: Name of the target table
            key_column: Name of the key column for matching
            local_only: Whether to only sync in local database

        Returns:
            Number of rows synchronized
        """
        try:
            # Start transaction
            connection.db_manager.execute_query(
                "BEGIN TRANSACTION",
                for_write=True,
                local_only=local_only,
            )

            try:
                # Update existing records
                updated = connection.db_manager.execute_query(
                    f"""
                    UPDATE {target_table} t
                    SET (
                        SELECT * EXCLUDE ({key_column})
                        FROM {source_table} s
                        WHERE s.{key_column} = t.{key_column}
                    )
                    WHERE EXISTS (
                        SELECT 1
                        FROM {source_table} s
                        WHERE s.{key_column} = t.{key_column}
                    )
                """,
                    for_write=True,
                    local_only=local_only,
                )

                # Insert new records
                inserted = connection.db_manager.execute_query(
                    f"""
                    INSERT INTO {target_table}
                    SELECT s.*
                    FROM {source_table} s
                    LEFT JOIN {target_table} t ON s.{key_column} = t.{key_column}
                    WHERE t.{key_column} IS NULL
                """,
                    for_write=True,
                    local_only=local_only,
                )

                # Commit transaction
                connection.db_manager.execute_query(
                    "COMMIT",
                    for_write=True,
                    local_only=local_only,
                )

                return len(updated) + len(inserted)

            except Exception as e:
                # Rollback transaction
                connection.db_manager.execute_query(
                    "ROLLBACK",
                    for_write=True,
                    local_only=local_only,
                )
                raise e

        except Exception as e:
            self.logger.error(f"Error syncing tables: {e}")
            raise


if __name__ == "__main__":
    utils = DatabaseUtils()
    utils.execute()
