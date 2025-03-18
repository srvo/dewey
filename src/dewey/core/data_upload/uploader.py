#!/usr/bin/env python3
"""
Data Uploader Module

This module provides functionality for uploading various data files to MotherDuck,
organizing them according to the core modules structure.
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from ..engines import MotherDuckEngine

# Configure logging
logger = logging.getLogger(__name__)

class DataUploader:
    """Manages data uploads to MotherDuck."""
    
    def __init__(
        self,
        database_name: str = "dewey",
        token: Optional[str] = None,
        local_db_path: Optional[str] = None,
    ):
        """Initialize the data uploader.
        
        Args:
            database_name: Name of the database to connect to
            token: MotherDuck token (if None, will try to get from env)
            local_db_path: Path to local DuckDB database (if None, will use default)
        """
        self.engine = MotherDuckEngine(
            database_name=database_name,
            token=token,
            local_db_path=local_db_path,
        )
    
    def upload_file(
        self,
        file_path: str,
        module: Optional[str] = None,
        table_name: Optional[str] = None,
        dedup_strategy: str = "update",
    ) -> bool:
        """Upload a file to MotherDuck.
        
        Args:
            file_path: Path to the file to upload
            module: Module to organize the data under (auto-detected if None)
            table_name: Name for the table (auto-generated if None)
            dedup_strategy: How to handle duplicates
            
        Returns:
            bool: True if upload was successful
        """
        return self.engine.upload_file(
            file_path=file_path,
            module=module,
            table_name=table_name,
            dedup_strategy=dedup_strategy,
        )
    
    def upload_directory(
        self,
        directory: str,
        recursive: bool = True,
        dedup_strategy: str = "update",
    ) -> Tuple[int, int]:
        """Upload all supported files in a directory.
        
        Args:
            directory: Path to directory
            recursive: Whether to search subdirectories
            dedup_strategy: How to handle duplicates
            
        Returns:
            Tuple of (success_count, total_count)
        """
        return self.engine.upload_directory(
            directory=directory,
            recursive=recursive,
            dedup_strategy=dedup_strategy,
        )
    
    def close(self):
        """Close database connections."""
        self.engine.close()

def main():
    """Command line interface for data upload."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload data to MotherDuck")
    parser.add_argument(
        "--file",
        help="Path to the file to upload",
    )
    parser.add_argument(
        "--dir",
        help="Path to the directory containing files to upload",
    )
    parser.add_argument(
        "--database",
        default="dewey",
        help="Name of the target database",
    )
    parser.add_argument(
        "--module",
        help="Module to organize the data under (auto-detected if not specified)",
    )
    parser.add_argument(
        "--table",
        help="Name for the table (auto-generated if not specified)",
    )
    parser.add_argument(
        "--dedup-strategy",
        choices=["update", "skip", "replace", "version"],
        default="update",
        help="Strategy for handling duplicates",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively search subdirectories when uploading a directory",
    )
    
    args = parser.parse_args()
    
    if not args.file and not args.dir:
        parser.error("Either --file or --dir must be specified")
    
    if args.file and args.dir:
        parser.error("Only one of --file or --dir can be specified")
    
    # Initialize uploader
    uploader = DataUploader(args.database)
    
    try:
        if args.dir:
            # Upload all files in directory
            logger.info(f"Uploading files from directory {args.dir}")
            success_count, total_count = uploader.upload_directory(
                directory=args.dir,
                recursive=args.recursive,
                dedup_strategy=args.dedup_strategy,
            )
            logger.info(f"Uploaded {success_count} of {total_count} files successfully")
            return 0 if success_count == total_count else 1
        else:
            # Upload single file
            logger.info(f"Uploading file {args.file}")
            success = uploader.upload_file(
                file_path=args.file,
                module=args.module,
                table_name=args.table,
                dedup_strategy=args.dedup_strategy,
            )
            if success:
                logger.info(f"Successfully uploaded {args.file}")
                return 0
            else:
                logger.error(f"Failed to upload {args.file}")
                return 1
    finally:
        uploader.close()

if __name__ == "__main__":
    main() 