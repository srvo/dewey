# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

"""Database setup script for email processing system.

This module handles the creation and configuration of the SQLite database used for storing
email data, contact information, and processing metadata. It creates all necessary tables
and indexes with appropriate constraints and relationships.

The database schema is designed to support:
- Email storage with full metadata
- Contact management and enrichment
- Processing history and error tracking
- Scalable indexing for common queries
- Soft delete functionality
- Extensible metadata storage using JSON fields

Key Features:
- Atomic database initialization
- Foreign key constraints
- Write-Ahead Logging (WAL) for better concurrency
- Comprehensive indexing for common queries
- Soft delete pattern implementation
- Extensible JSON metadata storage
"""

import logging
import sqlite3

# Configure logging with timestamp, level, and message format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="project.log",
    filemode="a",
)
logger = logging.getLogger(__name__)


def setup_database() -> None:
    """Initialize and configure the SQLite database with required schema.

    This function:
    1. Creates a new SQLite database connection
    2. Enables foreign key support and WAL mode
    3. Creates all necessary tables with appropriate constraints
    4. Creates indexes for common query patterns
    5. Handles errors and logs progress

    The database schema includes:
    - raw_emails: Stores email messages with full metadata
    - contacts: Manages contact information and relationships
    - contact_metadata_history: Tracks changes to contact metadata
    - processing_history: Logs email processing operations

    Raises
    ------
        Exception: If any database operation fails, the exception is logged and re-raised

    Returns
    -------
        None

    """
    try:
        conn = sqlite3.connect("srvo.db")
        cursor = conn.cursor()

        # Enable foreign key support for relational integrity
        cursor.execute("PRAGMA foreign_keys = ON")

        # Enable Write-Ahead Logging for better concurrency and performance
        cursor.execute("PRAGMA journal_mode=WAL")

        # Drop existing raw_emails table if it exists to ensure clean slate
        cursor.execute("DROP TABLE IF EXISTS raw_emails")

        # Create raw_emails table with comprehensive email metadata
        # This table serves as the primary storage for all email messages
        # Includes fields for:
        # - Message identification (UUID and Gmail ID)
        # - Content storage (plain text, HTML, raw)
        # - Participant information
        # - Metadata and processing status
        # - System timestamps for tracking
        cursor.execute(
            """
        CREATE TABLE raw_emails (
            id TEXT PRIMARY KEY,                    -- UUID for internal reference
            gmail_id TEXT UNIQUE,                   -- Gmail API message ID
            thread_id TEXT,                         -- Gmail thread ID

            -- Email content
            subject TEXT,
            snippet TEXT,
            plain_body TEXT,                        -- Plain text content
            html_body TEXT,                         -- HTML content if available
            raw_content TEXT,                       -- Original raw content

            -- Participants
            from_name TEXT,
            from_email TEXT,
            to_addresses TEXT,                      -- JSON array
            cc_addresses TEXT,                      -- JSON array
            bcc_addresses TEXT,                     -- JSON array

            -- Metadata
            received_date TIMESTAMP,
            labels TEXT,                            -- JSON array of Gmail labels
            metadata JSON,                          -- Extensible metadata store
            importance INTEGER DEFAULT 0,           -- Priority/importance score
            category TEXT,                          -- Email category/type

            -- Flags
            is_draft BOOLEAN DEFAULT 0,
            is_sent BOOLEAN DEFAULT 0,
            is_read BOOLEAN DEFAULT 0,
            is_starred BOOLEAN DEFAULT 0,
            is_trashed BOOLEAN DEFAULT 0,

            -- Processing status
            status TEXT DEFAULT 'new',              -- new, processing, processed, failed
            processing_version INTEGER DEFAULT 1,    -- For tracking schema/processing changes
            processed_date TIMESTAMP,
            error_message TEXT,

            -- System fields
            size_estimate INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP                    -- For soft deletes
        )""",
        )

        # Create indexes to optimize common query patterns
        # Index on Gmail ID for API integration lookups
        cursor.execute("CREATE INDEX idx_raw_emails_gmail_id ON raw_emails(gmail_id)")

        # Index on thread ID for conversation threading
        cursor.execute("CREATE INDEX idx_raw_emails_thread ON raw_emails(thread_id)")

        # Index on received date for time-based queries
        cursor.execute("CREATE INDEX idx_raw_emails_date ON raw_emails(received_date)")

        # Index on sender email for contact-based queries
        cursor.execute("CREATE INDEX idx_raw_emails_from ON raw_emails(from_email)")

        # Index on processing status for workflow management
        cursor.execute("CREATE INDEX idx_raw_emails_status ON raw_emails(status)")

        # Index on category for classification-based queries
        cursor.execute("CREATE INDEX idx_raw_emails_category ON raw_emails(category)")

        # Create contacts table for managing contact information
        # This table stores:
        # - Contact identification and metadata
        # - Source tracking for contact discovery
        # - Status and timestamps for lifecycle management
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS contacts (
            id TEXT PRIMARY KEY,                    -- UUID
            email TEXT UNIQUE,
            name TEXT,
            company TEXT,
            metadata JSON,                          -- Extensible metadata store
            source_type TEXT,                       -- How we discovered this contact
            source_id TEXT,                         -- Reference to source (e.g. email id)
            status TEXT DEFAULT 'active',           -- active, archived, blocked
            first_seen_date TIMESTAMP,
            last_seen_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP                    -- For soft deletes
        )""",
        )

        # Create contact_metadata_history table for audit trail
        # This table tracks changes to contact metadata over time
        # Includes:
        # - Change tracking with old/new values
        # - Confidence scoring for data quality
        # - Source tracking for data provenance
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS contact_metadata_history (
            id TEXT PRIMARY KEY,                    -- UUID for each change record
            contact_id TEXT,                        -- Reference to contacts table
            metadata_type TEXT,                     -- Type of metadata (e.g. 'job_title', 'phone')
            old_value TEXT,                         -- Previous value before change
            new_value TEXT,                         -- New value after change
            confidence REAL,                        -- Confidence score (0.0-1.0)
            source_type TEXT,                       -- Source of this metadata update
            source_id TEXT,                         -- Reference to source record
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- When change occurred
            FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
        )""",
        )

        # Create processing_history table for operational analytics
        # This table tracks all email processing operations
        # Includes:
        # - Processing type and status
        # - Error tracking and debugging info
        # - Performance metrics
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS processing_history (
            id TEXT PRIMARY KEY,                    -- UUID
            email_id TEXT,
            process_type TEXT,                      -- Type of processing performed
            status TEXT,                           -- success, failure
            error_message TEXT,
            metadata JSON,                          -- Additional processing metadata
            duration_ms INTEGER,                    -- Processing duration
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (email_id) REFERENCES raw_emails(id)
        )""",
        )

        conn.commit()
        logger.info("Database setup completed successfully")

    except Exception as e:
        logger.exception(f"Error setting up database: {e!s}")
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    """Main entry point for database setup script."""
    try:
        logger.info("Starting database setup")
        setup_database()
        logger.info("Database setup completed successfully")
    except Exception as e:
        logger.exception(f"Database setup failed: {e!s}")
        raise
