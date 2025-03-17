import os
import sys
import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

from dewey.core.data_upload.motherduck_uploader import (
    upload_duckdb_file,
    upload_sqlite_file,
    upload_csv_file,
    upload_parquet_file,
    upload_json_file,
    get_motherduck_connection
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"upload_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Upload data files to MotherDuck')
    parser.add_argument('--input_dir', type=str, default='/Users/srvo/input_data', help='Directory containing input files')
    parser.add_argument('--target_db', type=str, default='dewey', help='Target MotherDuck database')
    parser.add_argument('--dedup_strategy', type=str, default='update', choices=['update', 'replace', 'skip', 'version'], 
                        help='Strategy for handling duplicate tables')
    parser.add_argument('--file_pattern', type=str, default='*', help='File pattern to match (e.g., *.duckdb)')
    parser.add_argument('--file', type=str, help='Direct file path to upload')
    parser.add_argument('--timeout_ms', type=int, default=60000, help='Timeout in milliseconds for database operations')
    parser.add_argument('--max_retries', type=int, default=3, help='Maximum number of retries for failed uploads')
    parser.add_argument('--retry_delay', type=int, default=5, help='Delay in seconds between retries')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Test connection to MotherDuck
    try:
        conn = get_motherduck_connection(args.target_db)
        logger.info(f"Successfully connected to MotherDuck database {args.target_db}")
        conn.execute("SELECT 1").fetchone()
    except Exception as e:
        logger.error(f"Failed to connect to MotherDuck: {str(e)}")
        return 1
    
    # Find files to process
    files = []
    
    # If a direct file path is provided, use that
    if args.file:
        if os.path.isfile(args.file):
            files = [Path(args.file)]
        else:
            logger.error(f"File not found: {args.file}")
            return 1
    else:
        # Validate input directory
        if not os.path.isdir(args.input_dir):
            logger.error(f"Input directory {args.input_dir} does not exist")
            return 1
            
        # Find all files in the input directory matching the pattern
        input_path = Path(args.input_dir)
        try:
            files = list(input_path.glob(args.file_pattern))
        except NotImplementedError:
            # Handle absolute paths
            logger.info(f"Using direct file matching for {args.file_pattern}")
            if '*' in args.file_pattern:
                import glob
                files = [Path(f) for f in glob.glob(os.path.join(args.input_dir, args.file_pattern))]
            else:
                file_path = os.path.join(args.input_dir, args.file_pattern)
                if os.path.exists(file_path):
                    files = [Path(file_path)]
    
    if not files:
        logger.warning(f"No files found matching pattern {args.file_pattern} in {args.input_dir}")
        return 0
    
    logger.info(f"Found {len(files)} files to process")
    for file in files:
        logger.debug(f"Found file: {file}")
    
    # Process each file
    success_count = 0
    failure_count = 0
    skipped_count = 0
    
    for file_path in files:
        file_path_str = str(file_path)
        logger.info(f"Processing file: {file_path_str}")
        
        # Determine file type and call appropriate upload function
        file_ext = file_path.suffix.lower()
        
        # Skip directories and non-data files
        if file_path.is_dir() or file_ext not in ['.duckdb', '.sqlite', '.db', '.csv', '.parquet', '.json']:
            logger.info(f"Skipping {file_path_str} (not a supported data file)")
            skipped_count += 1
            continue
        
        # Try to upload the file with retries
        success = False
        retries = 0
        
        while not success and retries <= args.max_retries:
            if retries > 0:
                logger.info(f"Retry attempt {retries} for {file_path_str}")
                time.sleep(args.retry_delay)
            
            try:
                if file_ext == '.duckdb':
                    logger.debug(f"Uploading DuckDB file: {file_path_str}")
                    success = upload_duckdb_file(file_path_str, args.target_db, args.dedup_strategy)
                elif file_ext in ['.sqlite', '.db']:
                    logger.debug(f"Uploading SQLite file: {file_path_str}")
                    success = upload_sqlite_file(file_path_str, args.target_db, args.dedup_strategy)
                elif file_ext == '.csv':
                    logger.debug(f"Uploading CSV file: {file_path_str}")
                    success = upload_csv_file(file_path_str, args.target_db, args.dedup_strategy)
                elif file_ext == '.parquet':
                    logger.debug(f"Uploading Parquet file: {file_path_str}")
                    success = upload_parquet_file(file_path_str, args.target_db, args.dedup_strategy)
                elif file_ext == '.json':
                    logger.debug(f"Uploading JSON file: {file_path_str}")
                    success = upload_json_file(file_path_str, args.target_db, args.dedup_strategy)
                
                if success:
                    logger.info(f"Successfully uploaded {file_path_str}")
                    success_count += 1
                    break
                else:
                    logger.warning(f"Upload failed for {file_path_str}")
                    retries += 1
            except Exception as e:
                logger.error(f"Error processing {file_path_str}: {str(e)}")
                retries += 1
        
        if not success:
            logger.error(f"Failed to upload {file_path_str} after {args.max_retries} retries")
            failure_count += 1
    
    # Summary
    logger.info(f"Upload process completed")
    logger.info(f"Total files: {len(files)}")
    logger.info(f"Successfully uploaded: {success_count}")
    logger.info(f"Failed: {failure_count}")
    logger.info(f"Skipped: {skipped_count}")
    
    return 0 if failure_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 