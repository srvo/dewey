"""Database utilities module.

This module provides utility functions and helpers for database operations.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from .connection import db_manager, DatabaseConnectionError

logger = logging.getLogger(__name__)

def generate_id(prefix: str = '') -> str:
    """Generate a unique ID for database records.
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        Unique ID string
    """
    return f"{prefix}{uuid.uuid4().hex}"

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

def parse_timestamp(timestamp: str) -> datetime:
    """Parse a timestamp from database format.
    
    Args:
        timestamp: Timestamp string to parse
        
    Returns:
        Parsed datetime object
    """
    return datetime.fromisoformat(timestamp)

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
    return value.replace('\x00', '').replace('\r', ' ').replace('\n', ' ')

def format_json(value: Any) -> str:
    """Format a value as JSON for database storage.
    
    Args:
        value: Value to format
        
    Returns:
        JSON string
    """
    if value is None:
        return 'null'
        
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
        
    return json.dumps(value)

def parse_json(value: str) -> Any:
    """Parse a JSON value from database storage.
    
    Args:
        value: JSON string to parse
        
    Returns:
        Parsed value
    """
    if not value or value == 'null':
        return None
        
    return json.loads(value)

def format_list(values: List[Any], separator: str = ',') -> str:
    """Format a list for database storage.
    
    Args:
        values: List of values to format
        separator: Separator character
        
    Returns:
        Formatted string
    """
    return separator.join(str(v) for v in values)

def parse_list(value: str, separator: str = ',') -> List[str]:
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

def format_bool(value: bool) -> int:
    """Format a boolean for database storage.
    
    Args:
        value: Boolean to format
        
    Returns:
        Integer (0 or 1)
    """
    return 1 if value else 0

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
        return value.lower() in ('1', 'true', 't', 'yes', 'y')
        
    return bool(value)

def format_enum(value: str, valid_values: List[str]) -> str:
    """Format an enum value for database storage.
    
    Args:
        value: Value to format
        valid_values: List of valid enum values
        
    Returns:
        Formatted string
    """
    value = str(value).upper()
    if value not in valid_values:
        raise ValueError(f"Invalid enum value: {value}")
    return value

def parse_enum(value: str, valid_values: List[str]) -> str:
    """Parse an enum value from database storage.
    
    Args:
        value: Value to parse
        valid_values: List of valid enum values
        
    Returns:
        Parsed enum value
    """
    value = str(value).upper()
    if value not in valid_values:
        raise ValueError(f"Invalid enum value: {value}")
    return value

def format_money(amount: Union[int, float]) -> int:
    """Format a money amount for database storage (in cents).
    
    Args:
        amount: Amount to format
        
    Returns:
        Amount in cents as integer
    """
    return int(float(amount) * 100)

def parse_money(cents: int) -> float:
    """Parse a money amount from database storage.
    
    Args:
        cents: Amount in cents
        
    Returns:
        Amount as float
    """
    return float(cents) / 100

def build_where_clause(conditions: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """Build a WHERE clause from conditions.
    
    Args:
        conditions: Dictionary of column names and values
        
    Returns:
        Tuple of (where_clause, parameters)
    """
    if not conditions:
        return "", []
        
    clauses = []
    params = []
    
    for col, val in conditions.items():
        if val is None:
            clauses.append(f"{col} IS NULL")
        elif isinstance(val, (list, tuple)):
            placeholders = ', '.join(['?' for _ in val])
            clauses.append(f"{col} IN ({placeholders})")
            params.extend(val)
        else:
            clauses.append(f"{col} = ?")
            params.append(val)
            
    return "WHERE " + " AND ".join(clauses), params

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
        if col.startswith('-'):
            clauses.append(f"{col[1:]} DESC")
        else:
            clauses.append(f"{col} ASC")
            
    return "ORDER BY " + ", ".join(clauses)

def build_limit_clause(limit: Optional[int] = None,
                      offset: Optional[int] = None) -> str:
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

def build_select_query(table_name: str,
                      columns: Optional[List[str]] = None,
                      conditions: Optional[Dict[str, Any]] = None,
                      order_by: Optional[Union[str, List[str]]] = None,
                      limit: Optional[int] = None,
                      offset: Optional[int] = None) -> Tuple[str, List[Any]]:
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
    where_clause, params = build_where_clause(conditions or {})
    order_clause = build_order_clause(order_by)
    limit_clause = build_limit_clause(limit, offset)
    
    # Combine query
    query = f"""
        SELECT {col_list}
        FROM {table_name}
        {where_clause}
        {order_clause}
        {limit_clause}
    """
    
    return query.strip(), params

def build_insert_query(table_name: str,
                      data: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """Build an INSERT query.
    
    Args:
        table_name: Name of the table to insert into
        data: Dictionary of column names and values
        
    Returns:
        Tuple of (query, parameters)
    """
    columns = list(data.keys())
    placeholders = ', '.join(['?' for _ in columns])
    values = list(data.values())
    
    query = f"""
        INSERT INTO {table_name}
        ({', '.join(columns)})
        VALUES ({placeholders})
    """
    
    return query.strip(), values

def build_update_query(table_name: str,
                      data: Dict[str, Any],
                      conditions: Dict[str, Any]) -> Tuple[str, List[Any]]:
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
    where_clause, where_params = build_where_clause(conditions)
    
    query = f"""
        UPDATE {table_name}
        SET {set_clause}
        {where_clause}
    """
    
    return query.strip(), set_params + where_params

def build_delete_query(table_name: str,
                      conditions: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """Build a DELETE query.
    
    Args:
        table_name: Name of the table to delete from
        conditions: Dictionary of conditions
        
    Returns:
        Tuple of (query, parameters)
    """
    where_clause, params = build_where_clause(conditions)
    
    query = f"""
        DELETE FROM {table_name}
        {where_clause}
    """
    
    return query.strip(), params

def execute_batch(queries: List[Tuple[str, List[Any]]],
                 local_only: bool = False) -> None:
    """Execute multiple queries in a transaction.
    
    Args:
        queries: List of (query, parameters) tuples
        local_only: Whether to only execute on local database
    """
    try:
        # Start transaction
        db_manager.execute_query("BEGIN TRANSACTION",
                               for_write=True, local_only=local_only)
        
        try:
            # Execute queries
            for query, params in queries:
                db_manager.execute_query(query, params,
                                      for_write=True, local_only=local_only)
                
            # Commit transaction
            db_manager.execute_query("COMMIT",
                                   for_write=True, local_only=local_only)
                
        except Exception as e:
            # Rollback transaction
            db_manager.execute_query("ROLLBACK",
                                   for_write=True, local_only=local_only)
            raise e
            
    except Exception as e:
        error_msg = f"Failed to execute batch: {e}"
        logger.error(error_msg)
        raise DatabaseConnectionError(error_msg) 