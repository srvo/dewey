"""Script to fix errored emails by reprocessing them.
Dependencies:
- SQLite database with processed_contacts and raw_emails tables
- DeepInfra API for contact validation
- Logging utilities from log_analyzer.py
"""

import logging
import sqlite3
import time

from scripts.db_connector import get_db
from scripts.enrich_contacts import (
    extract_contact_info,
    update_contact_database,
    validate_with_deepinfra,
)
from scripts.log_analyzer import (
    get_errored_message_ids,
    log_recovery_progress,
    log_recovery_summary,
)

# Initialize logging to capture INFO and ERROR level logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="project.log",
    filemode="a",
)
logger = logging.getLogger(__name__)


def process_errored_email(service, conn: sqlite3.Connection, message_id: str) -> bool:
    """Reprocess a single errored email.

    Args:
    ----
        service: Email service instance (e.g., Gmail API service).
        conn (sqlite3.Connection): Active SQLite database connection.
        message_id (str): The Message-ID of the email to reprocess.

    Returns:
    -------
        bool: True if processing was successful, False otherwise.

    """
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
        SELECT from_name, from_email, subject, full_message
        FROM raw_emails
        WHERE message_id = ?
        """,
            (message_id,),
        )
        email = cursor.fetchone()

        if not email:
            logger.error(f"Email with Message-ID {message_id} not found.")
            return False

        from_name, from_email, subject, full_message = email
        contact_info = extract_contact_info(full_message)
        validation = validate_with_deepinfra(
            f"From: {from_name} <{from_email}>\n"
            f"Subject: {subject}\n"
            f"Signature: {contact_info.get('signature_block')}"
        )

        if validation:
            update_contact_database(conn, contact_info, validation)
            cursor.execute(
                """
            INSERT INTO processed_contacts (message_id)
            VALUES (?)
            """,
                (message_id,),
            )
            conn.commit()
            logger.info(f"Successfully reprocessed email {message_id}.")
            return True
        else:
            logger.error(f"Validation failed for email {message_id}.")
            return False

    except Exception as e:
        logger.error(f"Error processing errored email {message_id}: {str(e)}")
        return False


def main():
    """Main function to identify and reprocess errored emails."""
    db = get_db()
    with db.get_connection() as conn:
        # Get unique errored message IDs from log_analyzer
        errored_message_ids = get_errored_message_ids("project.log")
        total_to_process = len(errored_message_ids)
        logger.info(f"Found {total_to_process} errored emails to reprocess.")

        success_count = 0
        failure_count = 0

        for message_id in errored_message_ids:
            success = process_errored_email(None, conn, message_id)
            if success:
                success_count += 1
            else:
                failure_count += 1
            log_recovery_progress(success_count, failure_count, total_to_process)
            time.sleep(1)  # To avoid overwhelming the API

        log_recovery_summary(total_to_process, success_count, failure_count)


if __name__ == "__main__":
    logger.info("Starting errored emails recovery process.")
    main()
    logger.info("Errored emails recovery process completed.")
