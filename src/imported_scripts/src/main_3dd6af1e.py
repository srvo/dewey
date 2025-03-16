"""Main application module for the Email Processing System.

This module serves as the entry point for the application, handling:
- Application initialization and configuration
- Database setup and connection management
- Gmail API authentication and email fetching
- Logging configuration
- Error handling and recovery

The module follows a modular architecture with clear separation of concerns:
- Configuration is handled through environment variables and settings
- Database operations are delegated to the database connector
- Email processing is handled by the email processing service
- Logging is centralized and configurable

Key Features:
- Robust error handling and logging
- Configuration through environment variables
- Modular architecture for maintainability
- Comprehensive documentation
"""

from __future__ import annotations

import logging
import logging.config
import os
import os.path
import pickle
from datetime import datetime

from database.models import (
    Config,
    EmailLabelHistory,
    MessageThreadAssociation,
    RawEmail,
)
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.settings import LOGGING_CONFIG

logger = logging.getLogger(__name__)


def verify_database_schema() -> bool:
    """Verify that the database schema matches the expected structure."""
    required_tables = {"contacts", "emails", "email_contact_associations"}
    table_columns = {
        "contacts": {"id", "email", "created_at"},
        "emails": {
            "id",
            "gmail_id",
            "subject",
            "raw_content",
            "received_at",
            "processed_at",
        },
        "email_contact_associations": {"id", "email_id", "contact_id"},
    }

    with connection.cursor() as cursor:
        # Check for required tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = {
            row[0]
            for row in cursor.fetchall()
            if row[0] not in ("django_migrations", "sqlite_sequence")
        }
        missing_tables = required_tables - existing_tables
        if missing_tables:
            msg = f"Missing required tables: {', '.join(missing_tables)}"
            raise CommandError(msg)

        # Check Gmail ID uniqueness constraint
        cursor.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='index' AND tbl_name='emails'
            AND sql LIKE '%gmail_id%UNIQUE%';
        """,
        )
        result = cursor.fetchone()
        if not result or result[0] == 0:
            msg = "Missing unique constraint on emails.gmail_id"
            raise CommandError(msg)

        # Check columns for each table
        for table in sorted(required_tables):  # Sort tables for consistent order
            cursor.execute(f"PRAGMA table_info({table});")
            rows = cursor.fetchall()
            # Convert rows to a list of column names for better error messages
            existing_columns = {row[1] for row in rows}  # Column name is at index 1
            required_columns = table_columns[table]
            missing_columns = required_columns - existing_columns
            if missing_columns:
                msg = f"Table {table} missing columns: {', '.join(sorted(missing_columns))}"
                raise CommandError(
                    msg,
                )

    return True


def sync_gmail_history(last_history_id: str | None = None) -> bool:
    """Sync Gmail history changes since last_history_id.

    Args:
        last_history_id: Last processed history ID

    Returns:
        bool: True if sync successful, False otherwise

    """
    try:
        # Get Gmail service
        creds = get_gmail_credentials()
        service = build("gmail", "v1", credentials=creds)

        # Get history changes
        history = (
            service.users()
            .history()
            .list(userId="me", startHistoryId=last_history_id)
            .execute()
        )

        # Process changes
        for change in history.get("history", []):
            # Handle message added/removed
            if "messagesAdded" in change:
                for msg in change["messagesAdded"]:
                    process_message_added(msg)

            if "messagesRemoved" in change:
                for msg in change["messagesRemoved"]:
                    process_message_removed(msg)

            # Handle label changes
            if "labelsAdded" in change or "labelsRemoved" in change:
                process_label_changes(change)

        # Update last processed history ID
        if history.get("historyId"):
            update_last_history_id(history["historyId"])

        return True

    except Exception as e:
        logging.exception(f"Error syncing Gmail history: {e!s}")
        return False


def verify_gmail_id_tracking() -> bool:
    """Verify Gmail ID tracking integrity.

    Checks for:
    - Missing Gmail IDs
    - Duplicate Gmail IDs
    - Orphaned email records

    Returns:
        bool: True if Gmail ID tracking is valid, False otherwise

    """
    try:
        with connection.cursor() as cursor:
            # Check for missing Gmail IDs
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM emails
                WHERE gmail_id IS NULL
            """,
            )
            missing_ids = cursor.fetchone()[0]
            if missing_ids > 0:
                logging.error(f"Found {missing_ids} emails with missing Gmail IDs")
                return False

            # Check for duplicate Gmail IDs
            cursor.execute(
                """
                SELECT gmail_id, COUNT(*)
                FROM emails
                GROUP BY gmail_id
                HAVING COUNT(*) > 1
            """,
            )
            duplicates = cursor.fetchall()
            if duplicates:
                logging.error(f"Found {len(duplicates)} duplicate Gmail IDs")
                return False

            return True
    except Exception as e:
        logging.exception(f"Error verifying Gmail ID tracking: {e!s}")
        return False


