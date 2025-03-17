#!/usr/bin/env python3
import os
import sys
import argparse
import logging
import time
import subprocess
from datetime import datetime
from pathlib import Path

# Configure logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"batch_upload_log_{timestamp}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def find_files(input_dir, file_type, exclude_dirs=None):
    """Find files of a specific type in the input directory."""
    if exclude_dirs is None:
        exclude_dirs = []
    
    exclude_dirs = [os.path.normpath(d) for d in exclude_dirs]
    
    files = []
    for root, dirs, filenames in os.walk(input_dir):
        # Skip excluded directories
        if any(os.path.normpath(os.path.join(input_dir, d)) in os.path.normpath(root) for d in exclude_dirs):
            continue
            
        for filename in filenames:
            if filename.lower().endswith(f".{file_type.lower()}"):
                files.append(os.path.join(root, filename))
    return files

def upload_files_in_batches(files, target_db, dedup_strategy, batch_size):
    """Upload files in batches."""
    total_files = len(files)
    successful_uploads = 0
    failed_uploads = 0
    skipped_files = 0
    
    for i in range(0, total_files, batch_size):
        batch = files[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(total_files + batch_size - 1)//batch_size} ({len(batch)} files)")
        
        for file_path in batch:
            logger.info(f"Uploading file: {file_path}")
            try:
                # Determine file type
                file_ext = os.path.splitext(file_path)[1].lower()[1:]  # Remove the dot
                
                # Create a subprocess command to run the upload script
                cmd = [
                    "python", 
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload.py"),
                    "--file", file_path,
                    "--target_db", target_db,
                    "--dedup_strategy", dedup_strategy
                ]
                
                # Run the upload process
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"Successfully uploaded {file_path}")
                    successful_uploads += 1
                else:
                    logger.error(f"Failed to upload {file_path}")
                    logger.error(f"Error: {result.stderr}")
                    failed_uploads += 1
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                failed_uploads += 1
            
            logger.debug("")  # Add a blank line for readability
    
    return successful_uploads, failed_uploads, skipped_files

def main():
    parser = argparse.ArgumentParser(description="Batch upload files to MotherDuck")
    parser.add_argument("--input_dir", default="/Users/srvo/input_data", help="Directory containing files to upload")
    parser.add_argument("--target_db", default="dewey", help="Target MotherDuck database")
    parser.add_argument("--dedup_strategy", choices=["update", "replace", "skip", "version"], default="replace", help="Strategy for handling duplicate tables")
    parser.add_argument("--batch_size", type=int, default=5, help="Number of files to process in each batch")
    parser.add_argument("--file_types", default="duckdb,sqlite,csv,json,parquet", help="Comma-separated list of file types to process")
    parser.add_argument("--max_files", type=int, default=None, help="Maximum number of files to process per file type")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--exclude_dirs", default="", help="Comma-separated list of directories to exclude")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Validate input directory
    if not os.path.isdir(args.input_dir):
        logger.error(f"Input directory {args.input_dir} does not exist")
        return 1
    
    # Process exclude_dirs
    exclude_dirs = [d.strip() for d in args.exclude_dirs.split(",")] if args.exclude_dirs else []
    
    # Process each file type
    file_types = [ft.strip() for ft in args.file_types.split(",")]
    total_successful = 0
    total_failed = 0
    
    for file_type in file_types:
        logger.info(f"Processing {file_type} files")
        files = find_files(args.input_dir, file_type, exclude_dirs)
        
        if args.max_files is not None and len(files) > args.max_files:
            logger.info(f"Limiting to {args.max_files} {file_type} files")
            files = files[:args.max_files]
        
        logger.info(f"Found {len(files)} {file_type} files to process")
        
        if files:
            successful, failed, skipped = upload_files_in_batches(
                files, args.target_db, args.dedup_strategy, args.batch_size
            )
            
            total_successful += successful
            total_failed += failed
            
            logger.info(f"Batch upload completed for {file_type} files")
            logger.info(f"Total files: {len(files)}")
            logger.info(f"Successfully uploaded: {successful}")
            logger.info(f"Failed: {failed}")
            logger.info(f"Skipped: {skipped}")
    
    logger.info("All file types processed")
    logger.info(f"Total successfully uploaded: {total_successful}")
    logger.info(f"Total failed: {total_failed}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 