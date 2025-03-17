"""Contact Table Merger

This script handles the migration and merging of contact data from legacy tables
into a new unified schema. It performs the following key operations:
1. Creates backups of original tables
2. Creates new tables with enhanced schema
3. Migrates data from original tables
4. Merges enriched contact data
5. Creates indexes for optimized queries
6. Handles errors and rollbacks safely

The new schema includes:
- UUID primary keys for better data integrity
- Timestamps for tracking data changes
- Support for multiple metadata types
- Enrichment tracking capabilities
- Anonymization support for GDPR compliance
"""

import sqlite3

from scripts.log_config import setup_logger

logger = setup_logger(__name__)


def merge_contact_tables() -> None:
    """Merge original and enriched contact tables into a unified structure.

    This function performs a complete migration of contact data from legacy tables
    to a new schema while preserving all existing data. It handles:
    - Table backups
    - Schema creation
    - Data migration
    - Index creation
    - Error handling and rollback

    The process is atomic - either all changes are committed or none are.

    Raises:
    ------
        Exception: If any error occurs during the migration process

    """
    conn = None
    try:
        logger.info("Connecting to production database")
        conn = sqlite3.connect("email_data.db")
        cursor = conn.cursor()

        # Backup original tables by renaming them with _original suffix
        # This preserves the data while allowing us to create new tables
        logger.info("Creating backup of original tables")
        cursor.execute("ALTER TABLE contacts RENAME TO contacts_original;")
        cursor.execute(
            "ALTER TABLE contact_metadata RENAME TO contact_metadata_original;"
        )

        # Create new contacts table with enhanced schema
        # Includes UUID primary key, timestamps, and enrichment tracking
        logger.info("Creating new contacts table with enhanced schema")
        cursor.execute(
            """
        CREATE TABLE contacts (
            id TEXT PRIMARY KEY,          -- UUID
            email TEXT UNIQUE,            -- For lookups
            name TEXT,
            company TEXT,
            domain TEXT,                  -- Derived from email
            avg_priority REAL,
            email_count INTEGER DEFAULT 0,
            last_priority_change TIMESTAMP,
            first_seen_date TIMESTAMP,
            last_seen_date TIMESTAMP,
            enrichment_status TEXT DEFAULT 'pending',
            last_enriched TIMESTAMP,
            enrichment_source TEXT,
            confidence_score REAL DEFAULT 0.0,
            is_anonymized BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        )

        # Migrate data from original contacts table
        # Generates new UUIDs for each record while preserving existing data
        # Maps old fields to new schema with appropriate defaults
        logger.info("Migrating data from original contacts table")
        cursor.execute(
            """
        INSERT INTO contacts (
            id, email, name, domain, avg_priority,
            email_count, last_priority_change, enrichment_status,
            last_enriched, enrichment_source, confidence_score,
            first_seen_date, created_at
        )
        SELECT
            hex(randomblob(16)), email, name, domain, avg_priority,
            email_count, last_priority_change, enrichment_status,
            last_enriched, enrichment_source, confidence_score,
            last_priority_change, created_at
        FROM contacts_original;
        """
        )

        # Merge enriched contacts into the new table
        # Uses INSERT OR IGNORE to prevent duplicates based on email
        # Preserves all enrichment data from the external source
        logger.info("Merging enriched contacts with conflict resolution")
        cursor.execute(
            """
        INSERT OR IGNORE INTO contacts (
            id, email, name, company, domain,
            first_seen_date, last_seen_date, is_anonymized,
            created_at, updated_at
        )
        SELECT
            contact_id, email, name, company, domain,
            first_seen_date, last_seen_date, is_anonymized,
            created_at, updated_at
        FROM enriched_contacts;
        """
        )

        # Create new metadata table with support for multiple metadata types
        # Includes versioning through valid_from/valid_to timestamps
        # Allows tracking of metadata source and confidence levels
        logger.info("Creating new metadata table with versioning support")
        cursor.execute(
            """
        CREATE TABLE contact_metadata (
            id TEXT PRIMARY KEY,          -- UUID
            contact_id TEXT,
            metadata_type TEXT,           -- job_title, phone, linkedin, etc.
            value TEXT,                   -- The actual metadata value
            confidence REAL,
            source TEXT,                  -- Where this metadata came from
            valid_from TIMESTAMP,         -- For historical tracking
            valid_to TIMESTAMP,           -- NULL means currently valid
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        );
        """
        )

        # Migrate metadata from original table to new schema
        # Converts single-field metadata into type/value pairs
        # Preserves confidence and source information
        logger.info("Migrating metadata to new type/value schema")
        for field in ["job_title", "phone", "linkedin"]:
            cursor.execute(
                f"""
            INSERT INTO contact_metadata (
                id, contact_id, metadata_type, value,
                confidence, source, valid_from, valid_to, created_at
            )
            SELECT
                hex(randomblob(16)), contact_id, '{field}', {field},
                confidence, source, valid_from, valid_to, created_at
            FROM contact_metadata_original
            WHERE {field} IS NOT NULL;
            """
            )

        # Create indexes for optimized query performance
        # Includes indexes on commonly searched fields and foreign keys
        logger.info("Creating indexes for optimized query performance")
        cursor.execute("CREATE INDEX idx_contacts_email ON contacts(email);")
        cursor.execute("CREATE INDEX idx_contacts_domain ON contacts(domain);")
        cursor.execute("CREATE INDEX idx_contacts_company ON contacts(company);")
        cursor.execute(
            "CREATE INDEX idx_contacts_enrichment ON contacts(enrichment_status);"
        )
        cursor.execute(
            "CREATE INDEX idx_contact_metadata_contact ON contact_metadata(contact_id);"
        )
        cursor.execute(
            "CREATE INDEX idx_contact_metadata_type ON contact_metadata(metadata_type);"
        )

        conn.commit()
        logger.info("Successfully merged contact tables")

    except Exception as e:
        logger.error(f"Error merging contact tables: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    """Main entry point for the contact table merge process."""
    try:
        logger.info("Starting contact table merge process")
        merge_contact_tables()
        logger.info("Contact table merge completed successfully")
    except Exception as e:
        logger.critical(f"Contact table merge failed: {str(e)}")
        raise
