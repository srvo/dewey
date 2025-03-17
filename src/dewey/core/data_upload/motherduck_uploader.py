#!/usr/bin/env python3
"""
MotherDuck Uploader

This script uploads data from the input directory to MotherDuck, organizing it
according to the core modules structure.
"""

import os
import json
import csv
import logging
import argparse
import duckdb
import glob
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("motherduck_uploader")

# Define core modules for organizing data
CORE_MODULES = {
    "crm": ["contacts", "emails", "calendar", "opportunities"],
    "research": ["analysis", "search", "keywords"],
    "accounting": ["transactions", "accounts", "portfolio"],
    "personal": ["audio", "notes"],
}

def get_motherduck_connection(database_name: str = "dewey") -> duckdb.DuckDBPyConnection:
    """
    Get a connection to MotherDuck.
    
    Args:
        database_name: Name of the database to connect to
        
    Returns:
        DuckDB connection to MotherDuck
    """
    # Check if MOTHERDUCK_TOKEN is set
    token = os.environ.get("MOTHERDUCK_TOKEN")
    if not token:
        logger.warning("MOTHERDUCK_TOKEN environment variable not set")
        logger.info("Using local DuckDB database instead")
        return duckdb.connect(f"{database_name}.duckdb")
    
    try:
        # First try to connect to MotherDuck without specifying a database
        # This allows us to create the database if it doesn't exist
        conn_str = f"md:?motherduck_token={token}"
        conn = duckdb.connect(conn_str)
        
        # Check if the database exists
        try:
            # Try to list databases to see if our target exists
            databases = conn.execute("SHOW DATABASES").fetchall()
            database_exists = any(db[0] == database_name for db in databases)
            
            if not database_exists:
                logger.info(f"Database '{database_name}' does not exist, creating it")
                conn.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
        except Exception as e:
            logger.warning(f"Error checking if database exists: {str(e)}")
            # Continue anyway, as we'll try to connect to the database directly
        
        # Now connect to the specific database
        conn_str = f"md:{database_name}?motherduck_token={token}"
        conn = duckdb.connect(conn_str)
        logger.info(f"Connected to MotherDuck database: {database_name}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to MotherDuck: {str(e)}")
        logger.info("Using local DuckDB database instead")
        return duckdb.connect(f"{database_name}.duckdb")

def determine_module(file_path: str) -> str:
    """
    Determine which module a file belongs to based on its path and content.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Module name (crm, research, accounting, personal)
    """
    file_path_lower = file_path.lower()
    file_name = os.path.basename(file_path_lower)
    
    # Check path for module indicators
    if any(keyword in file_path_lower for keyword in ["crm", "contact", "email", "calendar"]):
        return "crm"
    elif any(keyword in file_path_lower for keyword in ["research", "analysis", "search", "keyword"]):
        return "research"
    elif any(keyword in file_path_lower for keyword in ["account", "portfolio", "transaction", "financial"]):
        return "accounting"
    elif any(keyword in file_path_lower for keyword in ["audio", "note", "personal"]):
        return "personal"
    
    # Check filename for module indicators
    if any(keyword in file_name for keyword in ["contact", "email", "calendar", "opportunity"]):
        return "crm"
    elif any(keyword in file_name for keyword in ["research", "analysis", "search"]):
        return "research"
    elif any(keyword in file_name for keyword in ["account", "portfolio", "transaction"]):
        return "accounting"
    elif any(keyword in file_name for keyword in ["audio", "note", "personal"]):
        return "personal"
    
    # Default to "other" if no match
    return "other"

def determine_table_name(file_path: str, module: str) -> str:
    """
    Determine a suitable table name for the data based on file path and module.
    
    Args:
        file_path: Path to the file
        module: Module name
        
    Returns:
        Table name
    """
    file_name = os.path.basename(file_path)
    base_name = os.path.splitext(file_name)[0]
    
    # Clean up the base name to make it a valid table name
    base_name = base_name.lower()
    base_name = ''.join(c if c.isalnum() else '_' for c in base_name)
    base_name = base_name.strip('_')
    
    # Remove date patterns (common in filenames)
    import re
    base_name = re.sub(r'_\d{6}_\d{6}', '', base_name)
    base_name = re.sub(r'_\d{8}', '', base_name)
    base_name = re.sub(r'_\d{14}', '', base_name)
    
    # If the base name is now empty, use a default
    if not base_name:
        base_name = f"{module}_data"
    
    # Prefix with module name if not already included
    if not base_name.startswith(f"{module}_"):
        table_name = f"{module}_{base_name}"
    else:
        table_name = base_name
    
    return table_name

