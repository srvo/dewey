from __future__ import annotations

import json
import logging
import os
import pickle
import sqlite3
import sys
from datetime import datetime
from typing import Any

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configure logging to output to both console and file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("gmail_label_learner.log")],
)

# OAuth2 scopes required for Gmail API access
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def setup_database() -> sqlite3.Connection:
    """Initialize and configure the SQLite database for storing email corrections.

    Creates two main tables:
    1. email_corrections: Stores individual email correction data
    2. priority_patterns: Stores learned patterns from corrections

    Returns:
        sqlite3.Connection: Active database connection

    """
    conn = sqlite3.connect("email_corrections.db")
    c = conn.cursor()

    # Create email_corrections table to store individual corrections
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS email_corrections (
            message_id TEXT PRIMARY KEY,
            subject TEXT,
            original_priority INTEGER,
            corrected_priority INTEGER,
            confidence REAL,
            timestamp DATETIME,
            learned BOOLEAN DEFAULT FALSE
        )
    """,
    )

    # Create priority_patterns table to store learned patterns
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS priority_patterns (
            pattern TEXT,
            priority INTEGER,
            confidence REAL,
            count INTEGER,
            last_updated DATETIME
        )
    """,
    )

    conn.commit()
    return conn


def authenticate_gmail() -> Any:
    """Authenticate with Gmail API using OAuth2 credentials.

    Handles both initial authentication and token refresh. Stores credentials
    in a pickle file for future use.

    Returns:
        Any: Authenticated Gmail API service object

    Raises:
        SystemExit: If authentication fails completely

    """
    token_pickle = "scripts/token.pickle"
    credentials_path = "scripts/credentials.json"

    try:
        creds = load_credentials(token_pickle)

        if not creds or not creds.valid:
            creds = refresh_or_new_credentials(creds, credentials_path, token_pickle)

        return build("gmail", "v1", credentials=creds)

    except Exception as e:
        logging.exception(f"Authentication failed: {e!s}")
        sys.exit(1)


def load_credentials(token_pickle: str) -> Any:
    """Load credentials from pickle file if it exists."""
    if os.path.exists(token_pickle):
        with open(token_pickle, "rb") as token:
            return pickle.load(token)
    return None


def refresh_or_new_credentials(
    creds: Any,
    credentials_path: str,
    token_pickle: str,
) -> Any:
    """Refresh or create new credentials."""
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(token_pickle, "wb") as token:
        pickle.dump(creds, token)
    return creds


def get_priority_from_labels(labels: list[str]) -> int | None:
    """Extract priority level from Gmail labels.

    Args:
        labels (List[str]): List of Gmail label IDs/names

    Returns:
        Optional[int]: Priority level (0-5) if found, None otherwise

    """
    # Map of Gmail priority labels to numerical values
    priority_map = {
        "Priority/Marketing": 0,  # Lowest priority
        "Priority/Very Low": 1,
        "Priority/Low": 2,
        "Priority/Medium": 3,
        "Priority/High": 4,
        "Priority/Critical": 5,  # Highest priority
    }

    # Search through labels for priority indicators
    for label in labels:
        for priority_label, priority in priority_map.items():
            if priority_label in label:
                return priority
    return None


def load_edge_cases() -> list[dict]:
    """Load previously processed emails from edge_cases.json file.

    The file contains JSON objects, one per line, representing emails
    that required manual priority adjustments.

    Returns:
        List[dict]: List of dictionaries containing edge case data

    Note:
        Returns empty list if file doesn't exist or is empty

    """
    try:
        with open("scripts/edge_cases.json") as f:
            # Parse each line as separate JSON object
            return [json.loads(line) for line in f if line.strip()]
    except Exception as e:
        logging.exception(f"Error loading edge cases: {e!s}")
        return []


def find_corrections(
    service: Any,
    edge_cases: list[dict],
    conn: sqlite3.Connection,
) -> None:
    """Identify and record manual priority corrections in Gmail.

    Compares original priority assignments with current labels to detect
    manual corrections made by users.

    Args:
        service (Any): Authenticated Gmail API service
        edge_cases (List[dict]): List of previously processed emails
        conn (sqlite3.Connection): Database connection

    Note:
        Errors are logged but don't interrupt processing of other emails

    """
    c = conn.cursor()

    for case in edge_cases:
        try:
            # Fetch current message metadata from Gmail
            msg = fetch_message_metadata(
                service,
                case.get("message_id"),
                case.get("subject"),
            )

            # Get current and original priorities
            current_priority = get_priority_from_labels(msg.get("labelIds", []))
            original_priority = case.get("priority")

            # If priorities differ, record the correction
            if current_priority is not None and current_priority != original_priority:
                record_correction(c, case, original_priority, current_priority)
                log_correction(case.get("subject"), original_priority, current_priority)

        except Exception as e:
            logging.exception(f"Error processing message: {e!s}")
            continue

    # Commit all changes to database
    conn.commit()


