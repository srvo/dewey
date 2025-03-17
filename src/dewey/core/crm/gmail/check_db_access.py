#!/usr/bin/env python3
"""
Database Access Checker
======================

This script checks if a DuckDB database file exists and is accessible.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import duckdb

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("db_checker")


def check_db_access(db_path: str) -> bool:
    """Check if a database file exists and is accessible.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        True if the database is accessible, False otherwise
    """
    # Check if the file exists
    if not os.path.exists(db_path):
        logger.info(f"Database file does not exist: {db_path}")
        
        # Check if the directory exists
        db_dir = os.path.dirname(os.path.abspath(db_path))
        if not os.path.exists(db_dir):
            logger.info(f"Directory does not exist: {db_dir}")
            try:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Created directory: {db_dir}")
            except Exception as e:
                logger.error(f"Error creating directory: {e}")
                return False
        
        # Try to create the database file
        try:
            conn = duckdb.connect(db_path)
            conn.close()
            logger.info(f"Successfully created database file: {db_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating database file: {e}")
            return False
    
    # Check if the file is accessible
    try:
        conn = duckdb.connect(db_path)
        
        # Check if we can execute a query
        conn.execute("SELECT 1")
        
        # Get the list of tables
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        logger.info(f"Database has {len(tables)} tables:")
        for table in tables:
            logger.info(f"  - {table[0]}")
        
        conn.close()
        logger.info(f"Database file is accessible: {db_path}")
        return True
    except Exception as e:
        logger.error(f"Error accessing database file: {e}")
        return False


def main():
    """Check if a database file exists and is accessible."""
    parser = argparse.ArgumentParser(description="Check if a DuckDB database file exists and is accessible")
    parser.add_argument("--db-path", type=str, required=True, help="Path to the database file")
    
    args = parser.parse_args()
    
    # Expand the database path
    db_path = os.path.expanduser(args.db_path)
    
    logger.info(f"Checking database access: {db_path}")
    
    if check_db_access(db_path):
        logger.info("Database is accessible")
    else:
        logger.error("Database is not accessible")
        sys.exit(1)


if __name__ == "__main__":
    main() 