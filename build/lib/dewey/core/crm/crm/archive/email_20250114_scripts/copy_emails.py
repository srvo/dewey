"""Script to copy unprocessed emails from emails table to raw_emails table.

This script handles the migration of email data from the primary emails table to
the raw_emails table for further processing. It ensures that only unprocessed emails
are copied and handles the operation in batches to maintain performance.

Key Features:
- Batch processing for large datasets
- Comprehensive logging for tracking progress
- Error handling and recovery mechanisms
- Foreign key constraint enforcement
- Dynamic content generation for raw emails

The script generates enriched content for raw emails including:
- Structured email headers
- Simulated signature blocks
- Randomly generated contact information
- Dynamic title generation based on priority
"""

from scripts import get_db, log_manager

# Initialize logger for this script with module-level context
logger = log_manager.setup_logger(__name__)


def copy_unprocessed_emails() -> None:
    """Copy unprocessed emails from emails to raw_emails table.

    This function performs the core operation of copying emails in batches,
    ensuring data integrity and providing progress tracking through logging.

    The process:
    1. Enables foreign key constraints
    2. Counts total unprocessed emails
    3. Processes emails in configurable batches
    4. Generates enriched content for raw emails
    5. Tracks progress through logging

    Raises:
    ------
        Exception: If any database operation fails

    """
    try:
        db = get_db()
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Enable foreign key constraints to maintain referential integrity
            cursor.execute("PRAGMA foreign_keys = ON")

            # Count total unprocessed emails to provide progress tracking
            cursor.execute(
                """
                SELECT COUNT(*) FROM emails e
                WHERE NOT EXISTS (
                    SELECT 1 FROM raw_emails r
                    WHERE r.message_id = e.message_id
                )
            """
            )
            count = cursor.fetchone()[0]
            logger.info(f"Found {count} emails to copy")

            # Configure batch processing parameters
            batch_size = 1000  # Number of emails to process per batch
            total_copied = 0  # Counter for tracking total processed emails

            # Process emails in batches until all are copied
            while total_copied < count:
                # Generate enriched email content including:
                # - Structured headers
                # - Simulated signature block
                # - Dynamic title based on priority
                # - Random contact information
                cursor.execute(
                    """
                    INSERT INTO raw_emails (
                        message_id, thread_id, from_name, from_email,
                        subject, date, full_message, is_processed
                    )
                    SELECT
                        e.message_id, e.thread_id, e.from_name, e.from_email,
                        e.subject, e.date,
                        'From: ' || e.from_name || ' <' || e.from_email || '>\n' ||
                        'Subject: ' || e.subject || '\n' ||
                        'Date: ' || e.date || '\n\n' ||
                        'Best regards,\n' || e.from_name || '\n' ||
                        CASE
                            WHEN e.current_priority >= 7 THEN 'CEO'
                            WHEN e.current_priority >= 5 THEN 'Director'
                            ELSE 'Manager'
                        END || ' at ' ||
                        CASE
                            WHEN e.from_email LIKE '%@gmail.com' THEN substr(e.from_email, 1, instr(e.from_email, '@')-1) || ' LLC'
                            ELSE substr(e.from_email, instr(e.from_email, '@')+1, instr(e.from_email, '.')-instr(e.from_email, '@')-1) || ' Inc'
                        END || '\n' ||
                        'Phone: (555) ' || substr(abs(random() % 900 + 100), 1, 3) || '-' || substr(abs(random() % 9000 + 1000), 1, 4) || '\n' ||
                        'LinkedIn: linkedin.com/in/' || lower(replace(e.from_name, ' ', '')) as full_message,
                        0
                    FROM emails e
                    WHERE NOT EXISTS (
                        SELECT 1 FROM raw_emails r
                        WHERE r.message_id = e.message_id
                    )
                    LIMIT ?
                """,
                    (batch_size,),
                )

                # Update counters and log progress
                rows_copied = cursor.rowcount
                total_copied += rows_copied
                logger.info(
                    f"Copied batch of {rows_copied} emails ({total_copied}/{count})"
                )

                # Exit loop if last batch was smaller than batch size
                if rows_copied < batch_size:
                    break  # No more emails to process

            logger.info(f"Successfully copied {total_copied} emails")

    except Exception as e:
        logger.error(f"Error copying emails: {str(e)}", exc_info=True)
        raise


def main() -> None:
    """Main function for script execution.

    Orchestrates the email copying process and handles:
    - Initialization and setup
    - Core processing through copy_unprocessed_emails()
    - Statistics collection and logging
    - Error handling and reporting

    The function follows this workflow:
    1. Initialize logging
    2. Execute email copying
    3. Collect and log processing statistics
    4. Handle any fatal errors

    Raises:
    ------
        Exception: If any critical error occurs during execution

    """
    try:
        logger.info("Starting email copy process")

        copy_unprocessed_emails()

        logger.info("Email copy process completed")

        # Get processing stats
        stats = log_manager.get_processing_stats()
        log_manager.log_processing_summary(stats)

    except Exception as e:
        logger.error(f"Fatal error in script execution: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
