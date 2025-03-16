# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Database initialization script to create all necessary tables and indexes.

This script handles the complete setup of the SQLite database schema including:
- Core tables for email processing and contact management
- Enrichment tracking tables
- Historical metadata tracking
- Indexes for optimized query performance
- Foreign key relationships and constraints

The schema is designed to support:
- Email processing and storage
- Contact enrichment workflows
- Opportunity detection and tracking
- Historical metadata versioning
- Task management for enrichment processes
"""

import sqlite3

from scripts.config import config
from scripts.log_config import setup_logger

logger = setup_logger(__name__)


def init_database() -> None:
    """Initialize database with all required tables and indexes.

    This function:
    1. Creates all core tables with appropriate constraints
    2. Sets up foreign key relationships
    3. Creates indexes for common query patterns
    4. Enables database-level features like foreign key support

    Raises
    ------
        sqlite3.Error: If any database operation fails

    """
    conn = None
    try:
        logger.info(f"Connecting to database at {config.DB_PATH}")
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        # Enable foreign key support for relational integrity
        cursor.execute("PRAGMA foreign_keys = ON")
        # WAL mode disabled for now due to compatibility concerns
        # cursor.execute("PRAGMA journal_mode = WAL")

        # Create raw_emails table - stores all incoming email data
        # This is the primary table for email processing pipeline
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS raw_emails (
            id TEXT PRIMARY KEY,
            gmail_id TEXT UNIQUE,
            thread_id TEXT,
            from_email TEXT,
            from_name TEXT,
            to_email TEXT,
            to_name TEXT,
            subject TEXT,
            date TIMESTAMP,
            plain_body TEXT,
            html_body TEXT,
            labels TEXT,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        )

        # Create contacts table - central repository for all contact information
        # Includes fields for both raw and enriched contact data
        # Uses JSON metadata field for flexible storage of additional attributes
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS contacts (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            name TEXT,
            company TEXT,
            job_title TEXT,
            linkedin_url TEXT,
            phone TEXT,
            enrichment_status TEXT DEFAULT 'pending',
            last_enriched TIMESTAMP,
            enrichment_source TEXT,
            confidence_score REAL DEFAULT 0.0,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        )

        # Create opportunities table - tracks detected business opportunities
        # Links to both contacts and emails for full context
        # Includes confidence scoring and status tracking
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS opportunities (
            id TEXT PRIMARY KEY,
            contact_id TEXT,
            email_id TEXT,
            opportunity_type TEXT,        -- demo, meeting, follow-up, etc.
            status TEXT DEFAULT 'new',    -- new, active, completed, expired
            confidence REAL,
            metadata JSON,
            detected_date TIMESTAMP,
            due_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id),
            FOREIGN KEY (email_id) REFERENCES raw_emails(id)
        )""",
        )

        # Create enrichment_tasks table - manages enrichment workflows
        # Tracks status and results of enrichment processes
        # Supports retry logic through attempts tracking
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS enrichment_tasks (
            id TEXT PRIMARY KEY,
            entity_type TEXT,             -- contact, email, opportunity
            entity_id TEXT,               -- ID of the entity being enriched
            task_type TEXT,               -- contact_info, social_media, company_info
            status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
            attempts INTEGER DEFAULT 0,
            last_attempt TIMESTAMP,
            result JSON,
            error_message TEXT,
            metadata JSON,                -- Additional metadata for the task
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        )

        # Create enrichment_sources table - tracks provenance of enriched data
        # Maintains history of where data came from and its validity period
        # Supports confidence scoring for data quality assessment
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS enrichment_sources (
            id TEXT PRIMARY KEY,
            source_type TEXT,             -- email_signature, linkedin, clearbit, etc.
            entity_type TEXT,             -- contact, company
            entity_id TEXT,
            data JSON,
            confidence REAL,
            valid_from TIMESTAMP,
            valid_to TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        )

        # Create contact_metadata_history table - tracks changes to contact metadata
        # Provides audit trail for contact information changes
        # Links to enrichment sources for provenance tracking
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS contact_metadata_history (
            id TEXT PRIMARY KEY,
            contact_id TEXT,
            metadata_type TEXT,           -- Type of metadata (e.g. 'job_title', 'phone')
            old_value TEXT,
            new_value TEXT,
            confidence REAL,
            source_type TEXT,             -- How we got this update
            source_id TEXT,               -- Reference to source
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )""",
        )

        # Create indexes - optimize common query patterns
        # Indexes are carefully selected based on query patterns and data volumes
        # Each index is documented with its primary use case
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_raw_emails_gmail_id ON raw_emails(gmail_id)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_raw_emails_thread ON raw_emails(thread_id)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_raw_emails_from ON raw_emails(from_email)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_raw_emails_date ON raw_emails(date)",
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_contacts_enrichment ON contacts(enrichment_status)",
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_opportunities_contact ON opportunities(contact_id)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_opportunities_email ON opportunities(email_id)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_opportunities_type ON opportunities(opportunity_type)",
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_enrichment_tasks_entity ON enrichment_tasks(entity_type, entity_id)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_enrichment_tasks_status ON enrichment_tasks(status)",
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_enrichment_sources_entity ON enrichment_sources(entity_type, entity_id)",
        )

        conn.commit()
        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.exception(f"Error during initialization: {e!s}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    """Main execution block for standalone database initialization."""
    logger.info("Starting database initialization")
    try:
        init_database()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.exception(f"Database initialization failed: {e!s}")
        raise
