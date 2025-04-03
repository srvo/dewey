#!/usr/bin/env python
"""
    Schedule DB Sync Cron Job.

    This script sets up a cron job to run the database synchronization
    between MotherDuck and local DuckDB during off-hours.
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

from crontab import CronTab

# Ensure the project root is in the path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_cron_job(schedule="0 3 * * *", copy_first=True, incremental=True, user=None):
    """
    Set up a cron job to run the database sync script.

    Args:
    -----
        schedule: Cron schedule expression (default: 3 AM daily)
        copy_first: Whether to copy the database before syncing
        incremental: Whether to use incremental sync
        user: User for crontab (None for current user)

    Returns:
    --------
        True if successful, False otherwise

    """
    try:
        # Get absolute paths
        sync_script = script_dir / "direct_db_sync.py"
        log_file = project_root / "logs" / "db_sync.log"

        # Create log directory if it doesn't exist
        log_dir = log_file.parent
        if not log_dir.exists():
            log_dir.mkdir(parents=True)
            logger.info(f"Created log directory: {log_dir}")

        # Build command
        command = f"cd {project_root} && "
        command += "python scripts/direct_db_sync.py "
        command += "--verbose "
        command += "--mode incremental " if incremental else "--mode full "
        command += "--copy-first " if copy_first else ""
        command += f">> {log_file} 2>&1"

        # Create new cron tab
        cron = CronTab(user=user)

        # Check if the job already exists
        for job in cron:
            if "direct_db_sync.py" in str(job):
                logger.info("Removing existing db sync cron job")
                cron.remove(job)

        # Create new job
        job = cron.new(command=command)
        job.setall(schedule)
        job.set_comment("DeweyDB scheduled sync")

        # Write to crontab
        cron.write()

        logger.info(f"Cron job set up successfully with schedule: {schedule}")
        logger.info(f"Command: {command}")

        return True

    except Exception as e:
        logger.error(f"Error setting up cron job: {e}")
        return False


def test_sync_script():
    """
    Test if the sync script runs correctly.

    Returns:
    --------
        True if successful, False otherwise

    """
    try:
        sync_script = script_dir / "direct_db_sync.py"

        # Check if the script exists
        if not sync_script.exists():
            logger.error(f"Sync script not found: {sync_script}")
            return False

        # Make sure it's executable
        if not os.access(sync_script, os.X_OK):
            logger.info("Making sync script executable")
            sync_script.chmod(0o755)

        # Check if MOTHERDUCK_TOKEN is set
        if not os.environ.get("MOTHERDUCK_TOKEN"):
            logger.error("MOTHERDUCK_TOKEN environment variable not set")
            return False

        logger.info("Testing sync script with --help option")

        # Run the script with --help to verify it works
        process = subprocess.run(
            [sys.executable, str(sync_script), "--help"],
            capture_output=True,
            text=True,
        )

        if process.returncode != 0:
            logger.error(f"Script test failed with code {process.returncode}")
            logger.error(f"Error: {process.stderr}")
            return False

        logger.info("Sync script test passed")
        return True

    except Exception as e:
        logger.error(f"Error testing sync script: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Setup DB sync cron job")

    parser.add_argument(
        "--schedule",
        help="Cron schedule expression (default: 3 AM daily)",
        default="0 3 * * *",
    )

    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Don't make a copy of the database before syncing",
    )

    parser.add_argument(
        "--full", action="store_true", help="Use full sync instead of incremental"
    )

    parser.add_argument(
        "--user", help="User for crontab (default: current user)", default=None
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Test the sync script first
    if not test_sync_script():
        logger.error("Sync script test failed, cron job not set up")
        return 1

    # Set up cron job
    success = setup_cron_job(
        schedule=args.schedule,
        copy_first=not args.no_copy,
        incremental=not args.full,
        user=args.user,
    )

    if not success:
        logger.error("Failed to set up cron job")
        return 1

    logger.info("Cron job set up successfully")

    # Print instructions
    print("\nCron job has been set up to run the database sync.")
    print(f"Schedule: {args.schedule}")
    print("Mode: " + ("Full" if args.full else "Incremental"))
    print("Copy database first: " + ("No" if args.no_copy else "Yes"))
    print("\nTo view or modify the cron job, run: crontab -e")
    print("To view the logs, run: cat " + str(project_root / "logs" / "db_sync.log"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