def check_for_duplicates(conn: duckdb.DuckDBPyConnection, target_table: str, source_conn: duckdb.DuckDBPyConnection, source_table: str) -> Tuple[bool, int]:
    """
    Check for duplicate records between source and target tables.
    
    Args:
        conn: Target DuckDB connection
        target_table: Target table name
        source_conn: Source DuckDB connection
        source_table: Source table name
        
    Returns:
        Tuple of (has_duplicates, duplicate_count)
    """
    try:
        # Check if target table exists
        try:
            conn.execute(f"SELECT COUNT(*) FROM {target_table}")
            target_exists = True
        except:
            return False, 0
            
        if not target_exists:
            return False, 0
            
        # Get primary key columns if they exist
        try:
            # Try to get primary key info from source table
            pk_info = source_conn.execute(f"PRAGMA table_info({source_table})").fetchall()
            pk_columns = [col[1] for col in pk_info if col[5] > 0]  # col[5] > 0 indicates primary key
            
            if not pk_columns:
                # If no primary key, try to find unique identifier columns
                columns = source_conn.execute(f"DESCRIBE {source_table}").fetchall()
                column_names = [col[0].lower() for col in columns]
                
                # Look for common ID columns
                for id_col in ['id', 'uuid', f'{source_table}_id', 'key', 'primary_key']:
                    if id_col in column_names:
                        pk_columns = [id_col]
                        break
            
            if not pk_columns:
                # If still no key columns, use all columns (will be slower)
                columns = source_conn.execute(f"DESCRIBE {source_table}").fetchall()
                pk_columns = [col[0] for col in columns]
                
        except Exception as e:
            logger.warning(f"Could not determine primary key for {source_table}: {str(e)}")
            return False, 0
            
        # Count records in source
        source_count = source_conn.execute(f"SELECT COUNT(*) FROM {source_table}").fetchone()[0]
        
        # Count records in target
        target_count = conn.execute(f"SELECT COUNT(*) FROM {target_table}").fetchone()[0]
        
        # If target is empty, no duplicates
        if target_count == 0:
            return False, 0
            
        # Create temporary view of source data in target database
        source_data = source_conn.execute(f"SELECT * FROM {source_table}").fetchall()
        column_names = [col[0] for col in source_conn.execute(f"DESCRIBE {source_table}").fetchall()]
        
        # Create a temporary table in the target database with the source data
        temp_table = f"temp_{source_table}_{int(time.time())}"
        columns_str = ", ".join([f"{col} {dtype}" for col, dtype in 
                               source_conn.execute(f"DESCRIBE {source_table}").fetchall()])
        
        conn.execute(f"CREATE TEMPORARY TABLE {temp_table} ({columns_str})")
        
        # Insert data in batches
        batch_size = 1000
        for i in range(0, len(source_data), batch_size):
            batch = source_data[i:i+batch_size]
            placeholders = ", ".join(["?" for _ in range(len(column_names))])
            for row in batch:
                conn.execute(f"INSERT INTO {temp_table} VALUES ({placeholders})", row)
        
        # Count duplicates based on primary key
        pk_columns_str = ", ".join(pk_columns)
        query = f"""
            SELECT COUNT(*) FROM (
                SELECT {pk_columns_str} FROM {temp_table}
                INTERSECT
                SELECT {pk_columns_str} FROM {target_table}
            )
        """
        
        duplicate_count = conn.execute(query).fetchone()[0]
        
        # Clean up
        conn.execute(f"DROP TABLE {temp_table}")
        
        return duplicate_count > 0, duplicate_count
        
    except Exception as e:
        logger.error(f"Error checking for duplicates: {str(e)}")
        return False, 0

