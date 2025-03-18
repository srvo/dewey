#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path
from dewey.utils import get_logger
from dewey.core.data_upload import DataUploader

def main():
    parser = argparse.ArgumentParser(description='Batch upload data files to MotherDuck')
    parser.add_argument('input_dir', help='Directory containing input files')
    parser.add_argument('--target_db', help='Target database name', default='dewey')
    parser.add_argument('--module', help='Module name for organization', default=None)
    parser.add_argument('--pattern', help='File pattern to match (e.g. *.csv)', default='*')
    parser.add_argument('--dedup_strategy', choices=['none', 'update', 'ignore'], default='none',
                       help='Deduplication strategy: none, update, or ignore')
    parser.add_argument('--recursive', action='store_true', help='Recursively search directories')
    args = parser.parse_args()

    # Set up logging
    log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
    logger = get_logger('batch_upload', log_dir)

    try:
        uploader = DataUploader(args.target_db)
        input_dir = Path(args.input_dir)
        
        if not input_dir.is_dir():
            logger.error(f"Input directory does not exist: {input_dir}")
            sys.exit(1)
            
        logger.info(f"Starting batch upload from {input_dir}")
        logger.info(f"File pattern: {args.pattern}")
        logger.info(f"Module: {args.module}")
        logger.info(f"Deduplication strategy: {args.dedup_strategy}")
        
        uploader.upload_directory(
            input_dir,
            pattern=args.pattern,
            module=args.module,
            recursive=args.recursive,
            dedup_strategy=args.dedup_strategy
        )
        
        logger.info("Batch upload completed successfully")
        
    except Exception as e:
        logger.error(f"Error during batch upload: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        if 'uploader' in locals():
            uploader.close()

if __name__ == '__main__':
    main() 