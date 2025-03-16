# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025
from __future__ import annotations

import json
import logging
import os
import pickle
import sqlite3
import sys
from datetime import datetime

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

    Returns
    -------
        sqlite3.Connection: Active database connection

    """
    conn = sqlite3.connect("email_corrections.db")
    c = conn.cursor()

    # Create email_corrections table to store individual corrections
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS email_corrections (
            message_id TEXT PRIMARY KEY,        -- Unique email message ID
            subject TEXT,                       -- Email subject line
            original_priority INTEGER,          -- Initial priority assigned
            corrected_priority INTEGER,         -- Manually corrected priority
            confidence REAL,                    -- Confidence score of original assignment
            timestamp DATETIME,                 -- When correction was recorded
            learned BOOLEAN DEFAULT FALSE       -- Whether pattern has been processed
        )
    """,
    )

    # Create priority_patterns table to store learned patterns
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS priority_patterns (
            pattern TEXT,                       -- Text pattern (e.g., subject keywords)
            priority INTEGER,                   -- Associated priority level
            confidence REAL,                    -- Confidence in this pattern
            count INTEGER,                      -- Number of occurrences observed
            last_updated DATETIME               -- Last time pattern was updated
        )
    """,
    )

    conn.commit()
    return conn


def authenticate_gmail() -> any:
    """Authenticate with Gmail API using OAuth2 credentials.

    Handles both initial authentication and token refresh. Stores credentials
    in a pickle file for future use.

    Returns
    -------
        any: Authenticated Gmail API service object

    Raises
    ------
        SystemExit: If authentication fails completely

    """
    token_pickle = "scripts/token.pickle"
    credentials_path = "scripts/credentials.json"

    try:
        # Check for existing credentials
        if os.path.exists(token_pickle):
            with open(token_pickle, "rb") as token:
                creds = pickle.load(token)
        else:
            creds = None

        # If no valid credentials, initiate auth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh expired credentials
                creds.refresh(Request())
            else:
                # Start new auth flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path,
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(token_pickle, "wb") as token:
                pickle.dump(creds, token)

        # Build and return Gmail API service
        return build("gmail", "v1", credentials=creds)

    except Exception as e:
        logging.exception(f"Authentication failed: {e!s}")
        sys.exit(1)


def get_priority_from_labels(labels: list) -> int | None:
    """Extract priority level from Gmail labels.

    Args:
    ----
        labels (list): List of Gmail label IDs/names

    Returns:
    -------
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


def load_edge_cases() -> list:
    """Load previously processed emails from edge_cases.json file.

    The file contains JSON objects, one per line, representing emails
    that required manual priority adjustments.

    Returns:
    -------
        list: List of dictionaries containing edge case data

    Note:
    ----
        Returns empty list if file doesn't exist or is empty

    """
    try:
        with open("scripts/edge_cases.json") as f:
            # Parse each line as separate JSON object
            return [json.loads(line) for line in f if line.strip()]
    except Exception as e:
        logging.exception(f"Error loading edge cases: {e!s}")
        return []


def find_corrections(service: any, edge_cases: list, conn: sqlite3.Connection) -> None:
    """Identify and record manual priority corrections in Gmail.

    Compares original priority assignments with current labels to detect
    manual corrections made by users.

    Args:
    ----
        service (any): Authenticated Gmail API service
        edge_cases (list): List of previously processed emails
        conn (sqlite3.Connection): Database connection

    Note:
    ----
        Errors are logged but don't interrupt processing of other emails

    """
    c = conn.cursor()

    for case in edge_cases:
        try:
            # Fetch current message metadata from Gmail
            msg = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=case.get("message_id"),
                    format="metadata",
                    metadataHeaders=["subject"],
                )
                .execute()
            )

            # Get current and original priorities
            current_priority = get_priority_from_labels(msg.get("labelIds", []))
            original_priority = case.get("priority")

            # If priorities differ, record the correction
            if current_priority is not None and current_priority != original_priority:
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
                        current_priority,
                        case.get("confidence", 0.0),
                        datetime.now().isoformat(),
                        False,
                    ),
                )

                logging.info(
                    f"Found correction for '{case.get('subject')}': "
                    f"{original_priority} -> {current_priority}",
                )

        except Exception as e:
            logging.exception(f"Error processing message: {e!s}")
            continue

    # Commit all changes to database
    conn.commit()


def analyze_patterns(conn: sqlite3.Connection) -> None:
    """Analyze corrections to identify and learn priority patterns.

    Processes unlearned corrections to identify recurring patterns in
    subject lines that correlate with specific priority levels.

    Args:
    ----
        conn (sqlite3.Connection): Database connection

    Note:
    ----
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

        # Mark these corrections as processed
        c.execute(
            """
            UPDATE email_corrections
            SET learned = TRUE
            WHERE subject = ? AND corrected_priority = ?
        """,
            (subject, priority),
        )

        logging.info(
            f"Learned pattern: '{subject}' -> Priority {priority} "
            f"(confidence: {confidence:.2f}, count: {count})",
        )

    # Commit all database changes
    conn.commit()


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
    ----
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
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM email_corrections WHERE learned = FALSE")
        pending = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM priority_patterns")
        patterns = c.fetchone()[0]

        logging.info("\nSummary:")
        logging.info(f"Pending corrections: {pending}")
        logging.info(f"Learned patterns: {patterns}")

    finally:
        # Ensure database connection is closed
        conn.close()


if __name__ == "__main__":
    main()
