"""
Database utility functions for PostgreSQL.

This module provides utility functions for database operations using psycopg2
and a connection pool.
"""

import logging
from contextlib import contextmanager
from typing import Any

import psycopg2
import psycopg2.extras  # For dictionary cursor if needed later
import psycopg2.pool

# Assuming config.py is one level up and in a core.db package
from dewey.core.db.config import get_db_config

logger = logging.getLogger(__name__)

# Global connection pool variable
_connection_pool: psycopg2.pool.SimpleConnectionPool | None = None


def initialize_pool():
    """Initialize the PostgreSQL connection pool."""
    global _connection_pool
    if _connection_pool is None:
        try:
            config = get_db_config()
            # Construct DSN from config for the pool
            dsn = (
                f"dbname={config['pg_dbname']} "
                f"user={config['pg_user']} "
                f"password={config['pg_password'] or ''} "  # Handle potential None password
                f"host={config['pg_host']} "
                f"port={config['pg_port']}"
            )
            min_conn = 1
            max_conn = config.get("pool_size", 5)
            _connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=min_conn, maxconn=max_conn, dsn=dsn,
            )
            logger.info(
                f"Database connection pool initialized (min={min_conn}, max={max_conn})",
            )
        except (psycopg2.OperationalError, KeyError) as e:
            logger.error(f"Failed to initialize database pool: {e}")
            _connection_pool = None  # Ensure pool remains None on error
            raise  # Re-raise the exception to signal failure


def _get_pool() -> psycopg2.pool.SimpleConnectionPool:
    """Get the connection pool, initializing it if necessary."""
    if _connection_pool is None:
        initialize_pool()
    if _connection_pool is None:  # Check again after initialization attempt
        raise RuntimeError("Database connection pool is not available.")
    return _connection_pool


@contextmanager
def get_db_cursor(commit: bool = False):
    """
    Provide a database cursor from the connection pool.

    Handles connection acquisition, cursor creation, transaction commit/rollback,
    and connection release.

    Args:
    ----
        commit: If True, commit the transaction upon successful exit.
                If False, the block is treated as read-only (no commit/rollback needed
                unless an error occurs).

    Yields:
    ------
        psycopg2.extensions.cursor: The database cursor.

    Raises:
    ------
        RuntimeError: If the pool is not initialized.
        Exception: Propagates exceptions from database operations.

    """
    pool = _get_pool()
    conn = None
    cursor = None
    try:
        conn = pool.getconn()
        # Use DictCursor for easy row access by column name, if desired
        # cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor = conn.cursor()
        yield cursor
        if commit:
            conn.commit()
            logger.debug("Transaction committed.")
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Database error: {error}")
        if conn and commit:  # Only rollback if we intended to modify
            try:
                conn.rollback()
                logger.warning("Transaction rolled back due to error.")
            except psycopg2.Error as rb_error:
                logger.error(f"Error during rollback: {rb_error}")
        raise  # Re-raise the original error
    finally:
        if cursor:
            try:
                cursor.close()
            except psycopg2.Error as cur_err:
                logger.error(f"Error closing cursor: {cur_err}")
        if conn:
            try:
                pool.putconn(conn)
            except psycopg2.Error as pc_err:
                logger.error(f"Error returning connection to pool: {pc_err}")


def close_pool():
    """Close all connections in the pool."""
    global _connection_pool
    if _connection_pool:
        try:
            _connection_pool.closeall()
            logger.info("Database connection pool closed.")
            _connection_pool = None
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}")


# --- Modified Utility Functions ---


def execute_query(query: str, params: list[Any] | None = None) -> None:
    """
    Execute a query without fetching results (e.g., INSERT, UPDATE, DELETE).

    Args:
    ----
        query: The SQL query with %s placeholders.
        params: A list of parameters for the query.

    """
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(query, params or [])


def fetch_one(query: str, params: list[Any] | None = None) -> tuple[Any, ...] | None:
    """
    Fetch a single result row.

    Args:
    ----
        query: The SQL query with %s placeholders.
        params: A list of parameters for the query.

    Returns:
    -------
        A tuple containing the result row, or None if no result.

    """
    with get_db_cursor(commit=False) as cursor:  # Read-only
        cursor.execute(query, params or [])
        result = cursor.fetchone()
    return result


def fetch_all(query: str, params: list[Any] | None = None) -> list[tuple[Any, ...]]:
    """
    Fetch all result rows.

    Args:
    ----
        query: The SQL query with %s placeholders.
        params: A list of parameters for the query.

    Returns:
    -------
        A list of tuples, where each tuple is a result row.

    """
    with get_db_cursor(commit=False) as cursor:  # Read-only
        cursor.execute(query, params or [])
        results = cursor.fetchall()
    return results


def create_table_if_not_exists(table_name: str, columns_definition: str) -> None:
    """
    Create a table if it doesn't exist.

    Args:
    ----
        table_name: The name of the table.
        columns_definition: The column definitions for the table (PostgreSQL syntax).

    """
    # Ensure table_name is safe if it comes from variable input
    # Basic check; consider more robust validation if needed
    if not table_name.replace("_", "").isalnum():
        raise ValueError(f"Invalid table name: {table_name}")

    # columns_definition should also be validated or constructed safely
    query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_definition})"
    # Use execute_query which handles commit
    execute_query(query)


def table_exists(table_name: str, schema: str = "public") -> bool:
    """
    Check if a table exists in the specified schema.

    Args:
    ----
        table_name: The name of the table.
        schema: The schema name (default is 'public').

    Returns:
    -------
        True if the table exists, False otherwise.

    """
    query = (
        "SELECT EXISTS ("
        "   SELECT FROM information_schema.tables "
        "   WHERE table_schema = %s AND table_name = %s"
        ");"
    )
    result = fetch_one(query, [schema, table_name])
    return result[0] if result else False


def insert_row(table_name: str, data: dict[str, Any]) -> None:
    """
    Insert a row into a table.

    Args:
    ----
        table_name: The name of the table.
        data: A dictionary mapping column names to values.

    """
    if not data:
        return  # Nothing to insert

    columns = ", ".join(data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    # Use execute_query which handles commit
    execute_query(query, list(data.values()))


def update_row(
    table_name: str,
    data: dict[str, Any],
    condition: str,
    condition_params: list[Any] | None = None,
) -> None:
    """
    Update row(s) in a table based on a condition.

    Args:
    ----
        table_name: The name of the table.
        data: A dictionary mapping column names to new values.
        condition: The WHERE clause (e.g., "id = %s AND status = %s").
        condition_params: Parameters for the WHERE clause.

    """
    if not data:
        return  # Nothing to update

    set_clause = ", ".join([f"{column} = %s" for column in data])
    query = f"UPDATE {table_name} SET {set_clause}"
    params = list(data.values())

    if condition:
        query += f" WHERE {condition}"
        if condition_params:
            params.extend(condition_params)

    # Use execute_query which handles commit
    execute_query(query, params)


# Consider adding a function to fetch returning id after insert if needed
# def insert_row_returning_id(table_name: str, data: Dict[str, Any], id_column: str = 'id') -> Optional[Any]:
#    ...
#    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) RETURNING {id_column}"
#    with get_db_cursor(commit=True) as cursor:
#        cursor.execute(query, list(data.values()))
#        result = cursor.fetchone()
#    return result[0] if result else None
