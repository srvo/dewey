# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

"""Email Service Module.

This module provides a robust email fetching service with:
- Periodic email fetching from Gmail API
- Database integration for storing emails
- Advanced error handling and retry mechanisms
- Graceful shutdown capabilities
- Comprehensive logging and monitoring

The service runs in a continuous loop, periodically fetching new emails and storing them
in the database. It handles various edge cases including:
- Network connectivity issues
- API rate limits
- Database connection problems
- Signal interrupts
"""
from __future__ import annotations

import logging
import signal
import time
from datetime import datetime, timedelta

from scripts.config import config
from scripts.db_connector import db
from scripts.email_operations import EmailFetcher
from scripts.log_config import setup_logging


class EmailService:
    """Core email service class for managing periodic email fetching.

    This service runs in a continuous loop, periodically fetching emails from Gmail API
    and storing them in the database. It includes:
    - Configurable fetch intervals
    - Graceful shutdown handling
    - Comprehensive error recovery
    - Database health monitoring

    Attributes
    ----------
        fetch_interval (float): Seconds between email fetch operations
        check_interval (float): Seconds between status checks
        running (bool): Service running state flag
        last_run (Optional[datetime]): Timestamp of last successful fetch
        email_fetcher (EmailFetcher): Instance of email fetching class

    """

    def __init__(
        self,
        db_path: str | None = None,
        checkpoint_file: str | None = None,
        fetch_interval: float = 900,
        check_interval: float = 1.0,
    ) -> None:
        """Initialize the email service with configuration and dependencies.

        Args:
        ----
            fetch_interval: Seconds between email fetch operations (default: 900 = 15 minutes)
            check_interval: Seconds between status checks (default: 1.0)

        Raises:
        ------
            RuntimeError: If database initialization or health check fails
            Exception: For any other initialization errors

        """
        self.fetch_interval = fetch_interval
        self.check_interval = check_interval
        self.running = False
        self.last_run: datetime | None = None

        # Initialize database connection
        try:
            db.initialize_database()
            if not db.health_check():
                msg = "Database health check failed"
                raise RuntimeError(msg)
        except Exception as e:
            logging.exception(f"Database initialization failed: {e!s}")
            raise

        # Initialize email fetcher
        self.email_fetcher = EmailFetcher(
            db_path=config.DB_URL,
            checkpoint_file=config.CHECKPOINT_FILE,
        )

        # Set up signal handlers
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

        setup_logging()
        logging.info("Email service initialized with database connection")

    def handle_signal(self, signum, frame) -> None:
        """Handle shutdown signals gracefully.

        Args:
        ----
            signum: Signal number received
            frame: Current stack frame (unused)

        """
        logging.warning(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False

    def fetch_cycle(self) -> None:
        """Execute a single email fetch cycle.

        This method:
        1. Initiates a new email fetch operation
        2. Processes fetched emails through the pipeline
        3. Updates last_run timestamp on success
        4. Logs errors without updating timestamp for retry

        Any exceptions during processing are caught and logged, but the service
        continues running to attempt recovery on next cycle.
        """
        try:
            logging.info("Starting email fetch cycle")
            self.email_fetcher.process_new_emails()
            self.last_run = datetime.now()
            logging.info("Email fetch cycle completed")
        except Exception as e:
            logging.error(f"Error during fetch cycle: {e!s}", exc_info=True)
            # Don't update last_run so we retry on next iteration

    def run(self) -> None:
        """Run the service in a continuous loop.

        The main service loop:
        1. Checks if enough time has passed since last fetch
        2. Executes fetch cycle when appropriate
        3. Sleeps briefly between checks
        4. Handles shutdown signals gracefully
        5. Logs all critical errors

        The loop continues until self.running is set to False, typically
        through a signal handler or fatal error.
        """
        self.running = True
        logging.info("Email service started")

        try:
            while self.running:
                current_time = datetime.now()

                # Check if we should run based on fetch interval
                if self.last_run is None or (current_time - self.last_run) >= timedelta(
                    seconds=self.fetch_interval,
                ):
                    self.fetch_cycle()

                # Sleep briefly while maintaining responsiveness
                time.sleep(self.check_interval)

        except Exception as e:
            logging.error(f"Fatal error in email service: {e!s}", exc_info=True)
        finally:
            logging.info("Email service shutting down")


def run_service(interval_minutes: int = 15) -> None:
    """Run the email service with default configuration.

    This is the main entry point for the email service. It:
    - Creates an EmailService instance
    - Starts the service loop
    - Handles any uncaught exceptions

    Args:
    ----
        interval_minutes: Minutes between email fetch operations (default: 15)

    """
    service = EmailService(
        fetch_interval=interval_minutes * 60,  # Convert minutes to seconds
    )
    service.run()


if __name__ == "__main__":
    # Main entry point when run as a script
    run_service()
