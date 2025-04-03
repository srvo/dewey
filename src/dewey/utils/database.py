"""
Database utility functions.

This module provides utility functions for database operations.
"""

from typing import Any, Dict, List, Optional, Tuple, Union

import duckdb


def execute_query(conn: duckdb.DuckDBPyConnection, query: str, params: Optional[List[Any]] = None) -> None:
    """
    Execute a query on the database connection.
    
    Args:
        conn: The database connection.
        query: The query to execute.
        params: The parameters for the query.
    """
    if params:
        conn.execute(query, params)
    else:
        conn.execute(query)


def fetch_one(conn: duckdb.DuckDBPyConnection, query: str, params: Optional[List[Any]] = None) -> Optional[Tuple[Any, ...]]:
    """
    Fetch a single result from the database.
    
    Args:
        conn: The database connection.
        query: The query to execute.
        params: The parameters for the query.
        
    Returns:
        A tuple containing the result, or None if no result is found.
    """
    if params:
        result = conn.execute(query, params).fetchone()
    else:
        result = conn.execute(query).fetchone()
    return result


def fetch_all(conn: duckdb.DuckDBPyConnection, query: str, params: Optional[List[Any]] = None) -> List[Tuple[Any, ...]]:
    """
    Fetch all results from the database.
    
    Args:
        conn: The database connection.
        query: The query to execute.
        params: The parameters for the query.
        
    Returns:
        A list of tuples containing the results.
    """
    if params:
        results = conn.execute(query, params).fetchall()
    else:
        results = conn.execute(query).fetchall()
    return results


def create_table_if_not_exists(conn: duckdb.DuckDBPyConnection, table_name: str, columns_definition: str) -> None:
    """
    Create a table if it doesn't exist.
    
    Args:
        conn: The database connection.
        table_name: The name of the table.
        columns_definition: The column definitions for the table.
    """
    query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_definition})"
    execute_query(conn, query)


def table_exists(conn: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    """
    Check if a table exists in the database.
    
    Args:
        conn: The database connection.
        table_name: The name of the table.
        
    Returns:
        True if the table exists, False otherwise.
    """
    query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    result = fetch_one(conn, query)
    return result is not None


def insert_row(conn: duckdb.DuckDBPyConnection, table_name: str, data: Dict[str, Any]) -> None:
    """
    Insert a row into a table.
    
    Args:
        conn: The database connection.
        table_name: The name of the table.
        data: A dictionary mapping column names to values.
    """
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    execute_query(conn, query, list(data.values()))


def update_row(conn: duckdb.DuckDBPyConnection, table_name: str, data: Dict[str, Any], condition: str, condition_params: List[Any]) -> None:
    """
    Update a row in a table.
    
    Args:
        conn: The database connection.
        table_name: The name of the table.
        data: A dictionary mapping column names to values.
        condition: The condition for the update (e.g., "id = ?").
        condition_params: The parameters for the condition.
    """
    set_clause = ", ".join([f"{column} = ?" for column in data.keys()])
    query = f"UPDATE {table_name} SET {set_clause} WHERE {condition}"
    execute_query(conn, query, list(data.values()) + condition_params) 