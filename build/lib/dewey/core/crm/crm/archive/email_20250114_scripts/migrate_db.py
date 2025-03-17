"""Database migration script to add enrichment tables and fields.

This script handles the evolution of the database schema to support:
- Contact enrichment data (job titles, LinkedIn profiles, etc.)
- Business opportunity tracking
- Enrichment task management
- Data source tracking
- Historical metadata changes

The migration is idempotent - it can be run multiple times safely as it checks
for existing columns and tables before creating them.

Key Features:
- Safe schema evolution with existence checks
- Comprehensive foreign key relationships
- Indexing for common query patterns
- JSON support for flexible metadata storage
- Timestamp tracking for all changes
"""

import sqlite3

from scripts.config import config
from scripts.log_config import setup_logger

logger = setup_logger(__name__)


def migrate_database() -> None:
    """Perform database migration to add enrichment-related schema elements.

    This function:
    - Adds new columns to existing tables
    - Creates new tables for enrichment data
    - Sets up foreign key relationships
    - Creates indexes for common query patterns
    - Implements WAL mode for better concurrency

    Raises:
    ------
        sqlite3.Error: If any database operation fails

    """
    conn = None
    try:
        logger.info(f"Connecting to database at {config.DB_PATH}")
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        # Enable foreign key constraints and WAL mode for better concurrency
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")

        # Get existing columns to avoid duplicate column creation
        cursor.execute("PRAGMA table_info(contacts)")
        existing_columns = {col[1] for col in cursor.fetchall()}

        # Define new columns to add to contacts table
        # Each tuple contains (column_name, column_type)
        new_columns = [
            ("job_title", "TEXT"),  # Professional title of the contact
            ("linkedin_url", "TEXT"),  # URL to LinkedIn profile
            ("phone", "TEXT"),  # Contact phone number
            (
                "enrichment_status",
                "TEXT DEFAULT 'pending'",
            ),  # Status of enrichment process
            ("last_enriched", "TIMESTAMP"),  # Last successful enrichment timestamp
            ("enrichment_source", "TEXT"),  # Source of enrichment data
            ("confidence_score", "REAL DEFAULT 0.0"),  # Confidence in enrichment data
        ]

        # Add new columns only if they don't already exist
        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                logger.info(f"Adding column {col_name} to contacts table")
                cursor.execute(f"ALTER TABLE contacts ADD COLUMN {col_name} {col_type}")
                logger.debug(f"Successfully added {col_name} ({col_type}) to contacts")

        # Create opportunities table to track potential business opportunities
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS opportunities (
            id TEXT PRIMARY KEY,  -- Unique identifier for the opportunity
            contact_id TEXT,  -- Associated contact
            email_id TEXT,  -- Source email that triggered the opportunity
            opportunity_type TEXT,  -- Type of opportunity (demo, meeting, etc.)
            status TEXT DEFAULT 'new',  -- Current status of opportunity
            confidence REAL,  -- Confidence score in opportunity validity
            metadata JSON,  -- Flexible metadata storage
            detected_date TIMESTAMP,  -- When opportunity was detected
            due_date TIMESTAMP,  -- Deadline for opportunity follow-up
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Record creation time
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Last update time
            FOREIGN KEY (contact_id) REFERENCES contacts(id),
            FOREIGN KEY (email_id) REFERENCES raw_emails(id)
        )"""
        )
        logger.debug("Created opportunities table with foreign key constraints")

        # Create enrichment_tasks table to manage enrichment workflows
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS enrichment_tasks (
            id TEXT PRIMARY KEY,  -- Unique task identifier
            entity_type TEXT,  -- Type of entity being enriched
            entity_id TEXT,  -- ID of entity being enriched
            task_type TEXT,  -- Type of enrichment task
            status TEXT DEFAULT 'pending',  -- Current task status
            attempts INTEGER DEFAULT 0,  -- Number of attempts made
            last_attempt TIMESTAMP,  -- Timestamp of last attempt
            result JSON,  -- Task result data
            error_message TEXT,  -- Last error message if task failed
            metadata JSON,  -- Additional task metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Task creation time
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Last update time
        )"""
        )
        logger.debug("Created enrichment_tasks table with JSON support")

        # Create enrichment_sources table to track data provenance
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS enrichment_sources (
            id TEXT PRIMARY KEY,  -- Unique source identifier
            source_type TEXT,  -- Type of data source
            entity_type TEXT,  -- Type of entity this source relates to
            entity_id TEXT,  -- ID of related entity
            data JSON,  -- Source data in JSON format
            confidence REAL,  -- Confidence in source reliability
            valid_from TIMESTAMP,  -- When this data became valid
            valid_to TIMESTAMP,  -- When this data expires
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Record creation time
        )"""
        )
        logger.debug("Created enrichment_sources table with validity tracking")

        # Create indexes to optimize common query patterns
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_opportunities_contact ON opportunities(contact_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_opportunities_email ON opportunities(email_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_opportunities_type ON opportunities(opportunity_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_enrichment_tasks_entity ON enrichment_tasks(entity_type, entity_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_enrichment_tasks_status ON enrichment_tasks(status)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_enrichment_sources_entity ON enrichment_sources(entity_type, entity_id)"
        )
        logger.debug("Created indexes for optimized query performance")

        # Create contact_metadata_history table to track changes over time
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS contact_metadata_history (
            id TEXT PRIMARY KEY,  -- Unique history record identifier
            contact_id TEXT,  -- Related contact
            metadata_type TEXT,  -- Type of metadata being changed
            old_value TEXT,  -- Previous value
            new_value TEXT,  -- New value
            confidence REAL,  -- Confidence in change validity
            source_type TEXT,  -- Source of this change
            source_id TEXT,  -- Reference to source record
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Change timestamp
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )"""
        )
        logger.debug("Created contact_metadata_history table for audit trail")

        conn.commit()
        logger.info("Database migration completed successfully")

    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    """Main entry point for the migration script."""
    logger.info("Starting database migration")
    try:
        migrate_database()
        logger.info("Database migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise
