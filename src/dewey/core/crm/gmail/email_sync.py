#!/usr/bin/env python3
"""
Email Sync Module

This module handles synchronization of email data between local DuckDB and MotherDuck.
It uses the MotherDuckEngine for database operations and adds email-specific functionality.
"""

import os
import sys
import argparse
from pathlib import Path
from dewey.utils import get_logger
from dewey.core.engines import MotherDuckEngine

def main():
    parser = argparse.ArgumentParser(description='Sync Gmail data to MotherDuck')
    parser.add_argument('--target_db', help='Target database name', default='dewey')
    parser.add_argument('--dedup_strategy', choices=['none', 'update', 'ignore'], default='update',
                       help='Deduplication strategy: none, update, or ignore')
    args = parser.parse_args()

    # Set up logging
    log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
    logger = get_logger('email_sync', log_dir)

    try:
        engine = MotherDuckEngine(args.target_db)
        
        logger.info("Starting Gmail sync")
        engine.sync_gmail(dedup_strategy=args.dedup_strategy)
        logger.info("Gmail sync completed successfully")
        
    except Exception as e:
        logger.error(f"Error during Gmail sync: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        if 'engine' in locals():
            engine.close()

if __name__ == '__main__':
    main() 