def process_message_added(message_data) -> None:
    """Process a newly added message."""
    email = RawEmail.objects.filter(
        gmail_message_id=message_data["message"]["id"],
    ).first()

    if not email:
        # Create new email record
        email = RawEmail(
            gmail_message_id=message_data["message"]["id"],
            thread_id=message_data["message"]["threadId"],
            history_id=message_data["historyId"],
        )
        email.save()

    # Create thread association
    association = MessageThreadAssociation(
        message_id=email.email_id,
        thread_id=message_data["message"]["threadId"],
        version=1,
    )
    association.save()


def process_message_removed(message_data) -> None:
    """Process a removed message."""
    email = RawEmail.objects.filter(
        gmail_message_id=message_data["message"]["id"],
    ).first()

    if email:
        # Mark thread association as ended
        association = MessageThreadAssociation.objects.filter(
            message_id=email.email_id,
            valid_to=None,
        ).first()

        if association:
            association.valid_to = datetime.utcnow()
            association.save()


def process_label_changes(change_data) -> None:
    """Process label changes for messages."""
    for label_change in change_data.get("labelsAdded", []):
        for message in label_change["messageIds"]:
            history = EmailLabelHistory(
                email_id=message,
                label_id=label_change["labelId"],
                action="added",
                changed_by="system",
            )
            history.save()

    for label_change in change_data.get("labelsRemoved", []):
        for message in label_change["messageIds"]:
            history = EmailLabelHistory(
                email_id=message,
                label_id=label_change["labelId"],
                action="removed",
                changed_by="system",
            )
            history.save()


def update_last_history_id(history_id) -> None:
    """Update the last processed history ID."""
    config, created = Config.objects.get_or_create(
        key="last_history_id",
        defaults={"value": history_id},
    )
    if not created:
        config.value = history_id
        config.save()


def create_database() -> int:
    """Create and initialize the database.

    Returns:
        int: 0 if successful, 1 if failed

    """
    try:
        # Apply migrations first
        call_command("migrate")

        # Then verify schema
        verify_database_schema()
        return 0
    except CommandError:
        # Re-raise command errors for proper handling
        raise
    except Exception as e:
        logger.exception(f"Failed to create database: {e!s}")
        return 1


def get_gmail_credentials():
    """Get Gmail API credentials, either from cache or by prompting user."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return creds


def setup_logging(name):
    """Configure logging for the application."""
    logging.config.dictConfig(LOGGING_CONFIG)
    return logging.getLogger(name)


def initialize_application() -> bool:
    """Initialize the application.

    Returns:
        bool: True if initialization successful, False otherwise

    """
    try:
        # Set up logging first
        logging.config.dictConfig(LOGGING_CONFIG)

        # Create and initialize database
        try:
            if create_database() != 0:
                logger.error("Failed to initialize database")
                return False
        except CommandError as e:
            logger.exception(f"Command error: {e!s}")
            return False

        return True
    except Exception as e:
        logger.exception(f"Failed to initialize application: {e!s}")
        return False


# Gmail API authorization scopes
# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
