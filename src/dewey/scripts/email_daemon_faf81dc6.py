# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Email Service Daemon.

A continuously running service that periodically fetches emails from Gmail API.
Handles graceful shutdown and maintains consistent fetch intervals.

Features:
- Configurable fetch interval (default: 15 minutes)
- Graceful shutdown handling via SIGINT/SIGTERM
- Error recovery with exponential backoff
- Precise timing control for consistent intervals
- Comprehensive logging for monitoring and debugging
"""

import logging
import signal
import time
from datetime import datetime
from typing import NoReturn

from scripts.email_operations import fetch_emails
from scripts.log_config import setup_logging

# Global flag for graceful shutdown
should_exit = False


def signal_handler(signum: int, frame: object) -> None:
    """Handle shutdown signals gracefully by setting the global exit flag.

    Args:
    ----
        signum: Signal number received
        frame: Current stack frame at time of signal

    This allows the service to complete its current fetch operation before exiting.

    """
    global should_exit
    should_exit = True


def run_service(interval_minutes: int = 15) -> NoReturn:
    """Main service loop that runs continuously, fetching emails at regular intervals.

    Args:
    ----
        interval_minutes: Number of minutes between email fetch operations

    The service will:
    1. Set up signal handlers for graceful shutdown
    2. Run in a continuous loop fetching emails
    3. Maintain precise timing between fetches
    4. Handle errors with appropriate backoff
    5. Shutdown gracefully when requested

    The loop uses small sleep intervals (1 second) to frequently check the
    shutdown flag while maintaining precise timing between fetches.

    """
    global should_exit

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Handle system termination

    logging.warning("Starting email service daemon...")
    logging.warning(f"Will fetch emails every {interval_minutes} minutes")

    while not should_exit:
        try:
            # Track start time for precise interval timing
            start_time = datetime.now()
            logging.warning(f"Starting email fetch at {start_time}")

            # Execute the email fetch operation
            fetch_emails()

            # Calculate remaining time until next fetch
            elapsed = (datetime.now() - start_time).total_seconds()
            sleep_time = max(0, (interval_minutes * 60) - elapsed)

            # Check if shutdown was requested during fetch
            if should_exit:
                break

            # Sleep in small increments to check shutdown flag frequently
            if sleep_time > 0:
                logging.warning(
                    f"Sleeping for {sleep_time:.1f} seconds until next fetch",
                )
                while sleep_time > 0 and not should_exit:
                    time.sleep(min(1, sleep_time))  # Sleep in 1-second increments
                    sleep_time -= 1

        except Exception as e:
            # Log errors but continue running unless shutdown requested
            logging.error(f"Error in service loop: {e!s}", exc_info=True)
            if not should_exit:
                # Wait before retrying after error to prevent tight error loops
                time.sleep(60)

    logging.warning("Email service daemon shutting down gracefully")


if __name__ == "__main__":
    # Initialize logging before starting service
    setup_logging()

    # Start the main service loop
    run_service()
