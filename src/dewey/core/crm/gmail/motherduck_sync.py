#!/usr/bin/env python3
"""Sync local DuckDB database to MotherDuck for improved concurrency.

This script:
1. Connects to the local DuckDB database
2. Connects to MotherDuck
3. Syncs the emails table to MotherDuck
4. Adds a timestamp for the last sync
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb
import structlog

# Add the project root to the Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logger = structlog.get_logger(__name__)

def sync_to_motherduck(local_db_path=None, motherduck_db=None):
    """Sync local DuckDB database to MotherDuck.
    
    Args:
        local_db_path: Path to local DuckDB database (default: ~/dewey_emails.duckdb)
        motherduck_db: MotherDuck database name (default: dewey_emails)
        
    Returns:
        bool: True if sync was successful, False otherwise
    """
    # Default paths
    local_db_path = local_db_path or os.path.expanduser("~/dewey_emails.duckdb")
    motherduck_db = motherduck_db or "dewey_emails"
    
    # Get MotherDuck token from environment
    motherduck_token = os.environ.get("MOTHERDUCK_TOKEN")
    if not motherduck_token:
        logger.error("MOTHERDUCK_TOKEN environment variable not set")
        return False
    
    try:
        # Connect to local database in read-only mode
        logger.info("Connecting to local database", path=local_db_path)
        
        # Try multiple times with exponential backoff in case the database is locked
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                local_conn = duckdb.connect(local_db_path, read_only=True)
                break
            except Exception as e:
                if attempt < max_attempts - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4, 8, 16 seconds
                    logger.warning(
                        "Failed to connect to local database, retrying",
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        wait_time=wait_time,
                        error=str(e),
                    )
                    time.sleep(wait_time)
                else:
                    raise
        
        # Connect to MotherDuck
        logger.info("Connecting to MotherDuck", database=motherduck_db)
        motherduck_conn = duckdb.connect(f"md:{motherduck_db}?motherduck_token={motherduck_token}")
        
        # Get list of tables in local database
        tables = local_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [table[0] for table in tables]
        logger.info("Found tables in local database", tables=table_names)
        
        # Sync each table to MotherDuck
        for table_name in table_names:
            logger.info("Syncing table to MotherDuck", table=table_name)
            
            # Create table in MotherDuck if it doesn't exist
            schema = local_conn.execute(f"DESCRIBE {table_name}").fetchall()
            columns = []
            for col in schema:
                columns.append(f"{col[0]} {col[1]}")
            
            # Create table in MotherDuck with the same schema
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {', '.join(columns)}
            )
            """
            motherduck_conn.execute(create_table_sql)
            
            # Get the count of rows in the local table
            local_count = local_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            logger.info("Local table row count", table=table_name, count=local_count)
            
            # Get the count of rows in the MotherDuck table
            md_count = motherduck_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            logger.info("MotherDuck table row count", table=table_name, count=md_count)
            
            # If the counts are different, sync the data
            if local_count != md_count:
                logger.info(
                    "Syncing data to MotherDuck",
                    table=table_name,
                    local_count=local_count,
                    md_count=md_count,
                )
                
                # For emails table, use message_id as the key for upsert
                if table_name == "emails":
                    # First, create a temporary table with the local data
                    motherduck_conn.execute(f"CREATE OR REPLACE TEMPORARY TABLE temp_{table_name} AS SELECT * FROM '{local_db_path}'.{table_name}")
                    
                    # Then, perform an upsert operation
                    motherduck_conn.execute(f"""
                    INSERT OR REPLACE INTO {table_name}
                    SELECT * FROM temp_{table_name}
                    """)
                    
                    # Drop the temporary table
                    motherduck_conn.execute(f"DROP TABLE temp_{table_name}")
                else:
                    # For other tables, just replace the data
                    motherduck_conn.execute(f"DELETE FROM {table_name}")
                    motherduck_conn.execute(f"INSERT INTO {table_name} SELECT * FROM '{local_db_path}'.{table_name}")
            else:
                logger.info("Table already in sync", table=table_name)
        
        # Add sync timestamp
        sync_time = datetime.now().isoformat()
        motherduck_conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_metadata (
            key VARCHAR PRIMARY KEY,
            value VARCHAR,
            updated_at TIMESTAMP
        )
        """)
        
        motherduck_conn.execute("""
        INSERT OR REPLACE INTO sync_metadata (key, value, updated_at)
        VALUES ('last_sync', ?, CURRENT_TIMESTAMP)
        """, [sync_time])
        
        logger.info("Sync completed successfully", timestamp=sync_time)
        
        # Close connections
        local_conn.close()
        motherduck_conn.close()
        
        return True
        
    except Exception as e:
        logger.exception("Error syncing to MotherDuck", error=str(e))
        return False

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync local DuckDB database to MotherDuck")
    parser.add_argument(
        "--local-db",
        help="Path to local DuckDB database (default: ~/dewey_emails.duckdb)",
        default=os.path.expanduser("~/dewey_emails.duckdb"),
    )
    parser.add_argument(
        "--motherduck-db",
        help="MotherDuck database name (default: dewey_emails)",
        default="dewey_emails",
    )
    
    args = parser.parse_args()
    
    # Run the sync
    success = sync_to_motherduck(args.local_db, args.motherduck_db)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 