def handle_duplicates(conn: duckdb.DuckDBPyConnection, target_table: str, source_conn: duckdb.DuckDBPyConnection, 
                     source_table: str, strategy: str = "update") -> str:
    """
    Handle duplicate records between source and target tables.
    
    Args:
        conn: Target DuckDB connection
        target_table: Target table name
        source_conn: Source DuckDB connection
        source_table: Source table name
        strategy: Strategy to handle duplicates ('update', 'skip', 'replace', 'version')
        
    Returns:
        The table name to use for insertion (may be modified if using versioning)
    """
    has_duplicates, duplicate_count = check_for_duplicates(conn, target_table, source_conn, source_table)
    
    if not has_duplicates:
        return target_table
        
    logger.info(f"Found {duplicate_count} duplicate records between {source_table} and {target_table}")
    
    if strategy == "skip":
        # Skip duplicates by creating a temporary table with only new records
        logger.info(f"Using 'skip' strategy - will only insert new records")
        
        # Get primary key columns
        pk_info = source_conn.execute(f"PRAGMA table_info({source_table})").fetchall()
        pk_columns = [col[1] for col in pk_info if col[5] > 0]
        
        if not pk_columns:
            # If no primary key, try to find unique identifier columns
            columns = source_conn.execute(f"DESCRIBE {source_table}").fetchall()
            column_names = [col[0].lower() for col in columns]
            
            # Look for common ID columns
            for id_col in ['id', 'uuid', f'{source_table}_id', 'key', 'primary_key']:
                if id_col in column_names:
                    pk_columns = [id_col]
                    break
        
        if not pk_columns:
            logger.warning(f"No primary key found for {source_table}, using all columns for comparison")
            columns = source_conn.execute(f"DESCRIBE {source_table}").fetchall()
            pk_columns = [col[0] for col in columns]
        
        # Create a temporary table with only new records
        pk_columns_str = ", ".join(pk_columns)
        temp_table = f"temp_new_{source_table}_{int(time.time())}"
        
        # Create the temporary table with the same schema as source
        columns_str = ", ".join([f"{col[0]} {col[1]}" for col in 
                               source_conn.execute(f"DESCRIBE {source_table}").fetchall()])
        
        conn.execute(f"CREATE TEMPORARY TABLE {temp_table} ({columns_str})")
        
        # Insert only records that don't exist in the target
        column_names = [col[0] for col in source_conn.execute(f"DESCRIBE {source_table}").fetchall()]
        column_names_str = ", ".join(column_names)
        
        # Create a temporary view of source data
        source_data = source_conn.execute(f"SELECT * FROM {source_table}").fetchall()
        source_temp = f"temp_source_{source_table}_{int(time.time())}"
        
        conn.execute(f"CREATE TEMPORARY TABLE {source_temp} ({columns_str})")
        
        # Insert data in batches
        batch_size = 1000
        for i in range(0, len(source_data), batch_size):
            batch = source_data[i:i+batch_size]
            placeholders = ", ".join(["?" for _ in range(len(column_names))])
            for row in batch:
                conn.execute(f"INSERT INTO {source_temp} VALUES ({placeholders})", row)
        
        # Insert only new records
        conn.execute(f"""
            INSERT INTO {temp_table}
            SELECT s.* FROM {source_temp} s
            LEFT JOIN {target_table} t
            ON {' AND '.join([f's.{col} = t.{col}' for col in pk_columns])}
            WHERE {' AND '.join([f't.{col} IS NULL' for col in pk_columns])}
        """)
        
        # Get count of new records
        new_count = conn.execute(f"SELECT COUNT(*) FROM {temp_table}").fetchone()[0]
        logger.info(f"Found {new_count} new records to insert")
        
        # Clean up source temp table
        conn.execute(f"DROP TABLE {source_temp}")
        
        return temp_table
        
    elif strategy == "update":
        # Update existing records and insert new ones
        logger.info(f"Using 'update' strategy - will update existing records and insert new ones")
        return target_table
        
    elif strategy == "replace":
        # Replace the target table with the source table
        logger.info(f"Using 'replace' strategy - will replace existing table")
        conn.execute(f"DROP TABLE IF EXISTS {target_table}")
        return target_table
        
    elif strategy == "version":
        # Create a new versioned table
        timestamp = int(time.time())
        new_table = f"{target_table}_{timestamp}"
        logger.info(f"Using 'version' strategy - creating new table {new_table}")
        return new_table
    
    return target_table

