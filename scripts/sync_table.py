#!/usr/bin/env python
"""
Sync a single table from MotherDuck to local DuckDB.
This script provides a simple way to copy one table at a time.

Usage:
    python sync_table.py <table_name>
"""

import os
import sys
import time
import tempfile
from pathlib import Path

# Ensure the project root is in the path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

import duckdb

def sync_table(table_name):
    """Sync a specific table from MotherDuck to local DuckDB."""
    # Get MotherDuck token from environment
    token = os.environ.get('MOTHERDUCK_TOKEN')
    if not token:
        print("Error: MOTHERDUCK_TOKEN environment variable is not set")
        return False
    
    # Set up paths
    local_db_path = str(project_root / "dewey.duckdb")
    motherduck_db = "dewey"
    
    print(f"Syncing table {table_name} from MotherDuck:{motherduck_db} to local:{local_db_path}")
    
    try:
        # Connect to both databases
        md_conn = duckdb.connect(f'md:{motherduck_db}?motherduck_token={token}')
        local_conn = duckdb.connect(local_db_path)
        
        start_time = time.time()
        
        # Check if table exists in MotherDuck
        table_exists = md_conn.execute(
            f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}')"
        ).fetchone()[0]
        
        if not table_exists:
            print(f"Error: Table {table_name} does not exist in MotherDuck")
            return False
        
        # Count rows in the source table
        row_count = md_conn.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0]
        print(f"  Source has {row_count} rows")
        
        # Skip if table is empty
        if row_count == 0:
            print(f"  Table {table_name} is empty, skipping")
            return True
        
        # Create a temporary directory for CSV files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Get schema from MotherDuck
            schema_result = md_conn.execute(f"DESCRIBE {table_name}").fetchall()
            columns = []
            create_stmt_parts = []
            
            for col in schema_result:
                col_name = col[0]
                col_type = col[1]
                columns.append(col_name)
                create_stmt_parts.append(f'"{col_name}" {col_type}')
            
            create_stmt = f'CREATE TABLE {table_name} ({", ".join(create_stmt_parts)})'
            
            # Export from MotherDuck to CSV
            csv_path = os.path.join(temp_dir, f"{table_name}.csv")
            print(f"  Exporting data to CSV: {csv_path}")
            md_conn.execute(f"COPY (SELECT * FROM {table_name}) TO '{csv_path}' (HEADER, DELIMITER ',')")
            
            # Create table in local and import from CSV
            print(f"  Creating table in local database")
            local_conn.execute(f'DROP TABLE IF EXISTS {table_name}')
            local_conn.execute(create_stmt)
            
            print(f"  Importing data from CSV")
            local_conn.execute(f"COPY {table_name} FROM '{csv_path}' (HEADER, DELIMITER ',')")
            
            # Verify row count in the destination
            local_rows = local_conn.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0]
            print(f"  Destination has {local_rows} rows")
        
        duration = time.time() - start_time
        print(f"  Synced in {duration:.2f} seconds")
        
        # Close connections
        md_conn.close()
        local_conn.close()
        
        return True
    
    except Exception as e:
        print(f"Error syncing table {table_name}: {e}")
        return False

def main():
    """Main function to parse arguments and sync a table."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <table_name>")
        return 1
    
    table_name = sys.argv[1]
    success = sync_table(table_name)
    
    # Get the database file size
    local_db_path = str(project_root / "dewey.duckdb")
    db_size = Path(local_db_path).stat().st_size / (1024 * 1024)  # Convert to MB
    print(f"Local database size: {db_size:.2f} MB")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 