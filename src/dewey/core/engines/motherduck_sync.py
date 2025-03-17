
# Refactored from: motherduck_sync
# Date: 2025-03-16T16:19:11.339855
# Refactor Version: 1.0
```python
#!/usr/bin/env python
"""Sync local DuckDB data to MotherDuck cloud service with detailed logging."""

import argparse
import logging
import os
from pathlib import Path
from typing import Any, Dict

import ibis
from ibis.duckdb import DuckDBBackend
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler and formatter
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

# Create file handler
fh = logging.FileHandler("motherduck_sync.log")
fh.setFormatter(formatter)
logger.addHandler(fh)


def get_motherduck_connection(token: str) -> DuckDBBackend:
    """Create and return a MotherDuck connection using Ibis.

    Args:
        token: The MotherDuck token.

    Returns:
        A DuckDBBackend object representing the MotherDuck connection.
    """
    logger.info("Creating MotherDuck connection")
    return ibis.connect(f"duckdb://md:?motherduck_token={token}")


def sync_table_to_motherduck(
    local_con: DuckDBBackend, md_con: DuckDBBackend, table_name: str
) -> None:
    """Sync a single table from local DuckDB to MotherDuck.

    Args:
        local_con: The local DuckDB connection.
        md_con: The MotherDuck connection.
        table_name: The name of the table to sync.
    """
    try:
        logger.info(f"Starting sync for table: {table_name}")

        # Check if table exists locally
        if not local_con.exists(table_name):
            logger.warning(f"Local table {table_name} doesn't exist, skipping")
            return

        # Get local table
        logger.debug(f"Loading local table: {table_name}")
        local_table = local_con.table(table_name)

        # Create or replace table in MotherDuck
        if md_con.exists(table_name):
            logger.info(f"Table {table_name} exists in MotherDuck, replacing")
            md_con.unregister(table_name)

        logger.info(
            f"Creating table {table_name} in MotherDuck with schema matching local"
        )
        # Execute the local table expression and create table in MotherDuck with results
        data = local_table.execute()
        md_con.create_table(table_name, data, overwrite=True)
        logger.info(f"Successfully synced {table_name}")

    except Exception as e:
        logger.error(f"Failed to sync table {table_name}: {str(e)}")
        raise


def sync_database(
    db_file: Path, md_con: DuckDBBackend, result: Dict[str, Any]
) -> None:
    """Syncs all tables from a single DuckDB database to MotherDuck.

    Args:
        db_file: Path to the DuckDB database file.
        md_con: The MotherDuck connection.
        result: A dictionary to store the results of the sync process.
    """
    try:
        logger.info(f"Processing database: {db_file.name}")
        local_con = ibis.connect(f"duckdb:///{db_file}")
        result["databases_processed"].append(db_file.name)

        # Get list of tables
        logger.info("Listing local tables")
        tables = local_con.list_tables()
        logger.info(f"Found {len(tables)} tables to sync: {', '.join(tables)}")

        # Sync each table
        for table in tables:
            try:
                sync_table_to_motherduck(local_con, md_con, table)
                result["tables_synced"].append(table)
            except Exception as e:
                error_msg = f"Table {table} failed: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
    except Exception as e:
        error_msg = f"Failed to process {db_file.name}: {str(e)}"
        logger.error(error_msg)
        result["errors"].append(error_msg)


def sync_to_motherduck(db_directory: str, token: str) -> Dict[str, Any]:
    """Main sync function with detailed logging and error handling.

    Args:
        db_directory: The directory containing the DuckDB databases.
        token: The MotherDuck token.

    Returns:
        A dictionary containing the results of the sync process.
    """
    result: Dict[str, Any] = {
        "success": False,
        "databases_processed": [],
        "tables_synced": [],
        "errors": [],
    }

    try:
        logger.info("Starting MotherDuck sync process")
        logger.debug(
            f"Database directory: {db_directory}, MotherDuck token: {'***' if token else '<missing>'}"
        )

        # Validate directory
        db_path = Path(db_directory)
        if not db_path.exists() or not db_path.is_dir():
            raise ValueError(f"Invalid database directory: {db_directory}")

        # Get MotherDuck connection
        md_con = get_motherduck_connection(token)

        # Process all DuckDB files in directory
        for db_file in db_path.glob("*.duckdb"):
            sync_database(db_file, md_con, result)

        result["success"] = len(result["errors"]) == 0
        if result["success"]:
            logger.info("Sync completed successfully")
        else:
            logger.warning("Sync completed with errors")

    except Exception as e:
        logger.critical(f"Critical sync failure: {str(e)}")
        result["errors"].append(f"Critical failure: {str(e)}")

    return result


if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Sync DuckDB databases to MotherDuck"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="data/processed",
        help="Directory containing DuckDB files to sync",
    )
    args = parser.parse_args()

    md_token = os.getenv("MOTHERDUCK_TOKEN")

    if not md_token:
        logger.critical("MOTHERDUCK_TOKEN not found in .env file")
        exit(1)

    logger.info(f"Starting MotherDuck sync for directory: {args.directory}")
    result = sync_to_motherduck(args.directory, md_token)

    if result["success"]:
        logger.info(
            f"Sync successful. Tables synced: {len(result['tables_synced'])}"
        )
    else:
        logger.error(f"Sync failed with {len(result['errors'])} errors")
```
