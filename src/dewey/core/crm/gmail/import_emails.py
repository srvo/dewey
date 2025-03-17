#!/usr/bin/env python3
"""
Gmail Email Import Script
========================

This script imports emails from Gmail using gcloud CLI authentication.
It can be run as a scheduled task (cron job) to keep the CRM database updated.

Setup:
1. Authenticate with gcloud CLI:
   $ gcloud auth application-default login

2. Run the script:
   $ python import_emails.py --days 7 --max 1000

3. Set up a cron job to run it regularly:
   $ crontab -e
   0 */4 * * * cd /path/to/dewey && python src/dewey/core/crm/gmail/import_emails.py --days 1
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

from dewey.core.crm.gmail.gmail_service import GmailService

# Configure logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"gmail_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("gmail_import")


def main():
    """Run the Gmail import process."""
    parser = argparse.ArgumentParser(description="Import emails from Gmail")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    parser.add_argument("--max", type=int, default=1000, help="Maximum number of emails to import")
    parser.add_argument("--user", type=str, help="User email to impersonate (for domain-wide delegation)")
    parser.add_argument("--checkpoint", type=str, default="gmail_checkpoint.json", 
                        help="Checkpoint file path")
    parser.add_argument("--db", type=str, default="crm.duckdb", help="Database file name")
    parser.add_argument("--data-dir", type=str, help="Data directory for database files")
    parser.add_argument("--existing-db", type=str, help="Path to an existing database file to use")
    
    args = parser.parse_args()
    
    logger.info(f"Starting Gmail import: looking back {args.days} days, max {args.max} emails")
    
    try:
        # Initialize the Gmail service
        service = GmailService(
            user_email=args.user,
            checkpoint_file=args.checkpoint,
            database_name=args.db,
            data_dir=args.data_dir,
            existing_db_path=args.existing_db
        )
        
        # Import emails
        imported = service.import_emails(
            days=args.days,
            max_emails=args.max
        )
        
        logger.info(f"Gmail import completed successfully. Imported {imported} emails.")
        
    except Exception as e:
        logger.error(f"Gmail import failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 