def upload_duckdb_file(file_path, target_database, dedup_strategy='update'):
    """
    Upload a DuckDB file to a MotherDuck database.
    """
    logger.info(f"Uploading file {file_path}")
    
    try:
        # Connect to the target database
        target_conn = get_motherduck_connection(target_database)
        
        # Connect to the source DuckDB file
        source_conn = duckdb.connect(file_path)
        
        # Get the list of tables in the source database
        tables = source_conn.execute("SHOW TABLES").fetchall()
        
        if not tables:
            logger.warning(f"No tables found in {file_path}")
            return
        
        # Try to set timeout for schema operations if supported
        try:
            # Check if the timeout_ms parameter is supported
            source_conn.execute("SELECT current_setting('TimeZone')")
            # If supported, set the timeout
            source_conn.execute("SET statement_timeout = '60s'")
        except Exception as e:
            logger.debug(f"Could not set timeout: {str(e)}")
        
        # Generate module name from file path
        module_name = get_module_name_from_path(file_path)
        
        # Process each table
        for table in tables:
            table_name = table[0]
            
            try:
                # Generate target table name
                target_table = f"{module_name}_{table_name}"
                
                # Check if target table exists
                target_exists = target_conn.execute(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{target_table}')"
                ).fetchone()[0]
                
                if target_exists:
                    if dedup_strategy == 'replace':
                        logger.info(f"Replacing existing table {target_table}")
                        target_conn.execute(f"DROP TABLE {target_table}")
                        target_exists = False
                    elif dedup_strategy == 'skip':
                        logger.info(f"Table {target_table} already exists, skipping")
                        continue
                    elif dedup_strategy == 'version':
                        # Create a versioned table
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        target_table = f"{target_table}_{timestamp}"
                        logger.info(f"Creating versioned table {target_table}")
                        target_exists = False
                
                # Try the direct approach using ATTACH DATABASE
                try:
                    # Attach the source database
                    source_alias = f"source_{int(time.time())}"
                    target_conn.execute(f"ATTACH '{file_path}' AS {source_alias}")
                    
                    try:
                        if not target_exists:
                            # Create the table directly from the source
                            logger.info(f"Creating table {target_table} from {table_name}")
                            target_conn.execute(f"CREATE TABLE {target_table} AS SELECT * FROM {source_alias}.{table_name}")
                            logger.info(f"Successfully created table {target_table}")
                        else:
                            # For update strategy, append data
                            logger.info(f"Appending data to {target_table}")
                            target_conn.execute(f"INSERT INTO {target_table} SELECT * FROM {source_alias}.{table_name}")
                            logger.info(f"Successfully appended data to {target_table}")
                    finally:
                        # Detach the source database
                        target_conn.execute(f"DETACH {source_alias}")
                    
                    # If we got here, the direct approach worked
                    continue
                except Exception as direct_error:
                    logger.warning(f"Direct approach failed for table {table_name}: {str(direct_error)}")
                    logger.info(f"Falling back to schema validation approach")
                
                # If direct approach failed, try the schema validation approach
                # Get the schema of the source table
                schema_query = f"DESCRIBE {table_name}"
                schema = source_conn.execute(schema_query).fetchall()
                
                # Validate the schema
                is_valid, issues, fixed_schema = validate_table_schema(schema, table_name)
                
                if not is_valid:
                    for issue in issues:
                        logger.warning(f"Schema issue in table {table_name}: {issue}")
                    
                    # Try to fix the schema issues
                    fixed_table = fix_table_schema(source_conn, table_name, fixed_schema)
                    if fixed_table:
                        table_name = fixed_table
                    else:
                        logger.error(f"Could not fix schema issues for table {table_name}")
                        continue
                
                # For smaller tables, use the standard approach with more validation
                # ... rest of the existing code for handling smaller tables
            except Exception as e:
                logger.error(f"Error processing table {table_name}: {str(e)}")
                # Continue with next table
        
        # Clean up
        source_conn.close()
        
        logger.info(f"Successfully uploaded {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to upload {file_path}: {str(e)}")
        return False

def upload_sqlite_file(file_path, target_database, dedup_strategy='update'):
    """
    Upload a SQLite file to a MotherDuck database.
    """
    logger.info(f"Uploading file {file_path}")
    
    try:
        # Connect to the target database
        target_conn = get_motherduck_connection(target_database)
        
        # Create a temporary DuckDB database to load the SQLite file
        temp_duckdb = duckdb.connect(':memory:')
        
        # Try to set timeout for schema operations if supported
        try:
            # Check if the timeout_ms parameter is supported
            temp_duckdb.execute("SELECT current_setting('TimeZone')")
            # If supported, set the timeout
            temp_duckdb.execute("SET statement_timeout = '60s'")
        except Exception as e:
            logger.debug(f"Could not set timeout: {str(e)}")
        
        # Get the list of tables in the SQLite file
        import sqlite3
        sqlite_conn = sqlite3.connect(file_path)
        cursor = sqlite_conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            logger.warning(f"No tables found in {file_path}")
            return
        
        # Generate module name from file path
        module_name = get_module_name_from_path(file_path)
        
        # Process each table
        for table in tables:
            table_name = table[0]
            
            try:
                # Generate target table name
                target_table = f"{module_name}_{table_name}"
                
                # Check if target table exists
                target_exists = target_conn.execute(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{target_table}')"
                ).fetchone()[0]
                
                if target_exists:
                    if dedup_strategy == 'replace':
                        logger.info(f"Replacing existing table {target_table}")
                        target_conn.execute(f"DROP TABLE {target_table}")
                        target_exists = False
                    elif dedup_strategy == 'skip':
                        logger.info(f"Table {target_table} already exists, skipping")
                        continue
                    elif dedup_strategy == 'version':
                        # Create a versioned table
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        target_table = f"{target_table}_{timestamp}"
                        logger.info(f"Creating versioned table {target_table}")
                        target_exists = False
                
                # Try the direct approach using a temporary DuckDB database
                try:
                    # Create a temporary table in DuckDB from the SQLite table
                    temp_table = f"temp_{table_name}_{int(time.time())}"
                    temp_duckdb.execute(f"CREATE TABLE {temp_table} AS SELECT * FROM sqlite_scan('{file_path}', '{table_name}')")
                    
                    # Get the schema of the temporary table
                    schema = temp_duckdb.execute(f"DESCRIBE {temp_table}").fetchall()
                    
                    # Create column definitions
                    column_defs = []
                    for col in schema:
                        column_defs.append(f"{col[0]} {col[1]}")
                    
                    if not target_exists:
                        # Create the target table
                        create_query = f"CREATE TABLE {target_table} ({', '.join(column_defs)})"
                        target_conn.execute(create_query)
                        
                        # Copy the data
                        target_conn.execute(f"INSERT INTO {target_table} SELECT * FROM sqlite_scan('{file_path}', '{table_name}')")
                        logger.info(f"Successfully created table {target_table}")
                    else:
                        # For update strategy, append data
                        target_conn.execute(f"INSERT INTO {target_table} SELECT * FROM sqlite_scan('{file_path}', '{table_name}')")
                        logger.info(f"Successfully appended data to {target_table}")
                    
                    # Clean up
                    temp_duckdb.execute(f"DROP TABLE {temp_table}")
                    
                    # If we got here, the direct approach worked
                    continue
                except Exception as direct_error:
                    logger.warning(f"Direct approach failed for table {table_name}: {str(direct_error)}")
                    logger.info(f"Falling back to schema validation approach")
                
                # If direct approach failed, try the schema validation approach
                # ... rest of the existing code for handling SQLite tables
            except Exception as e:
                logger.error(f"Error processing table {table_name}: {str(e)}")
                # Continue with next table
        
        # Clean up
        sqlite_conn.close()
        
        logger.info(f"Successfully uploaded {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to upload {file_path}: {str(e)}")
        return False

