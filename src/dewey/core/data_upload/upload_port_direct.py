#!/usr/bin/env python3
"""
Direct uploader for port.duckdb file.
This script uses a simplified approach to upload the port.duckdb file directly to MotherDuck.
"""

import os
import sys
import time
import logging
import duckdb

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def get_motherduck_connection(database_name="dewey"):
    """Get a connection to MotherDuck or local DuckDB."""
    try:
        # Check if MOTHERDUCK_TOKEN is set
        token = os.environ.get("MOTHERDUCK_TOKEN")
        if token:
            # Connect to MotherDuck
            conn_str = f"md:{database_name}"
            conn = duckdb.connect(conn_str)
            logger.info(f"Connected to MotherDuck database: {database_name}")
        else:
            # Connect to local DuckDB
            conn_str = f"{database_name}.duckdb"
            conn = duckdb.connect(conn_str)
            logger.info(f"Connected to local DuckDB database: {conn_str}")
        
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

def direct_upload_table(source_path, table_name, target_database="dewey", dedup_strategy="skip"):
    """
    Upload a table directly from a DuckDB file to MotherDuck.
    
    Args:
        source_path: Path to the source DuckDB file
        table_name: Name of the table to upload
        target_database: Name of the target database
        dedup_strategy: Strategy for handling duplicates ('update', 'skip', 'replace', 'version')
    """
    try:
        # Connect to the target database
        target_conn = get_motherduck_connection(target_database)
        
        # Generate target table name
        module_name = os.path.basename(source_path).split('.')[0]
        target_table = f"{module_name}_{table_name}"
        
        # Check if target table exists
        target_exists = target_conn.execute(
            f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{target_table}')"
        ).fetchone()[0]
        
        if target_exists:
            if dedup_strategy == "replace":
                logger.info(f"Replacing existing table {target_table}")
                target_conn.execute(f"DROP TABLE {target_table}")
                target_exists = False
            elif dedup_strategy == "skip":
                logger.info(f"Table {target_table} already exists, skipping")
                return
            elif dedup_strategy == "version":
                timestamp = int(time.time())
                target_table = f"{target_table}_{timestamp}"
                logger.info(f"Creating versioned table {target_table}")
                target_exists = False
        
        # Attach the source database
        source_alias = f"source_{int(time.time())}"
        target_conn.execute(f"ATTACH '{source_path}' AS {source_alias}")
        
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
    
    except Exception as e:
        logger.error(f"Error uploading table {table_name}: {str(e)}")
        raise

def main():
    """Main function to upload port.duckdb tables."""
    source_path = "/Users/srvo/input_data/port.duckdb"
    dedup_strategy = "skip"
    
    # Connect to source DuckDB file to get table list
    try:
        source_conn = duckdb.connect(source_path)
        tables = source_conn.execute("SHOW TABLES").fetchall()
        
        if not tables:
            logger.warning(f"No tables found in {source_path}")
            return
        
        logger.info(f"Found {len(tables)} tables in {source_path}")
        
        # Process each table
        for table_info in tables:
            table_name = table_info[0]
            logger.info(f"Processing table {table_name}")
            
            try:
                direct_upload_table(source_path, table_name, dedup_strategy=dedup_strategy)
                logger.info(f"Successfully uploaded table {table_name}")
            except Exception as e:
                logger.error(f"Failed to upload table {table_name}: {str(e)}")
                # Continue with next table
        
        logger.info(f"Completed processing all tables in {source_path}")
        
    except Exception as e:
        logger.error(f"Error processing {source_path}: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 