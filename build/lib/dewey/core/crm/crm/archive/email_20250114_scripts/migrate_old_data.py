"""Data Migration Script

This script handles the migration of email data from an old SQLite database schema
to a new schema with improved structure and additional fields. The migration process
includes:

- Connecting to both source and target databases
- Reading data from the old schema
- Transforming data to fit the new schema
- Inserting data into the new database
- Handling errors and logging progress
- Maintaining data integrity through transactions

The script uses UUIDs for primary keys in the new database and adds timestamps
for created_at and updated_at fields.

Key Features:
- Batch processing with progress logging
- Comprehensive error handling
- Transaction management with rollback capability
- Detailed logging for audit purposes
"""

import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict

from scripts.log_config import setup_logger

logger = setup_logger(__name__)


def migrate_old_data() -> None:
    """Migrate email data from old database to new schema.

    This function handles the complete migration workflow:
    1. Connects to source and target databases
    2. Reads email data from old schema
    3. Transforms and inserts data into new schema
    4. Manages transactions and error handling

    The migration process includes:
    - Generating new UUIDs for each record
    - Adding timestamps for created_at and updated_at
    - Preserving all original email data
    - Handling potential data type conversions

    Raises:
    ------
        Exception: If any critical error occurs during migration

    """
    # Initialize database connections
    old_conn = None
    new_conn = None

    try:
        # Open connections to both databases
        logger.info("Opening source and target databases")
        old_conn = sqlite3.connect("email_data.db")
        new_conn = sqlite3.connect("srvo.db")

        # Create cursors for database operations
        old_cursor = old_conn.cursor()
        new_cursor = new_conn.cursor()

        # Fetch all emails from old database
        logger.info("Fetching emails from old database")
        old_cursor.execute("SELECT * FROM raw_emails")
        old_emails = old_cursor.fetchall()

        # Get column names from old schema for proper mapping
        old_cursor.execute("PRAGMA table_info(raw_emails)")
        columns = [col[1] for col in old_cursor.fetchall()]

        logger.info(f"Found {len(old_emails)} emails to migrate")

        # Process emails in batches with progress logging
        for i, old_email in enumerate(old_emails, 1):
            # Log progress every 100 emails
            if i % 100 == 0:
                logger.info(f"Migrated {i}/{len(old_emails)} emails")

            # Create dictionary mapping column names to values
            email_data: Dict[str, Any] = dict(zip(columns, old_email))

            try:
                # Generate new UUID for the record
                new_id = str(uuid.uuid4())
                current_time = datetime.now()

                # Insert transformed data into new schema
                new_cursor.execute(
                    """
                    INSERT INTO raw_emails (
                        id, gmail_id, thread_id, from_email, from_name,
                        to_email, to_name, subject, date, plain_body,
                        html_body, labels, metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id,
                        email_data.get("gmail_id"),
                        email_data.get("thread_id"),
                        email_data.get("from_email"),
                        email_data.get("from_name"),
                        email_data.get("to_email"),
                        email_data.get("to_name"),
                        email_data.get("subject"),
                        email_data.get("date"),
                        email_data.get("plain_body"),
                        email_data.get("html_body"),
                        email_data.get("labels"),
                        email_data.get("metadata"),
                        current_time,  # created_at timestamp
                        current_time,  # updated_at timestamp
                    ),
                )

            except Exception as e:
                # Log errors but continue with next email
                logger.error(f"Error migrating email {email_data.get('id')}: {str(e)}")
                continue

        # Commit transaction if all emails processed successfully
        new_conn.commit()
        logger.info("Migration completed successfully")

    except Exception as e:
        # Handle critical errors and rollback transaction
        logger.error(f"Error during migration: {str(e)}")
        if new_conn:
            new_conn.rollback()
        raise
    finally:
        # Ensure database connections are properly closed
        if old_conn:
            old_conn.close()
        if new_conn:
            new_conn.close()


if __name__ == "__main__":
    """Main entry point for the migration script."""
    try:
        logger.info("Starting data migration")
        migrate_old_data()
        logger.info("Data migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise
