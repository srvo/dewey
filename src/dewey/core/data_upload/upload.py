import os
import sys
import argparse
from pathlib import Path
from dewey.utils import get_logger

def main():
    parser = argparse.ArgumentParser(description='Upload data files to MotherDuck')
    parser.add_argument('file_path', help='Path to file or directory to upload')
    parser.add_argument('--target_db', help='Target database name', default='dewey')
    parser.add_argument('--module', help='Module name for organization', default=None)
    parser.add_argument('--table', help='Target table name', default=None)
    parser.add_argument('--dedup_strategy', choices=['none', 'update', 'ignore'], default='none',
                       help='Deduplication strategy: none, update, or ignore')
    parser.add_argument('--recursive', action='store_true', help='Recursively search directories')
    args = parser.parse_args()

    # Set up logging
    log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
    logger = get_logger('data_upload', log_dir)

    try:
        from dewey.core.data_upload import DataUploader
        
        uploader = DataUploader(args.target_db)
        file_path = Path(args.file_path)
        
        if file_path.is_file():
            logger.info(f"Uploading file: {file_path}")
            uploader.upload_file(
                file_path,
                module=args.module,
                table_name=args.table,
                dedup_strategy=args.dedup_strategy
            )
        elif file_path.is_dir():
            logger.info(f"Uploading directory: {file_path}")
            uploader.upload_directory(
                file_path,
                module=args.module,
                recursive=args.recursive,
                dedup_strategy=args.dedup_strategy
            )
        else:
            logger.error(f"Path does not exist: {file_path}")
            sys.exit(1)
            
        logger.info("Upload completed successfully")
        
    except Exception as e:
        logger.error(f"Error during upload: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        if 'uploader' in locals():
            uploader.close()

if __name__ == '__main__':
    main() 