def upload_csv_file(file_path, target_database, dedup_strategy='update'):
    """
    Upload a CSV file to a MotherDuck database.
    """
    logger.info(f"Uploading CSV file {file_path}")
    
    try:
        # Connect to the target database
        target_conn = get_motherduck_connection(target_database)
        
        # Generate module name from file path
        module_name = get_module_name_from_path(file_path)
        
        # Generate target table name
        table_name = os.path.basename(file_path).split('.')[0]
        target_table = f"{module_name}_{table_name}"
        
        # Check if target table exists
        target_exists = target_conn.execute(
            f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{target_table}')"
        ).fetchone()[0]
        
        if target_exists:
            if dedup_strategy == 'replace':
                logger.info(f"Replacing existing table {target_table}")
                target_conn.execute(f"DROP TABLE {target_table}")
                target_exists = False
            elif dedup_strategy == 'skip':
                logger.info(f"Table {target_table} already exists, skipping")
                return True
            elif dedup_strategy == 'version':
                # Create a versioned table
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                target_table = f"{target_table}_{timestamp}"
                logger.info(f"Creating versioned table {target_table}")
                target_exists = False
        
        # Create the table and load data
        if not target_exists:
            # Create the table from the CSV file
            target_conn.execute(f"CREATE TABLE {target_table} AS SELECT * FROM read_csv_auto('{file_path}')")
            logger.info(f"Successfully created table {target_table}")
        else:
            # For update strategy, append data
            target_conn.execute(f"INSERT INTO {target_table} SELECT * FROM read_csv_auto('{file_path}')")
            logger.info(f"Successfully appended data to {target_table}")
        
        logger.info(f"Successfully uploaded {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to upload {file_path}: {str(e)}")
        return False

def upload_parquet_file(file_path, target_database, dedup_strategy='update'):
    """
    Upload a Parquet file to a MotherDuck database.
    """
    logger.info(f"Uploading Parquet file {file_path}")
    
    try:
        # Connect to the target database
        target_conn = get_motherduck_connection(target_database)
        
        # Generate module name from file path
        module_name = get_module_name_from_path(file_path)
        
        # Generate target table name
        table_name = os.path.basename(file_path).split('.')[0]
        target_table = f"{module_name}_{table_name}"
        
        # Check if target table exists
        target_exists = target_conn.execute(
            f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{target_table}')"
        ).fetchone()[0]
        
        if target_exists:
            if dedup_strategy == 'replace':
                logger.info(f"Replacing existing table {target_table}")
                target_conn.execute(f"DROP TABLE {target_table}")
                target_exists = False
            elif dedup_strategy == 'skip':
                logger.info(f"Table {target_table} already exists, skipping")
                return True
            elif dedup_strategy == 'version':
                # Create a versioned table
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                target_table = f"{target_table}_{timestamp}"
                logger.info(f"Creating versioned table {target_table}")
                target_exists = False
        
        # Create the table and load data
        if not target_exists:
            # Create the table from the Parquet file
            target_conn.execute(f"CREATE TABLE {target_table} AS SELECT * FROM read_parquet('{file_path}')")
            logger.info(f"Successfully created table {target_table}")
        else:
            # For update strategy, append data
            target_conn.execute(f"INSERT INTO {target_table} SELECT * FROM read_parquet('{file_path}')")
            logger.info(f"Successfully appended data to {target_table}")
        
        logger.info(f"Successfully uploaded {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to upload {file_path}: {str(e)}")
        return False

