"""Database operations module.

This module provides high-level database operations and transaction management
for both local DuckDB and MotherDuck cloud databases.
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from .connection import db_manager
from .errors import DatabaseError, handle_error
from .sync import sync_manager

logger = logging.getLogger(__name__)

@contextmanager
def transaction(local_only: bool = False):
    """Context manager for database transactions.
    
    Args:
        local_only: Whether to only use local database
        
    Yields:
        None
    """
    try:
        db_manager.execute_query("BEGIN TRANSACTION", 
                               for_write=True, local_only=local_only)
        yield
        db_manager.execute_query("COMMIT", 
                               for_write=True, local_only=local_only)
    except Exception as e:
        db_manager.execute_query("ROLLBACK", 
                               for_write=True, local_only=local_only)
        raise

def record_change(table_name: str, operation: str, record_id: str, 
                 details: Optional[Dict] = None, user_id: Optional[str] = None) -> None:
    """Record a change in the change_log table.
    
    Args:
        table_name: Name of the table being modified
        operation: Type of operation (INSERT, UPDATE, DELETE)
        record_id: ID of the record being modified
        details: Additional details about the change
        user_id: ID of the user making the change
    """
    try:
        with transaction(local_only=True):
            db_manager.execute_query("""
                INSERT INTO change_log (
                    table_name, operation, record_id, 
                    changed_at, user_id, details
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            """, [table_name, operation, record_id, user_id, details],
            for_write=True, local_only=True)
            
            # Queue for sync if offline
            if not db_manager.is_online():
                sync_manager.queue_offline_change({
                    'table_name': table_name,
                    'operation': operation,
                    'record_id': record_id,
                    'details': details,
                    'user_id': user_id
                })
    except Exception as e:
        error_id = handle_error(e, {
            'table_name': table_name,
            'operation': operation,
            'record_id': record_id
        })
        raise DatabaseError(f"Failed to record change (Error ID: {error_id})")

def insert_record(table_name: str, data: Dict[str, Any], 
                 user_id: Optional[str] = None) -> str:
    """Insert a new record into a table.
    
    Args:
        table_name: Name of the table to insert into
        data: Dictionary of column names and values
        user_id: ID of the user making the change
        
    Returns:
        ID of the inserted record
    """
    try:
        with transaction(local_only=True):
            # Insert record locally
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            values = list(data.values())
            
            db_manager.execute_query(f"""
                INSERT INTO {table_name} ({columns})
                VALUES ({placeholders})
            """, values, for_write=True, local_only=True)
            
            # Record change
            record_id = data.get('id') or str(values[0])
            record_change(table_name, 'INSERT', record_id, data, user_id)
            
            logger.info(f"Inserted record {record_id} into {table_name}")
            return record_id
            
    except Exception as e:
        error_id = handle_error(e, {
            'table_name': table_name,
            'operation': 'INSERT'
        })
        raise DatabaseError(f"Failed to insert record (Error ID: {error_id})")

def update_record(table_name: str, record_id: str, data: Dict[str, Any],
                 user_id: Optional[str] = None) -> None:
    """Update an existing record in a table.
    
    Args:
        table_name: Name of the table to update
        record_id: ID of the record to update
        data: Dictionary of column names and values to update
        user_id: ID of the user making the change
    """
    try:
        with transaction(local_only=True):
            # Update record locally
            set_clause = ', '.join([f"{k} = ?" for k in data])
            values = list(data.values()) + [record_id]
            
            result = db_manager.execute_query(f"""
                UPDATE {table_name}
                SET {set_clause}
                WHERE id = ?
            """, values, for_write=True, local_only=True)
            
            if not result or not result[0][0]:
                raise DatabaseError(f"Record {record_id} not found in {table_name}")
            
            # Record change
            record_change(table_name, 'UPDATE', record_id, data, user_id)
            
            logger.info(f"Updated record {record_id} in {table_name}")
            
    except Exception as e:
        error_id = handle_error(e, {
            'table_name': table_name,
            'record_id': record_id,
            'operation': 'UPDATE'
        })
        raise DatabaseError(f"Failed to update record (Error ID: {error_id})")

def delete_record(table_name: str, record_id: str,
                 user_id: Optional[str] = None) -> None:
    """Delete a record from a table.
    
    Args:
        table_name: Name of the table to delete from
        record_id: ID of the record to delete
        user_id: ID of the user making the change
    """
    try:
        with transaction(local_only=True):
            # Get record data before deletion
            result = db_manager.execute_query(f"""
                SELECT * FROM {table_name}
                WHERE id = ?
            """, [record_id], local_only=True)
            
            if not result:
                raise DatabaseError(f"Record {record_id} not found in {table_name}")
                
            # Delete record locally
            db_manager.execute_query(f"""
                DELETE FROM {table_name}
                WHERE id = ?
            """, [record_id], for_write=True, local_only=True)
            
            # Record change
            old_data = dict(zip(['id'], result[0]))
            record_change(table_name, 'DELETE', record_id, 
                        {'old_data': old_data}, user_id)
            
            logger.info(f"Deleted record {record_id} from {table_name}")
            
    except Exception as e:
        error_id = handle_error(e, {
            'table_name': table_name,
            'record_id': record_id,
            'operation': 'DELETE'
        })
        raise DatabaseError(f"Failed to delete record (Error ID: {error_id})")

def get_record(table_name: str, record_id: str) -> Optional[Dict]:
    """Get a single record from a table.
    
    Args:
        table_name: Name of the table to query
        record_id: ID of the record to get
        
    Returns:
        Record as dictionary or None if not found
    """
    try:
        # Try MotherDuck first if online
        local_only = not db_manager.is_online()
        
        result = db_manager.execute_query(f"""
            SELECT * FROM {table_name}
            WHERE id = ?
        """, [record_id], local_only=local_only)
        
        if not result:
            return None
            
        # Get column names from table schema
        schema = db_manager.execute_query(f"DESCRIBE {table_name}", local_only=local_only)
        columns = [col[0] for col in schema]
        
        return dict(zip(columns, result[0]))
        
    except Exception as e:
        error_id = handle_error(e, {
            'table_name': table_name,
            'record_id': record_id,
            'operation': 'SELECT'
        })
        raise DatabaseError(f"Failed to get record (Error ID: {error_id})")

def query_records(table_name: str, conditions: Optional[Dict] = None,
                 order_by: Optional[str] = None, limit: Optional[int] = None) -> List[Dict]:
    """Query records from a table with optional filtering.
    
    Args:
        table_name: Name of the table to query
        conditions: Dictionary of column names and values to filter by
        order_by: Column name to order by (prefix with - for descending)
        limit: Maximum number of records to return
        
    Returns:
        List of records as dictionaries
    """
    try:
        # Try MotherDuck first if online
        local_only = not db_manager.is_online()
        
        # Build WHERE clause
        where_clause = ""
        values = []
        
        if conditions:
            clauses = []
            for col, val in conditions.items():
                if isinstance(val, (list, tuple)):
                    placeholders = ', '.join(['?' for _ in val])
                    clauses.append(f"{col} IN ({placeholders})")
                    values.extend(val)
                else:
                    clauses.append(f"{col} = ?")
                    values.append(val)
            where_clause = "WHERE " + " AND ".join(clauses)
            
        # Build ORDER BY clause
        order_clause = ""
        if order_by:
            if order_by.startswith('-'):
                order_clause = f"ORDER BY {order_by[1:]} DESC"
            else:
                order_clause = f"ORDER BY {order_by}"
                
        # Build LIMIT clause
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        # Execute query
        query = f"""
            SELECT * FROM {table_name}
            {where_clause}
            {order_clause}
            {limit_clause}
        """
        
        result = db_manager.execute_query(query, values, local_only=local_only)
        
        # Get column names from table schema
        schema = db_manager.execute_query(f"DESCRIBE {table_name}", local_only=local_only)
        columns = [col[0] for col in schema]
        
        # Convert results to dictionaries
        return [dict(zip(columns, row)) for row in result]
        
    except Exception as e:
        error_id = handle_error(e, {
            'table_name': table_name,
            'conditions': conditions,
            'operation': 'SELECT'
        })
        raise DatabaseError(f"Failed to query records (Error ID: {error_id})")

def bulk_insert(table_name: str, records: List[Dict],
               user_id: Optional[str] = None) -> List[str]:
    """Insert multiple records into a table.
    
    Args:
        table_name: Name of the table to insert into
        records: List of dictionaries containing record data
        user_id: ID of the user making the change
        
    Returns:
        List of inserted record IDs
    """
    try:
        with transaction(local_only=True):
            record_ids = []
            
            for data in records:
                # Insert record locally
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                values = list(data.values())
                
                db_manager.execute_query(f"""
                    INSERT INTO {table_name} ({columns})
                    VALUES ({placeholders})
                """, values, for_write=True, local_only=True)
                
                # Record change
                record_id = data.get('id') or str(values[0])
                record_ids.append(record_id)
                record_change(table_name, 'INSERT', record_id, data, user_id)
                
            logger.info(f"Inserted {len(records)} records into {table_name}")
            return record_ids
            
    except Exception as e:
        error_id = handle_error(e, {
            'table_name': table_name,
            'record_count': len(records),
            'operation': 'BULK_INSERT'
        })
        raise DatabaseError(f"Failed to bulk insert records (Error ID: {error_id})")

def execute_custom_query(query: str, params: Optional[List] = None,
                       for_write: bool = False) -> List[Tuple]:
    """Execute a custom SQL query.
    
    Args:
        query: SQL query to execute
        params: List of parameter values
        for_write: Whether the query modifies data
        
    Returns:
        List of result tuples
    """
    try:
        # Use local database for writes, try MotherDuck first for reads
        local_only = for_write or not db_manager.is_online()
        
        return db_manager.execute_query(query, params, for_write, local_only)
    except Exception as e:
        error_id = handle_error(e, {
            'query': query,
            'for_write': for_write
        })
        raise DatabaseError(f"Failed to execute custom query (Error ID: {error_id})") 