#!/usr/bin/env python
"""
Direct DB sync using DuckDB Python API.
Syncs tables from MotherDuck to local DuckDB database directly.
Also syncs schema changes from local back to MotherDuck.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
import argparse

# Ensure the project root is in the path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

import duckdb
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DBSyncer:
    """Class to handle synchronization between MotherDuck and local DuckDB."""
    
    def __init__(self, local_db_path: str, md_db_name: str, token: str):
        """Initialize the syncer with connection details.
        
        Args:
            local_db_path: Path to local DuckDB file
            md_db_name: MotherDuck database name
            token: MotherDuck authentication token
        """
        self.local_db_path = local_db_path
        self.md_db_name = md_db_name
        self.md_connection_string = f'md:{md_db_name}?motherduck_token={token}'
        self.batch_size = 10000
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.local_conn = None
        self.md_conn = None
        
    def connect(self) -> bool:
        """Establish connections to both databases.
        
        Returns:
            True if connections successful, False otherwise
        """
        try:
            self.md_conn = duckdb.connect(self.md_connection_string)
            logger.info("Successfully connected to MotherDuck")
            
            self.local_conn = duckdb.connect(self.local_db_path)
            logger.info("Successfully connected to local database")
            
            # Initialize sync metadata table
            self._init_sync_metadata()
            
            return True
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def _init_sync_metadata(self):
        """Initialize the sync metadata table in the local database."""
        try:
            # Create sync metadata table if it doesn't exist
            self.local_conn.execute("""
                CREATE TABLE IF NOT EXISTS dewey_sync_metadata (
                    table_name TEXT PRIMARY KEY,
                    last_sync_time TIMESTAMP,
                    last_sync_mode TEXT,
                    status TEXT,
                    error_message TEXT
                )
            """)
            logger.debug("Initialized sync metadata table")
        except Exception as e:
            logger.error(f"Error initializing sync metadata: {e}")
    
    def _get_last_sync_time(self, table_name: str) -> Optional[str]:
        """Get the last sync time for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Timestamp string of last sync or None if never synced
        """
        try:
            result = self.local_conn.execute(
                "SELECT last_sync_time FROM dewey_sync_metadata WHERE table_name = ?",
                [table_name]
            ).fetchone()
            
            if result and result[0]:
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Error getting last sync time: {e}")
            return None
    
    def _update_sync_metadata(self, table_name: str, sync_mode: str, status: str, error_message: str = ""):
        """Update the sync metadata for a table.
        
        Args:
            table_name: Name of the table
            sync_mode: 'full' or 'incremental'
            status: 'completed' or 'failed'
            error_message: Error message if status is 'failed'
        """
        try:
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            self.local_conn.execute("""
                INSERT OR REPLACE INTO dewey_sync_metadata
                (table_name, last_sync_time, last_sync_mode, status, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, [table_name, now, sync_mode, status, error_message])
            logger.debug(f"Updated sync metadata for {table_name}")
        except Exception as e:
            logger.error(f"Error updating sync metadata: {e}")
    
    def close(self):
        """Close database connections."""
        if self.md_conn:
            self.md_conn.close()
        if self.local_conn:
            self.local_conn.close()
    
    def list_tables(self, connection) -> List[str]:
        """Get list of tables from a connection.
        
        Args:
            connection: Database connection
            
        Returns:
            List of table names
        """
        tables = connection.execute('SHOW TABLES').fetchall()
        table_names = [table[0] for table in tables]
        
        # Filter out system tables
        filtered_tables = [t for t in table_names if not t.startswith('sqlite_') and 
                          not t.startswith('dewey_sync_') and
                          not t.startswith('information_schema')]
        return filtered_tables
    
    def get_table_schema(self, table_name: str, connection) -> Dict[str, str]:
        """Get the schema for a table.
        
        Args:
            table_name: Name of the table
            connection: Database connection
            
        Returns:
            Dictionary of column names to column types
        """
        schema_result = connection.execute(f"DESCRIBE {table_name}").fetchall()
        schema = {}
        
        for col in schema_result:
            col_name = col[0]
            col_type = col[1]
            schema[col_name] = col_type
            
        return schema
    
    def sync_schema_to_motherduck(self, table_name: str, local_schema: Dict[str, str], 
                                 md_schema: Dict[str, str]) -> bool:
        """Sync schema changes from local to MotherDuck.
        
        Args:
            table_name: Name of the table
            local_schema: Schema from local database
            md_schema: Schema from MotherDuck
            
        Returns:
            True if successful, False otherwise
        """
        # Find columns in local but not in MotherDuck
        new_columns = {col: dtype for col, dtype in local_schema.items() if col not in md_schema}
        
        if not new_columns:
            logger.info(f"  No schema changes to sync for {table_name}")
            return True
        
        logger.info(f"  Found {len(new_columns)} new columns to add to MotherDuck")
        
        try:
            for col_name, col_type in new_columns.items():
                logger.info(f"  Adding column {col_name} ({col_type}) to {table_name} in MotherDuck")
                self.md_conn.execute(f'ALTER TABLE {table_name} ADD COLUMN "{col_name}" {col_type}')
            return True
        except Exception as e:
            logger.error(f"  Error syncing schema for {table_name}: {e}")
            return False
    
    def create_table_in_motherduck(self, table_name: str, local_schema: Dict[str, str]) -> bool:
        """Create a table in MotherDuck based on local schema.
        
        Args:
            table_name: Name of the table
            local_schema: Schema from local database
            
        Returns:
            True if successful, False otherwise
        """
        try:
            create_stmt_parts = [f'"{col_name}" {col_type}' for col_name, col_type in local_schema.items()]
            create_stmt = f'CREATE TABLE {table_name} ({", ".join(create_stmt_parts)})'
            
            logger.info(f"  Creating table {table_name} in MotherDuck")
            self.md_conn.execute(create_stmt)
            return True
        except Exception as e:
            logger.error(f"  Error creating table {table_name} in MotherDuck: {e}")
            return False
    
    def check_table_exists(self, table_name: str, connection) -> bool:
        """Check if a table exists in the database.
        
        Args:
            table_name: Name of the table
            connection: Database connection
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            result = connection.execute(
                f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}')"
            ).fetchone()[0]
            return result
        except Exception:
            return False
    
    def sync_table_from_md_to_local(self, table_name: str, incremental: bool = False) -> bool:
        """Sync a table from MotherDuck to local.
        
        Args:
            table_name: Name of the table
            incremental: Whether to sync only new data since last sync
            
        Returns:
            True if sync successful, False otherwise
        """
        logger.info(f"Syncing table from MotherDuck to local: {table_name}")
        start_time = time.time()
        
        # Handle known column name mismatches
        column_mappings = {}
        if table_name == "master_clients":
            # Map from_email to from_address for this table
            column_mappings = {"from_email": "from_address"}
            logger.info(f"  Applied column name mapping for {table_name}: {column_mappings}")
        
        # Get last sync time if doing incremental sync
        last_sync_time = None
        if incremental:
            last_sync_time = self._get_last_sync_time(table_name)
            if last_sync_time:
                logger.info(f"  Incremental sync from {last_sync_time}")
            else:
                logger.info(f"  No previous sync found, falling back to full sync")
                incremental = False
        
        # Retry logic
        for attempt in range(self.max_retries):
            try:
                # Check if table exists in MotherDuck
                if not self.check_table_exists(table_name, self.md_conn):
                    logger.warning(f"  Table {table_name} does not exist in MotherDuck.")
                    return False
                
                # Count rows in the source table
                row_count = self.md_conn.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0]
                logger.info(f"  Source has {row_count} rows")
                
                if row_count == 0:
                    logger.info(f"  Table {table_name} is empty, skipping data transfer")
                    # Still sync the schema though
                    md_schema = self.get_table_schema(table_name, self.md_conn)
                    
                    # Apply column mappings if any exist (same as for non-empty tables)
                    if column_mappings and table_name == "master_clients":
                        # Adjust schema column names based on mappings
                        adjusted_schema = {}
                        for col_name, col_type in md_schema.items():
                            # If this column needs to be mapped, use the mapped name
                            if col_name in column_mappings:
                                adjusted_schema[column_mappings[col_name]] = col_type
                                logger.info(f"  Mapped column {col_name} to {column_mappings[col_name]}")
                            else:
                                adjusted_schema[col_name] = col_type
                        md_schema = adjusted_schema
                    
                    # Create or replace the table in the local database
                    create_stmt_parts = [f'"{col_name}" {col_type}' for col_name, col_type in md_schema.items()]
                    create_stmt = f'CREATE TABLE IF NOT EXISTS {table_name} ({", ".join(create_stmt_parts)})'
                    self.local_conn.execute(create_stmt)
                    
                    # Update sync metadata
                    self._update_sync_metadata(table_name, 'full' if not incremental else 'incremental', 'completed')
                    
                    duration = time.time() - start_time
                    logger.info(f"  Synced schema in {duration:.2f} seconds")
                    return True
                
                # Get the table schema
                md_schema = self.get_table_schema(table_name, self.md_conn)
                
                # Apply column mappings if any exist
                if column_mappings and table_name == "master_clients":
                    # Adjust schema column names based on mappings
                    adjusted_schema = {}
                    for col_name, col_type in md_schema.items():
                        # If this column needs to be mapped, use the mapped name
                        if col_name in column_mappings:
                            adjusted_schema[column_mappings[col_name]] = col_type
                            logger.info(f"  Mapped column {col_name} to {column_mappings[col_name]}")
                        else:
                            adjusted_schema[col_name] = col_type
                    md_schema = adjusted_schema
                
                # Create table if it doesn't exist
                if not self.check_table_exists(table_name, self.local_conn):
                    create_stmt_parts = [f'"{col_name}" {col_type}' for col_name, col_type in md_schema.items()]
                    create_stmt = f'CREATE TABLE {table_name} ({", ".join(create_stmt_parts)})'
                    self.local_conn.execute(create_stmt)
                    logger.info(f"  Created table {table_name} in local database")
                    # Force full sync for new tables
                    incremental = False
                
                # For full sync, drop and recreate the table
                if not incremental:
                    # Drop and recreate the table (full sync strategy)
                    self.local_conn.execute(f'DROP TABLE IF EXISTS {table_name}')
                    create_stmt_parts = [f'"{col_name}" {col_type}' for col_name, col_type in md_schema.items()]
                    create_stmt = f'CREATE TABLE {table_name} ({", ".join(create_stmt_parts)})'
                    self.local_conn.execute(create_stmt)
                
                # Now fetch the data in batches and insert it
                logger.info(f"  Transferring data...")
                offset = 0
                total_transferred = 0
                
                while offset < row_count:
                    # Construct batch query based on sync mode
                    if column_mappings and table_name == "master_clients":
                        # For master_clients, build a query with column renaming
                        select_cols = []
                        for col_name in self.get_table_schema(table_name, self.md_conn).keys():
                            if col_name in column_mappings:
                                # Rename the column in the SELECT
                                select_cols.append(f'"{col_name}" as "{column_mappings[col_name]}"')
                            else:
                                select_cols.append(f'"{col_name}"')
                        
                        if incremental and last_sync_time and 'modified_at' in md_schema:
                            # Use modified_at for incremental if available
                            batch_query = f"""
                                SELECT {', '.join(select_cols)} 
                                FROM {table_name} 
                                WHERE modified_at >= '{last_sync_time}'
                                LIMIT {self.batch_size} OFFSET {offset}
                            """
                        else:
                            # Regular query with column mapping
                            batch_query = f"""
                                SELECT {', '.join(select_cols)} 
                                FROM {table_name} 
                                LIMIT {self.batch_size} OFFSET {offset}
                            """
                    else:
                        # Normal case, no column renaming
                        if incremental and last_sync_time and 'modified_at' in md_schema:
                            # Use modified_at for incremental if available
                            batch_query = f"""
                                SELECT * FROM {table_name} 
                                WHERE modified_at >= '{last_sync_time}'
                                LIMIT {self.batch_size} OFFSET {offset}
                            """
                        else:
                            # Regular query
                            batch_query = f"SELECT * FROM {table_name} LIMIT {self.batch_size} OFFSET {offset}"
                    
                    batch_data = self.md_conn.execute(batch_query).fetchdf()
                    
                    # If batch is empty, we're done
                    if batch_data.empty:
                        break
                    
                    # For incremental sync with a timestamp, we need to DELETE + INSERT for modified records
                    if incremental and 'modified_at' in md_schema and 'id' in md_schema:
                        # Extract IDs from the batch to delete existing records
                        ids = batch_data['id'].tolist()
                        if ids:
                            id_list = ','.join([f"'{id}'" for id in ids])
                            self.local_conn.execute(f"DELETE FROM {table_name} WHERE id IN ({id_list})")
                    
                    # Insert the batch into the local database
                    self.local_conn.register("batch_data", batch_data)
                    self.local_conn.execute(f"INSERT INTO {table_name} SELECT * FROM batch_data")
                    
                    # Update offset and log progress
                    batch_size = len(batch_data)
                    total_transferred += batch_size
                    offset += self.batch_size
                    logger.info(f"  Transferred {total_transferred}/{row_count} rows")
                
                # Verify row count in destination
                local_rows = self.local_conn.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0]
                logger.info(f"  Destination has {local_rows} rows")
                
                # Update sync metadata
                self._update_sync_metadata(table_name, 'full' if not incremental else 'incremental', 'completed')
                
                duration = time.time() - start_time
                logger.info(f"  Synced in {duration:.2f} seconds")
                return True
                
            except Exception as e:
                logger.error(f"  Attempt {attempt+1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    logger.info(f"  Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"  Failed to sync table {table_name} after {self.max_retries} attempts")
                    # Update sync metadata with failure
                    self._update_sync_metadata(
                        table_name, 
                        'full' if not incremental else 'incremental', 
                        'failed', 
                        str(e)
                    )
                    return False
    
    def sync_schema_from_local_to_md(self, table_name: str) -> bool:
        """Sync schema changes from local to MotherDuck.
        
        Args:
            table_name: Name of the table
            
        Returns:
            True if sync successful, False otherwise
        """
        logger.info(f"Syncing schema from local to MotherDuck: {table_name}")
        start_time = time.time()
        
        try:
            # First check if the table exists in both places
            exists_local = self.check_table_exists(table_name, self.local_conn)
            exists_md = self.check_table_exists(table_name, self.md_conn)
            
            if not exists_local:
                logger.warning(f"  Table {table_name} does not exist in local DB, skipping schema sync")
                return False
            
            # Get local schema
            local_schema = self.get_table_schema(table_name, self.local_conn)
            
            if not exists_md:
                # Table doesn't exist in MotherDuck, create it
                logger.info(f"  Table {table_name} does not exist in MotherDuck, creating it")
                return self.create_table_in_motherduck(table_name, local_schema)
            
            # Table exists in both places, sync schema differences
            md_schema = self.get_table_schema(table_name, self.md_conn)
            return self.sync_schema_to_motherduck(table_name, local_schema, md_schema)
            
        except Exception as e:
            logger.error(f"  Error syncing schema for {table_name}: {e}")
            return False
    
    def sync_all(self, md_to_local: bool = True, local_to_md_schema: bool = True, incremental: bool = False) -> Tuple[int, int, List[str]]:
        """Sync all tables between MotherDuck and local.
        
        Args:
            md_to_local: Whether to sync data from MotherDuck to local
            local_to_md_schema: Whether to sync schema from local to MotherDuck
            incremental: Whether to sync only new data since last sync
            
        Returns:
            Tuple of (successful syncs, total tables, failed tables)
        """
        if not self.connect():
            return 0, 0, []
        
        try:
            # Get tables from both databases
            md_tables = self.list_tables(self.md_conn)
            local_tables = self.list_tables(self.local_conn) if local_to_md_schema else []
            
            # Combine tables from both sources
            all_tables = list(set(md_tables) | set(local_tables))
            logger.info(f"Found {len(all_tables)} tables to process")
            
            # Track sync results
            successful_syncs = 0
            failed_tables = []
            
            # Sync each table
            for table_name in all_tables:
                success = True
                
                # First sync schema if needed
                if local_to_md_schema and table_name in local_tables:
                    schema_success = self.sync_schema_from_local_to_md(table_name)
                    success = success and schema_success
                
                # Then sync data if needed
                if md_to_local and table_name in md_tables:
                    data_success = self.sync_table_from_md_to_local(table_name, incremental)
                    success = success and data_success
                
                if success:
                    successful_syncs += 1
                else:
                    failed_tables.append(table_name)
            
            logger.info(f"\nSummary: Successfully synced {successful_syncs}/{len(all_tables)} tables")
            
            if failed_tables:
                logger.warning(f"Failed tables: {', '.join(failed_tables)}")
            
            return successful_syncs, len(all_tables), failed_tables
            
        finally:
            self.close()

def main():
    """Main function to run the sync process."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Sync DuckDB databases between MotherDuck and local')
    parser.add_argument('--table', help='Sync only the specified table')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--mode', choices=['full', 'incremental'], default='full',
                       help='Sync mode: full (default) or incremental')
    args = parser.parse_args()
    
    # Set log level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Get MotherDuck token from environment
    token = os.environ.get('MOTHERDUCK_TOKEN')
    if not token:
        logger.error("Error: MOTHERDUCK_TOKEN environment variable is not set")
        return 1
    
    # Set up paths
    local_db_path = str(project_root / "dewey.duckdb")
    motherduck_db = "dewey"
    
    logger.info(f"Starting direct sync between MotherDuck:{motherduck_db} and local:{local_db_path}")
    
    try:
        # Create syncer and run sync
        syncer = DBSyncer(local_db_path, motherduck_db, token)
        
        # Handle single table sync if specified
        if args.table:
            if not syncer.connect():
                logger.error("Failed to connect to databases")
                return 1
                
            try:
                # Run sync for the specified table
                if args.mode == 'incremental':
                    success = syncer.sync_table_from_md_to_local(args.table, incremental=True)
                else:
                    success = syncer.sync_table_from_md_to_local(args.table, incremental=False)
                
                # Get the database file size
                db_size = Path(local_db_path).stat().st_size / (1024 * 1024 * 1024)  # Convert to GB
                logger.info(f"Local database size: {db_size:.2f} GB")
                
                return 0 if success else 1
            finally:
                syncer.close()
        else:
            # Run sync for all tables
            successful, total, failed = syncer.sync_all(
                md_to_local=True,
                local_to_md_schema=True,
                incremental=(args.mode == 'incremental')
            )
            
            # Get the database file size
            db_size = Path(local_db_path).stat().st_size / (1024 * 1024 * 1024)  # Convert to GB
            logger.info(f"Local database size: {db_size:.2f} GB")
            
            # Return success if all tables synced, or partial success code
            if successful == total:
                return 0
            elif successful > 0:
                return 2  # Partial success
            else:
                return 1  # Complete failure
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 