def fetch_message_metadata(service: Any, message_id: str, subject: str) -> dict:
    """Fetch message metadata from Gmail API."""
    try:
        return (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=["subject"],
            )
            .execute()
        )
    except Exception as e:
        logging.exception(f"Error fetching message metadata for '{subject}': {e}")
        raise


def record_correction(
    c: sqlite3.Cursor,
    case: dict,
    original_priority: int,
    corrected_priority: int,
) -> None:
    """Record a priority correction in the database."""
    c.execute(
        """
        INSERT OR REPLACE INTO email_corrections
        (message_id, subject, original_priority, corrected_priority,
         confidence, timestamp, learned)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            case.get("message_id"),
            case.get("subject"),
            original_priority,
            corrected_priority,
            case.get("confidence", 0.0),
            datetime.now().isoformat(),
            False,
        ),
    )


def log_correction(
    subject: str,
    original_priority: int,
    corrected_priority: int,
) -> None:
    """Log a priority correction."""
    logging.info(
        f"Found correction for '{subject}': "
        f"{original_priority} -> {corrected_priority}",
    )


def analyze_patterns(conn: sqlite3.Connection) -> None:
    """Analyze corrections to identify and learn priority patterns.

    Processes unlearned corrections to identify recurring patterns in
    subject lines that correlate with specific priority levels.

    Args:
        conn (sqlite3.Connection): Database connection

    Note:
        Requires at least 2 occurrences of a pattern before learning

    """
    c = conn.cursor()

    # Get unlearned corrections that appear at least twice
    c.execute(
        """
        SELECT subject, corrected_priority, COUNT(*) as count
        FROM email_corrections
        WHERE learned = FALSE
        GROUP BY subject, corrected_priority
        HAVING count >= 2
    """,
    )

    patterns = c.fetchall()

    for subject, priority, count in patterns:
        # Calculate confidence score (simple ratio of occurrences)
        confidence = count / (count + 1)

        # Update priority patterns table
        update_priority_patterns(c, subject, priority, confidence, count)

        # Mark these corrections as processed
        mark_corrections_as_learned(c, subject, priority)

        log_learned_pattern(subject, priority, confidence, count)

    # Commit all database changes
    conn.commit()


def update_priority_patterns(
    c: sqlite3.Cursor,
    subject: str,
    priority: int,
    confidence: float,
    count: int,
) -> None:
    """Update the priority patterns table with a new or updated pattern."""
    c.execute(
        """
        INSERT OR REPLACE INTO priority_patterns
        (pattern, priority, confidence, count, last_updated)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            subject,
            priority,
            confidence,
            count,
            datetime.now().isoformat(),
        ),
    )


def mark_corrections_as_learned(c: sqlite3.Cursor, subject: str, priority: int) -> None:
    """Mark corrections with the given subject and priority as learned."""
    c.execute(
        """
        UPDATE email_corrections
        SET learned = TRUE
        WHERE subject = ? AND corrected_priority = ?
    """,
        (subject, priority),
    )


def log_learned_pattern(
    subject: str,
    priority: int,
    confidence: float,
    count: int,
) -> None:
    """Log that a pattern has been learned."""
    logging.info(
        f"Learned pattern: '{subject}' -> Priority {priority} "
        f"(confidence: {confidence:.2f}, count: {count})",
    )


def main() -> None:
    """Main execution function for Gmail label learning system.

    Orchestrates the entire process:
    1. Sets up database
    2. Authenticates with Gmail
    3. Loads edge cases
    4. Finds corrections
    5. Analyzes patterns
    6. Reports summary statistics

    Note:
        Ensures database connection is properly closed even if errors occur

    """
    # Initialize database and services
    conn = setup_database()
    service = authenticate_gmail()
    edge_cases = load_edge_cases()

    try:
        # Process corrections and analyze patterns
        find_corrections(service, edge_cases, conn)
        analyze_patterns(conn)

        # Generate and log summary statistics
        pending, patterns = generate_summary_statistics(conn)

        logging.info("\nSummary:")
        logging.info(f"Pending corrections: {pending}")
        logging.info(f"Learned patterns: {patterns}")

    finally:
        # Ensure database connection is closed
        conn.close()


def generate_summary_statistics(conn: sqlite3.Connection) -> tuple[int, int]:
    """Generate summary statistics for pending corrections and learned patterns."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM email_corrections WHERE learned = FALSE")
    pending = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM priority_patterns")
    patterns = c.fetchone()[0]

    return pending, patterns


if __name__ == "__main__":
    main()
