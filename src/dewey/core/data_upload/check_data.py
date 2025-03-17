#!/usr/bin/env python
import os
import sys
import argparse
import logging
import duckdb
from tabulate import tabulate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_motherduck_connection(database_name="dewey"):
    """Connect to MotherDuck database."""
    try:
        conn = duckdb.connect(f"md:{database_name}")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to MotherDuck database {database_name}: {str(e)}")
        return None

def list_tables(conn, prefix=None):
    """List tables in the database, optionally filtered by prefix."""
    try:
        if prefix:
            query = f"SELECT table_name FROM information_schema.tables WHERE table_name LIKE '{prefix}%'"
        else:
            query = "SELECT table_name FROM information_schema.tables"
        
        result = conn.execute(query).fetchall()
        return [r[0] for r in result]
    except Exception as e:
        logger.error(f"Error listing tables: {str(e)}")
        return []

def get_table_info(conn, table_name):
    """Get information about a table."""
    try:
        # Get row count
        row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        
        # Get column info
        columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        column_info = [(col[1], col[2]) for col in columns]  # name, type
        
        # Get sample data (first 5 rows)
        sample_data = conn.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchall()
        
        return {
            "row_count": row_count,
            "columns": column_info,
            "sample_data": sample_data
        }
    except Exception as e:
        logger.error(f"Error getting info for table {table_name}: {str(e)}")
        return None

def print_table_summary(table_name, table_info):
    """Print a summary of a table."""
    if not table_info:
        logger.error(f"No information available for table {table_name}")
        return
    
    print(f"\n{'=' * 80}")
    print(f"TABLE: {table_name}")
    print(f"{'=' * 80}")
    print(f"Row count: {table_info['row_count']}")
    
    print("\nColumns:")
    column_data = [(i+1, col[0], col[1]) for i, col in enumerate(table_info['columns'])]
    print(tabulate(column_data, headers=["#", "Name", "Type"], tablefmt="grid"))
    
    if table_info['sample_data']:
        print("\nSample data (first 5 rows):")
        headers = [col[0] for col in table_info['columns']]
        print(tabulate(table_info['sample_data'], headers=headers, tablefmt="grid"))
    else:
        print("\nNo sample data available (table may be empty)")

def main():
    parser = argparse.ArgumentParser(description="Check data in MotherDuck database")
    parser.add_argument("--database", default="dewey", help="MotherDuck database name")
    parser.add_argument("--prefix", help="Filter tables by prefix")
    parser.add_argument("--table", help="Specific table to check")
    parser.add_argument("--list_only", action="store_true", help="Only list tables, don't show details")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Connect to MotherDuck
    conn = get_motherduck_connection(args.database)
    if not conn:
        return 1
    
    # List tables
    if args.table:
        tables = [args.table]
    else:
        tables = list_tables(conn, args.prefix)
    
    if not tables:
        logger.warning(f"No tables found{' with prefix ' + args.prefix if args.prefix else ''}")
        return 0
    
    # Print table list
    print(f"\nFound {len(tables)} tables in database {args.database}:")
    for i, table in enumerate(tables):
        print(f"{i+1}. {table}")
    
    # Exit if only listing tables
    if args.list_only:
        return 0
    
    # Print table details
    for table in tables:
        table_info = get_table_info(conn, table)
        print_table_summary(table, table_info)
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1) 