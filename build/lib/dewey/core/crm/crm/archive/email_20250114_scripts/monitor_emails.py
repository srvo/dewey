"""Real-time email monitoring script.

This script provides a live dashboard showing:
- Total email counts
- Email status breakdowns
- Processing rates over time
- Latest email received timestamp

The monitoring runs in a continuous loop with configurable refresh intervals.
All data is pulled from the application's SQLite database.

Key Features:
- Real-time statistics display
- Cross-platform terminal clearing
- Graceful shutdown on Ctrl+C
- Type hints for better code clarity
- Context manager for database connections
"""

import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict

from scripts.config import Config


@contextmanager
def get_db_connection():
    """Context manager for database connections.

    Provides a managed SQLite database connection that automatically closes
    when the context is exited, even if an error occurs.

    Yields:
    ------
        sqlite3.Connection: An active database connection

    Example:
    -------
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")

    """
    conn = sqlite3.connect(Config.DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def get_stats() -> Dict[str, Any]:
    """Get current email statistics from the database.

    Queries multiple aspects of email processing status including:
    - Total email count
    - Counts by processing status
    - Recent activity (last hour)
    - Latest email timestamp

    Returns:
    -------
        Dict[str, Any]: Dictionary containing statistics with keys:
            - total_emails: Total number of emails in system
            - status_counts: Dict of counts by processing status
            - last_hour_count: Emails received in last hour
            - latest_email_date: Timestamp of most recent email

    Raises:
    ------
        sqlite3.Error: If database queries fail

    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM raw_emails")
        total_count = cursor.fetchone()[0]

        # Get counts by status
        cursor.execute(
            """
            SELECT email_status, COUNT(*)
            FROM raw_emails
            GROUP BY email_status
        """
        )
        status_counts = dict(cursor.fetchall())

        # Get counts for last hour
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM raw_emails
            WHERE created_at >= datetime('now', '-1 hour')
        """
        )
        last_hour_count = cursor.fetchone()[0]

        # Get latest email date
        cursor.execute(
            """
            SELECT received_date
            FROM raw_emails
            ORDER BY received_date DESC
            LIMIT 1
        """
        )
        latest_date = cursor.fetchone()[0] if cursor.fetchone() else None

        return {
            "total_emails": total_count,
            "status_counts": status_counts,
            "last_hour_count": last_hour_count,
            "latest_email_date": latest_date,
        }


def clear_screen():
    """Clear the terminal screen.

    Uses appropriate command for the operating system:
    - 'cls' for Windows
    - 'clear' for Unix-based systems (Linux, macOS)

    Note: This is a simple implementation and may not work in all terminal
    environments or IDEs.
    """
    os.system("cls" if os.name == "nt" else "clear")


def display_stats(stats: Dict[str, Any], start_time: datetime):
    """Display statistics in a formatted, readable way.

    Args:
    ----
        stats: Dictionary of statistics from get_stats()
        start_time: When monitoring started, for uptime calculation

    The display includes:
    - Current timestamp
    - Monitoring duration
    - Total email count
    - Recent activity
    - Latest email timestamp
    - Status breakdown
    - Usage instructions

    """
    clear_screen()
    print("\n=== Email Processing Statistics ===")
    print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Running for: {str(datetime.now() - start_time).split('.')[0]}")
    print("\nTotal Emails:", stats["total_emails"])
    print("Emails processed in last hour:", stats["last_hour_count"])
    if stats["latest_email_date"]:
        print("Latest email date:", stats["latest_email_date"])

    print("\nEmail Status Breakdown:")
    for status, count in stats["status_counts"].items():
        print(f"  {status}: {count}")

    print("\nPress Ctrl+C to stop monitoring")
    print("=" * 40)


def monitor_emails(refresh_interval: int = 5):
    """Monitor email processing in real-time.

    Runs in a continuous loop, displaying updated statistics at regular intervals.
    Handles keyboard interrupts gracefully for clean shutdown.

    Args:
    ----
        refresh_interval: How often to refresh stats (in seconds). Default is 5.

    Note:
    ----
        The refresh interval should be balanced between:
        - Frequent enough to show timely updates
        - Not so frequent as to overload the database
        - Considerate of terminal rendering performance

    Typical usage:
        $ python monitor_emails.py
        # Runs with default 5-second refresh

    """
    start_time = datetime.now()

    try:
        while True:
            stats = get_stats()
            display_stats(stats, start_time)
            time.sleep(refresh_interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")


if __name__ == "__main__":
    # Configure basic logging to suppress non-critical messages
    logging.basicConfig(level=logging.WARNING)

    # Start monitoring with default refresh interval
    monitor_emails()

    # Note: To run with custom refresh interval:
    # monitor_emails(refresh_interval=10)  # 10-second refresh
