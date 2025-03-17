#!/usr/bin/env python3
"""
Database Schema Checker
======================

This script checks the schema of an existing DuckDB database file.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dewey.core.db import check_database_schema

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("db_checker")


def main():
    """Check the schema of an existing database."""
    parser = argparse.ArgumentParser(description="Check the schema of a DuckDB database")
    parser.add_argument("--db-path", type=str, required=True, help="Path to the database file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.db_path):
        logger.error(f"Database file not found: {args.db_path}")
        sys.exit(1)
    
    logger.info(f"Checking schema of database: {args.db_path}")
    
    try:
        schema = check_database_schema(args.db_path)
        
        if not schema:
            logger.warning("No tables found in the database")
            sys.exit(0)
        
        logger.info(f"Found {len(schema)} tables in the database:")
        
        for table_name, columns in schema.items():
            logger.info(f"\nTable: {table_name}")
            logger.info("Columns:")
            for column in columns:
                logger.info(f"  - {column}")
        
    except Exception as e:
        logger.error(f"Error checking database schema: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 