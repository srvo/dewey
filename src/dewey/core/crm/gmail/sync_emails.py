#!/usr/bin/env python3
"""Gmail Email Sync Script
======================

This script handles both consistency checking and email syncing for Gmail.
It can run in either historical or incremental mode and includes proper
error handling and logging.

Usage:
    # Run incremental sync (default)
    python sync_emails.py

    # Run historical sync
    python sync_emails.py --historical --days 30

    # Run consistency check only
    python sync_emails.py --check-only --days 7
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dewey.core.crm.gmail.gmail_sync_manager import GmailSyncManager
from dewey.core.db.errors import DatabaseError, SyncError

# Configure logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"gmail_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("gmail_sync")

def main():
    """Run the Gmail sync process."""
    parser = argparse.ArgumentParser(
        description="Sync emails from Gmail with consistency checking"
    )
    parser.add_argument(
        "--historical",
        action="store_true",
        help="Perform a historical sync instead of incremental"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only perform consistency check without syncing"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7 if not "--historical" in sys.argv else 30,
        help="Number of days to look back"
    )
    parser.add_argument(
        "--max-emails",
        type=int,
        help="Maximum number of emails to sync"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of emails to process in each batch"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="~/dewey_emails.duckdb",
        help="Path to local database file"
    )
    parser.add_argument(
        "--motherduck-db",
        type=str,
        default="dewey_emails",
        help="MotherDuck database name"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize sync manager
        manager = GmailSyncManager(
            db_path=args.db_path,
            motherduck_db=args.motherduck_db,
            batch_size=args.batch_size
        )
        
        # Check consistency first
        logger.info("Checking email consistency...")
        stats = manager.check_consistency(days_back=args.days)
        
        logger.info("Consistency check results:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
            
        # If check-only mode, stop here
        if args.check_only:
            if stats['needs_sync'] > 0:
                logger.warning(
                    f"Found {stats['needs_sync']} emails that need synchronization. "
                    "Run without --check-only to sync them."
                )
            return
            
        # Perform sync if needed
        if stats['needs_sync'] > 0 or args.historical:
            logger.info(
                f"Starting {'historical' if args.historical else 'incremental'} sync..."
            )
            
            sync_stats = manager.sync_emails(
                historical=args.historical,
                days_back=args.days,
                max_emails=args.max_emails
            )
            
            logger.info("Sync completed:")
            for key, value in sync_stats.items():
                logger.info(f"  {key}: {value}")
        else:
            logger.info("No emails need synchronization")
            
    except (DatabaseError, SyncError) as e:
        logger.error(f"Sync failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 