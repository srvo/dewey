#!/usr/bin/env python3

import os
import sys
import argparse
from pathlib import Path
from dewey.utils import get_logger


def split_journal(input_file: str, output_dir: str) -> None:
    """Split a journal file into monthly files."""
    logger = get_logger('journal_splitter')
    
    try:
        input_path = Path(input_file)
        output_path = Path(output_dir)
        
        if not input_path.exists():
            logger.error(f"Input file does not exist: {input_path}")
            sys.exit(1)
            
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Splitting journal file: {input_path}")
        logger.info(f"Output directory: {output_path}")
        
        # Read input file and split by month
        current_month = None
        current_file = None
        
        with open(input_path) as f:
            for line in f:
                # Try to parse date from transaction line
                if line.strip() and not line.startswith(';') and not line.startswith(' '):
                    try:
                        date = line.split()[0]
                        year_month = date[:7]  # YYYY-MM
                        
                        if year_month != current_month:
                            # Close current file if open
                            if current_file:
                                current_file.close()
                            
                            # Open new file for month
                            output_file = output_path / f"{year_month}.journal"
                            current_file = open(output_file, 'w')
                            current_month = year_month
                            
                            logger.info(f"Created file for {year_month}")
                    except Exception as e:
                        logger.warning(f"Could not parse date from line: {line.strip()}")
                        continue
                
                # Write line to current file
                if current_file:
                    current_file.write(line)
        
        # Close final file
        if current_file:
            current_file.close()
        
        logger.info("Journal splitting completed successfully")
        
    except Exception as e:
        logger.error(f"Error splitting journal: {str(e)}", exc_info=True)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Split a journal file into monthly files')
    parser.add_argument('input_file', help='Input journal file')
    parser.add_argument('output_dir', help='Output directory for split files')
    args = parser.parse_args()

    # Set up logging
    log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
    logger = get_logger('journal_splitter', log_dir)
    
    split_journal(args.input_file, args.output_dir)


if __name__ == '__main__':
    main()