def upload_json_file(file_path, target_database, dedup_strategy='update'):
    """
    Upload a JSON file to a MotherDuck database.
    """
    logger.info(f"Uploading JSON file {file_path}")
    
    try:
        # Connect to the target database
        target_conn = get_motherduck_connection(target_database)
        
        # Generate module name from file path
        module_name = get_module_name_from_path(file_path)
        
        # Generate target table name
        table_name = os.path.basename(file_path).split('.')[0]
        target_table = f"{module_name}_{table_name}"
        
        # Check if target table exists
        target_exists = target_conn.execute(
            f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{target_table}')"
        ).fetchone()[0]
        
        if target_exists:
            if dedup_strategy == 'replace':
                logger.info(f"Replacing existing table {target_table}")
                target_conn.execute(f"DROP TABLE {target_table}")
                target_exists = False
            elif dedup_strategy == 'skip':
                logger.info(f"Table {target_table} already exists, skipping")
                return True
            elif dedup_strategy == 'version':
                # Create a versioned table
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                target_table = f"{target_table}_{timestamp}"
                logger.info(f"Creating versioned table {target_table}")
                target_exists = False
        
        # Create the table and load data
        if not target_exists:
            # Create the table from the JSON file
            target_conn.execute(f"CREATE TABLE {target_table} AS SELECT * FROM read_json_auto('{file_path}')")
            logger.info(f"Successfully created table {target_table}")
        else:
            # For update strategy, append data
            target_conn.execute(f"INSERT INTO {target_table} SELECT * FROM read_json_auto('{file_path}')")
            logger.info(f"Successfully appended data to {target_table}")
        
        logger.info(f"Successfully uploaded {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to upload {file_path}: {str(e)}")
        return False

def upload_file(file_path, target_database="dewey", dedup_strategy="update"):
    """Upload a file to MotherDuck or local DuckDB.
    
    Args:
        file_path: Path to the file to upload
        target_database: Name of the target database
        dedup_strategy: Strategy for handling duplicates ('update', 'skip', 'replace', 'version')
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Validate file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False
            
        # Get file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == '.duckdb':
            return upload_duckdb_file(file_path, target_database, dedup_strategy)
        elif ext in ['.db', '.sqlite', '.sqlite3']:
            # Validate SQLite file
            if not is_valid_sqlite_file(file_path):
                logger.warning(f"Not a valid SQLite database file: {file_path}")
                return False
            return upload_sqlite_file(file_path, target_database, dedup_strategy)
        elif ext == '.csv':
            return upload_csv_file(file_path, target_database, dedup_strategy)
        elif ext == '.json':
            return upload_json_file(file_path, target_database, dedup_strategy)
        elif ext == '.parquet':
            return upload_parquet_file(file_path, target_database, dedup_strategy)
        else:
            logger.warning(f"Unsupported file extension: {ext}")
            return False
    except Exception as e:
        logger.error(f"Error uploading file {file_path}: {str(e)}")
        return False

def upload_directory(directory_path, target_database="dewey", dedup_strategy="update", recursive=True):
    """Upload all supported files in a directory to MotherDuck or local DuckDB.
    
    Args:
        directory_path: Path to the directory containing files to upload
        target_database: Name of the target database
        dedup_strategy: Strategy for handling duplicates ('update', 'skip', 'replace', 'version')
        recursive: Whether to recursively search subdirectories
    
    Returns:
        tuple: (number of successfully uploaded files, total number of files)
    """
    try:
        # Check if directory exists
        if not os.path.isdir(directory_path):
            logger.error(f"Directory not found: {directory_path}")
            return 0, 0
            
        # Find all supported files
        file_list = []
        supported_extensions = ['.duckdb', '.db', '.sqlite', '.sqlite3', '.csv', '.json', '.parquet']
        
        if recursive:
            for root, _, files in os.walk(directory_path):
                for file in files:
                    _, ext = os.path.splitext(file)
                    if ext.lower() in supported_extensions:
                        file_list.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory_path):
                _, ext = os.path.splitext(file)
                if ext.lower() in supported_extensions:
                    file_list.append(os.path.join(directory_path, file))
        
        if not file_list:
            logger.warning(f"No supported files found in {directory_path}")
            return 0, 0
            
        # Upload each file
        success_count = 0
        total_count = len(file_list)
        
        logger.info(f"Found {total_count} files to upload")
        
        for file_path in file_list:
            logger.info(f"Uploading {file_path}")
            if upload_file(file_path, target_database, dedup_strategy):
                success_count += 1
                logger.info(f"Successfully uploaded {file_path}")
            else:
                logger.error(f"Failed to upload {file_path}")
        
        return success_count, total_count
    except Exception as e:
        logger.error(f"Error uploading directory {directory_path}: {str(e)}")
        return 0, 0

def get_module_name_from_path(file_path):
    """Extract module name from file path.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: Module name (crm, research, accounting, personal)
    """
    path_parts = file_path.lower().split('/')
    
    # Check for module names in the path
    for module in ['crm', 'research', 'accounting', 'personal']:
        if module in path_parts:
            return module
    
    # Default to the directory name if no known module is found
    dir_name = os.path.basename(os.path.dirname(file_path))
    return dir_name.replace(' ', '_').lower()

def get_table_schema(conn, table_name):
    """Get schema of a table as a dictionary.
    
    Args:
        conn: Database connection
        table_name: Name of the table
        
    Returns:
        dict: Dictionary mapping column names to types
    """
    try:
        schema_info = conn.execute(f"DESCRIBE {table_name}").fetchall()
        return {col[0]: col[1] for col in schema_info}
    except Exception:
        return {}

def schemas_match(schema1, schema2):
    """Compare two schemas to check if they match.
    
    Args:
        schema1: First schema dictionary
        schema2: Second schema dictionary
        
    Returns:
        bool: True if schemas match, False otherwise
    """
    if not schema1 or not schema2:
        return False
        
    # Compare column names and types
    if set(schema1.keys()) != set(schema2.keys()):
        return False
        
    for col, type1 in schema1.items():
        type2 = schema2.get(col)
        if type1 != type2:
            return False
            
    return True

def table_exists(conn, table_name):
    """Check if a table exists in the database.
    
    Args:
        conn: Database connection
        table_name: Name of the table
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        conn.execute(f"DESCRIBE {table_name}")
        return True
    except Exception:
        return False

