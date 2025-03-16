# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

"""Contact Creation Script.

This script processes raw email data to create new contact records in the database.
It extracts unique email addresses from the raw_emails table that don't have corresponding
contact records and creates new contact entries with basic information.

Key Features:
- Identifies new contacts from email metadata
- Handles duplicate prevention through database constraints
- Provides detailed logging for tracking and debugging
- Uses UUIDs for contact identification
- Maintains enrichment status for future processing

Dependencies:
- Database connection through db_connector
- Logging configuration from log_config
- Configuration settings from config
"""

import uuid

from scripts.db_connector import get_db_connection
from scripts.log_config import setup_logger

# Initialize logger with module-specific configuration
logger = setup_logger(__name__)


def create_contacts_from_emails() -> None:
    """Process raw emails to create new contact records.

    This function:
    1. Queries the database for unique email addresses without existing contacts
    2. Creates new contact records with basic information
    3. Sets initial enrichment status to 'pending'
    4. Handles errors gracefully with detailed logging

    Returns
    -------
        None

    Raises
    ------
        Exception: Propagates any database or system-level errors after logging

    """
    try:
        # Establish database connection using context manager
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Query to find unique email addresses without existing contacts
            # Excludes empty/null email addresses to maintain data quality
            cursor.execute(
                """
                SELECT DISTINCT e.from_email, e.from_name
                FROM raw_emails e
                LEFT JOIN contacts c ON e.from_email = c.email
                WHERE c.id IS NULL
                AND e.from_email IS NOT NULL
                AND e.from_email != ''
                """,
            )

            # Fetch all results at once to minimize database load
            new_contacts: list[tuple[str, str]] = cursor.fetchall()
            logger.info(f"Found {len(new_contacts)} new contacts to create")

            # Process each new contact
            for email, name in new_contacts:
                try:
                    # Generate unique UUID for each contact
                    contact_id = str(uuid.uuid4())

                    # Insert new contact with initial enrichment status
                    cursor.execute(
                        """
                        INSERT INTO contacts (
                            id, email, name, enrichment_status
                        ) VALUES (?, ?, ?, 'pending')
                        """,
                        (contact_id, email, name),
                    )

                    logger.info(f"Created contact for {email}")

                except Exception as e:
                    # Log errors but continue processing other contacts
                    logger.exception(f"Error creating contact for {email}: {e!s}")
                    continue

            # Commit transaction after all inserts
            conn.commit()
            logger.info("Contact creation completed")

    except Exception as e:
        # Log and re-raise any critical errors
        logger.exception(f"Error in create_contacts_from_emails: {e!s}")
        raise


if __name__ == "__main__":
    """
    Main execution block for the contact creation script.

    This block:
    - Initializes the process with logging
    - Executes the contact creation function
    - Provides completion status
    - Handles any uncaught exceptions
    """
    try:
        logger.info("Starting contact creation process")
        create_contacts_from_emails()
        logger.info("Contact creation process completed")
    except Exception as e:
        logger.critical(f"Fatal error in main execution: {e!s}")
        raise
