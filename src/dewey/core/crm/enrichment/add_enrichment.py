"""Add enrichment capabilities to existing database while preserving sync functionality.

This module provides functionality to enhance the existing database with data enrichment
capabilities. It adds new tables and columns to support:
- Contact enrichment tracking
- Task management for enrichment processes
- Source tracking for enriched data
- Confidence scoring and status tracking

The changes are designed to be non-destructive and maintain compatibility with existing
database operations.
"""

import sqlite3
from typing import Any, Dict

from dewey.core.base_script import BaseScript


class AddEnrichmentCapabilities(BaseScript):
    """Adds enrichment capabilities to the existing database."""

    def __init__(self) -> None:
        """Initializes the AddEnrichmentCapabilities script."""
        super().__init__(config_section="crm", requires_db=True)

    def run(self) -> None:
        """Adds enrichment capabilities while preserving existing functionality.

        This function performs the following operations:
        1. Adds new columns to the contacts table for enrichment tracking
        2. Creates a new enrichment_tasks table for managing enrichment processes
        3. Creates a new enrichment_sources table for tracking data provenance
        4. Adds necessary indexes for efficient querying

        The function uses a transaction to ensure atomicity - either all changes are applied
        or none are if an error occurs.

        Raises
        ------
            sqlite3.Error: If any database operation fails
            Exception: For any other unexpected errors
        """
        conn = None
        try:
            self.logger.info("Connecting to production database")
            db_path = self.get_config_value("db_path", "email_data.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Add enrichment fields to contacts table
            self.logger.info("Adding enrichment fields to contacts table")

            # Add status column to track enrichment progress
            cursor.execute(
                """
            ALTER TABLE contacts ADD COLUMN enrichment_status TEXT DEFAULT 'pending';
                """,
            )
            # Status values:
            # - 'pending': No enrichment attempted yet
            # - 'processing': Enrichment in progress
            # - 'completed': Successful enrichment
            # - 'failed': Enrichment attempt failed
            cursor.execute(
                """
            ALTER TABLE contacts ADD COLUMN last_enriched TIMESTAMP;
                """,
            )
            # Tracks when the contact was last enriched
            # Useful for determining if re-enrichment is needed
            cursor.execute(
                """
            ALTER TABLE contacts ADD COLUMN enrichment_source TEXT;
                """,
            )
            # Tracks the primary source of enrichment data
            # Examples: 'clearbit', 'linkedin', 'email_signature'
            cursor.execute(
                """
            ALTER TABLE contacts ADD COLUMN confidence_score REAL DEFAULT 0.0;
                """,
            )
            # Confidence score (0.0-1.0) indicating reliability of enriched data
            # Helps prioritize manual review of low-confidence enrichments

            # Create enrichment tasks table
            self.logger.info("Creating enrichment tasks table")
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS enrichment_tasks (
                id TEXT PRIMARY KEY,          -- Unique task identifier
                entity_type TEXT,             -- Type of entity being enriched (contact, email, opportunity)
                entity_id TEXT,               -- ID of the entity being enriched
                task_type TEXT,               -- Type of enrichment task (contact_info, social_media, company_info)
                status TEXT DEFAULT 'pending', -- Current task status
                attempts INTEGER DEFAULT 0,   -- Number of attempts made
                last_attempt TIMESTAMP,       -- Timestamp of last attempt
                result JSON,                  -- Structured result data from enrichment
                error_message TEXT,           -- Error message if task failed
                metadata JSON,                -- Additional metadata for the task
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
                """,
            )
            # Task status lifecycle:
            # pending -> processing -> (completed|failed)
            # Failed tasks can be retried, incrementing attempts counter

            # Create enrichment sources table
            self.logger.info("Creating enrichment sources table")
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS enrichment_sources (
                id TEXT PRIMARY KEY,          -- Unique source identifier
                source_type TEXT,             -- Type of source (email_signature, linkedin, clearbit, etc.)
                entity_type TEXT,             -- Type of entity (contact, company)
                entity_id TEXT,               -- ID of the enriched entity
                data JSON,                    -- Raw data from the source
                confidence REAL,              -- Confidence in this source's accuracy
                valid_from TIMESTAMP,         -- When this data became valid
                valid_to TIMESTAMP,           -- When this data expires
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
                """,
            )
            # This table tracks provenance of enrichment data
            # Allows tracking multiple sources for the same entity
            # Useful for data reconciliation and versioning

            # Add necessary indexes for performance optimization
            self.logger.info("Creating indexes for enrichment tables")

            # Index for querying tasks by entity
            cursor.execute(
                """
            CREATE INDEX IF NOT EXISTS idx_enrichment_tasks_entity
            ON enrichment_tasks(entity_type, entity_id);
                """,
            )
            # Optimizes queries like:
            # - Get all tasks for a specific contact
            # - Get all tasks for a specific email
            cursor.execute(
                """
            CREATE INDEX IF NOT EXISTS idx_enrichment_tasks_status
            ON enrichment_tasks(status);
                """,
            )
            # Optimizes queries like:
            # - Get all pending tasks
            # - Get all failed tasks needing retry
            cursor.execute(
                """
            CREATE INDEX IF NOT EXISTS idx_enrichment_sources_entity
            ON enrichment_sources(entity_type, entity_id);
                """,
            )
            # Optimizes queries like:
            # - Get all sources for a specific contact
            # - Get all sources for a specific company
            cursor.execute(
                """
            CREATE INDEX IF NOT EXISTS idx_contacts_enrichment
            ON contacts(enrichment_status);
                """,
            )
            # Optimizes queries like:
            # - Get all contacts needing enrichment
            # - Get all contacts with failed enrichment

            conn.commit()
            self.logger.info("Successfully added enrichment capabilities")

        except Exception as e:
            self.logger.exception(f"Error adding enrichment capabilities: {e!s}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

        # TODO: Refactor to use centralized database connection and error handling


if __name__ == "__main__":
    """Main entry point for the enrichment capabilities migration script.

    When run as a script, this will:
    1. Initialize logging
    2. Execute the database migration
    3. Log success/failure status

    Example usage:
        python scripts/add_enrichment.py
    """
    script = AddEnrichmentCapabilities()
    script.execute()