def identify_primary_key(conn, table_name):
    """Identify primary key column of a table.
    
    Args:
        conn: Database connection
        table_name: Name of the table
        
    Returns:
        str: Name of primary key column, or None if not found
    """
    try:
        # Try to get primary key info
        pk_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        pk_columns = [col[1] for col in pk_info if col[5] > 0]  # col[5] is the pk flag
        
        if pk_columns:
            return pk_columns[0]
            
        # If no primary key, try to find common ID columns
        columns = conn.execute(f"DESCRIBE {table_name}").fetchall()
        column_names = [col[0].lower() for col in columns]
        
        for id_col in ['id', 'uuid', f'{table_name}_id', 'key', 'primary_key']:
            if id_col in column_names:
                return id_col
                
        return None
    except Exception:
        return None

def get_duckdb_type(sqlite_type):
    """Convert SQLite type to DuckDB type.
    
    Args:
        sqlite_type: SQLite data type
        
    Returns:
        str: Equivalent DuckDB data type
    """
    sqlite_type = sqlite_type.upper()
    
    if sqlite_type == "INTEGER":
        return "INTEGER"
    elif sqlite_type == "REAL":
        return "DOUBLE"
    elif sqlite_type in ["TEXT", "VARCHAR"]:
        return "VARCHAR"
    elif sqlite_type == "BLOB":
        return "BLOB"
    elif sqlite_type == "BOOLEAN":
        return "BOOLEAN"
    elif sqlite_type == "DATETIME":
        return "TIMESTAMP"
    elif sqlite_type == "DATE":
        return "DATE"
    else:
        return "VARCHAR"  # Default to VARCHAR for unknown types

def is_valid_sqlite_file(file_path):
    """Check if a file is a valid SQLite database.
    
    Args:
        file_path: Path to the file
        
    Returns:
        bool: True if valid SQLite file, False otherwise
    """
    # Check if file exists and has non-zero size
    if not os.path.exists(file_path):
        logger.error(f"SQLite file not found: {file_path}")
        return False
        
    if os.path.getsize(file_path) == 0:
        logger.error(f"SQLite file is empty: {file_path}")
        return False
        
    # Check SQLite file header magic string (should start with "SQLite format 3\0")
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
            if not header.startswith(b'SQLite format 3\0'):
                logger.error(f"Not a valid SQLite database file: {file_path}")
                return False
    except Exception as e:
        logger.error(f"Error reading SQLite file header: {str(e)}")
        return False
        
    # Try to connect to the SQLite database
    try:
        sqlite_conn = sqlite3.connect(file_path)
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        sqlite_conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error connecting to SQLite database: {str(e)}")
        return False

def validate_table_schema(schema, table_name):
    """
    Validate a table's schema for common issues.
    
    Args:
        schema: List of tuples containing (column_name, data_type, nullable)
        table_name: Name of the table
        
    Returns:
        Tuple of (is_valid, issues, modified_schema)
    """
    issues = []
    is_valid = True
    
    # Convert schema to a dictionary for easier manipulation
    schema_dict = {}
    for col in schema:
        col_name = col[0]
        col_type = col[1]
        
        # Check for empty column names
        if not col_name or col_name.strip() == '':
            is_valid = False
            new_col_name = f"column_{len(schema_dict)}"
            issues.append(f"Empty column name found, renamed to {new_col_name}")
            col_name = new_col_name
        
        # Check for duplicate column names (case insensitive)
        if col_name.lower() in [k.lower() for k in schema_dict.keys()]:
            is_valid = False
            new_col_name = f"{col_name}_{len(schema_dict)}"
            issues.append(f"Duplicate column name {col_name} found, renamed to {new_col_name}")
            col_name = new_col_name
        
        # Check for unsupported types
        if col_type not in ['INTEGER', 'BIGINT', 'DOUBLE', 'FLOAT', 'VARCHAR', 'TEXT', 'BOOLEAN', 'DATE', 'TIMESTAMP', 'BLOB']:
            is_valid = False
            if col_type in ['INT', 'INT4', 'INT8']:
                new_type = 'INTEGER'
            elif col_type in ['REAL', 'NUMERIC']:
                new_type = 'DOUBLE'
            elif col_type in ['CHAR', 'CHARACTER', 'NVARCHAR']:
                new_type = 'VARCHAR'
            elif col_type in ['BOOL']:
                new_type = 'BOOLEAN'
            elif col_type in ['DATETIME']:
                new_type = 'TIMESTAMP'
            else:
                new_type = 'VARCHAR'  # Default to VARCHAR for unknown types
            
            issues.append(f"Unsupported type {col_type} for column {col_name}, converted to {new_type}")
            col_type = new_type
        
        schema_dict[col_name] = col_type
    
    # Check if the table has at least one column
    if not schema_dict:
        is_valid = False
        issues.append("Table has no columns")
        schema_dict["id"] = "INTEGER"
    
    # Special handling for known problematic tables
    if table_name == 'domain_stats' and 'email_count' not in schema_dict:
        is_valid = False
        issues.append("Missing email_count column in domain_stats table, adding it")
        schema_dict['email_count'] = 'INTEGER'
    
    return is_valid, issues, schema_dict

def fix_table_schema(conn, table_name, modified_schema):
    """
    Create a fixed version of a table based on validation issues.
    
    Args:
        conn: DuckDB connection
        table_name: Name of the table to fix
        modified_schema: Dictionary of column_name -> data_type with fixes applied
        
    Returns:
        Name of the fixed table or None if failed
    """
    try:
        # Create a new table with the fixed schema
        fixed_table = f"fixed_{table_name}_{int(time.time())}"
        
        # Generate column definitions
        column_defs = []
        for col_name, col_type in modified_schema.items():
            column_defs.append(f"{col_name} {col_type}")
        
        # Create the fixed table
        create_query = f"CREATE TABLE {fixed_table} AS SELECT * FROM {table_name}"
        conn.execute(create_query)
        
        # For domain_stats table, set default value for email_count
        if table_name == 'domain_stats' and 'email_count' in modified_schema:
            conn.execute(f"UPDATE {fixed_table} SET email_count = 0 WHERE email_count IS NULL")
        
        return fixed_table
    except Exception as e:
        logger.error(f"Failed to fix schema for table {table_name}: {str(e)}")
        return None

def main():
    """Main function to upload data to MotherDuck."""
    parser = argparse.ArgumentParser(description='Upload data to MotherDuck')
    parser.add_argument('--file', help='Path to the file to upload')
    parser.add_argument('--dir', help='Path to the directory containing files to upload')
    parser.add_argument('--database', default='dewey', help='Name of the target database')
    parser.add_argument('--dedup-strategy', default='update', choices=['update', 'skip', 'replace', 'version'],
                        help='Strategy for handling duplicates')
    args = parser.parse_args()
    
    if not args.file and not args.dir:
        parser.error('Either --file or --dir must be specified')
    
    if args.file and args.dir:
        parser.error('Only one of --file or --dir can be specified')
    
    try:
        if args.dir:
            # Upload all files in the directory
            logger.info(f"Uploading files from directory {args.dir}")
            success_count, total_count = upload_directory(args.dir, args.database, args.dedup_strategy)
            logger.info(f"Uploaded {success_count} of {total_count} files successfully")
            return 0 if success_count == total_count else 1
        else:
            # Upload a single file
            logger.info(f"Uploading file {args.file}")
            success = upload_file(args.file, args.database, args.dedup_strategy)
            if success:
                logger.info(f"Successfully uploaded {args.file}")
                return 0
            else:
                logger.error(f"Failed to upload {args.file}")
                return 1
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1

if __name__ == "__main__":
    main() 