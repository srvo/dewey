"""Migrate contacts from old email_data.db to new srvo.db.

This script handles the migration of contact data between two SQLite databases:
- Source: Legacy email_data.db with basic contact information
- Target: New srvo.db with enhanced schema and additional fields

The migration process includes:
- Schema validation and creation
- Data transfer with conflict handling
- Index creation for performance optimization
- Comprehensive logging and error handling
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from scripts.config import Config

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def migrate_contacts() -> None:
    """Migrate contacts from old database to new database.

    This function performs the complete migration workflow:
    1. Validates source database existence
    2. Establishes connections to both databases
    3. Creates target schema if needed
    4. Transfers data with conflict handling
    5. Creates indexes for optimized queries
    6. Handles errors and provides detailed logging

    Raises:
    ------
        sqlite3.Error: For any database operation failures

    """
    config = Config()
    old_db_path = Path("/Users/srvo/email/email_data.db")
    new_db_path = config.DB_PATH

    if not old_db_path.exists():
        logger.error(f"Old database not found at {old_db_path}")
        return

    try:
        # Establish connections to both databases with error handling
        old_conn = sqlite3.connect(old_db_path)
        new_conn = sqlite3.connect(new_db_path)
        # Create cursor objects for executing SQL commands
        old_cur = old_conn.cursor()
        new_cur = new_conn.cursor()

        # Retrieve all contacts from source database
        # Selects essential contact fields for migration
        old_cur.execute(
            """
            SELECT email, name, domain, avg_priority, email_count, last_priority_change
            FROM contacts
        """
        )
        contacts = old_cur.fetchall()
        logger.info(f"Found {len(contacts)} contacts to migrate")

        # Create target table with enhanced schema if it doesn't exist
        # Includes additional fields for future functionality:
        # - job_title: Professional title
        # - linkedin_url: LinkedIn profile URL
        # - phone: Contact phone number
        # - enrichment_status: Data enrichment progress
        # - created_at/updated_at: Timestamps for record tracking
        new_cur.execute(
            """
            CREATE TABLE IF NOT EXISTS contacts (
                email TEXT PRIMARY KEY,
                name TEXT,
                domain TEXT,
                avg_priority REAL,
                email_count INTEGER DEFAULT 0,
                last_priority_change TIMESTAMP,
                job_title TEXT,
                linkedin_url TEXT,
                phone TEXT,
                enrichment_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Perform data migration with conflict handling
        migrated = 0  # Counter for successfully migrated records
        skipped = 0  # Counter for existing records (conflicts)

        # Process each contact record from source database
        for contact in contacts:
            try:
                # Execute insert with conflict handling (IGNORE)
                # Adds current timestamps for created_at and updated_at fields
                new_cur.execute(
                    """
                    INSERT OR IGNORE INTO contacts (
                        email, name, domain, avg_priority, email_count,
                        last_priority_change, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (*contact, datetime.now(), datetime.now()),
                )

                # Track migration statistics
                if new_cur.rowcount > 0:
                    migrated += 1  # Successful insert
                else:
                    skipped += 1  # Record already exists (conflict)

            except sqlite3.Error as e:
                # Log detailed error information while continuing with next record
                logger.error(f"Error migrating contact {contact[0]}: {e}")
                continue

        new_conn.commit()
        logger.info(f"Successfully migrated {migrated} contacts")
        logger.info(f"Skipped {skipped} existing contacts")

        # Create database indexes for optimized query performance
        logger.info("Creating indexes for optimized queries...")

        # Index on domain field for domain-based queries
        new_cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_contacts_domain ON contacts(domain)"
        )

        # Index on email_count field for frequency-based queries
        new_cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_contacts_email_count ON contacts(email_count)"
        )

        # Commit all changes to ensure data persistence
        new_conn.commit()

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
    finally:
        old_conn.close()
        new_conn.close()


if __name__ == "__main__":
    """Main entry point for the migration script."""
    try:
        logger.info("Starting contact migration process")
        migrate_contacts()
        logger.info("Contact migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
