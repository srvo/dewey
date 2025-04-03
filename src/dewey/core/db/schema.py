"""Schema management module.

This module handles database schema creation, migrations, and versioning
for PostgreSQL databases.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .connection import db_manager
from dewey.core.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)

# List of all tables that should exist in the database
TABLES = [
    "emails",
    "email_analyses",
    "company_context",
    "documents",
    "tasks",
    "ai_feedback",
    "schema_versions",
    "change_log",
    "sync_status",
    "sync_conflicts",
]

# Schema version tracking table (PostgreSQL compatible)
SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_versions (
    id SERIAL PRIMARY KEY,
    version INTEGER NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    checksum VARCHAR(64),
    status TEXT DEFAULT 'pending',
    error_message TEXT
)
"""

# Change tracking tables (PostgreSQL compatible)
CHANGE_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS change_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR NOT NULL,
    operation VARCHAR NOT NULL,
    record_id VARCHAR NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR,
    details JSONB
)
"""

SYNC_STATUS_TABLE = """
CREATE TABLE IF NOT EXISTS sync_status (
    id SERIAL PRIMARY KEY,
    sync_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR NOT NULL,
    message TEXT,
    details JSONB
)
"""

SYNC_CONFLICTS_TABLE = """
CREATE TABLE IF NOT EXISTS sync_conflicts (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR NOT NULL,
    record_id VARCHAR NOT NULL,
    operation VARCHAR NOT NULL,
    error_message TEXT,
    sync_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE,
    resolution_time TIMESTAMP WITH TIME ZONE,
    resolution_details JSONB
)
"""

# Core tables (PostgreSQL compatible)
EMAILS_TABLE = """
CREATE TABLE IF NOT EXISTS emails (
    id VARCHAR PRIMARY KEY,
    thread_id VARCHAR,
    subject VARCHAR,
    snippet VARCHAR,
    body_text TEXT,
    body_html TEXT,
    from_name VARCHAR,
    from_email VARCHAR,
    to_addresses JSONB,
    cc_addresses JSONB,
    bcc_addresses JSONB,
    received_date TIMESTAMP WITH TIME ZONE,
    labels JSONB,
    size_estimate INTEGER,
    is_draft BOOLEAN,
    is_sent BOOLEAN,
    is_read BOOLEAN,
    is_starred BOOLEAN,
    is_trashed BOOLEAN,
    attachments JSONB,
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    error_message VARCHAR,
    status VARCHAR DEFAULT 'new'
)
"""

EMAIL_ANALYSES_TABLE = """
CREATE TABLE IF NOT EXISTS email_analyses (
    msg_id VARCHAR PRIMARY KEY,
    thread_id VARCHAR,
    subject VARCHAR,
    from_address VARCHAR,
    analysis_date TIMESTAMP WITH TIME ZONE,
    raw_analysis JSONB,
    automation_score FLOAT,
    content_value FLOAT,
    human_interaction FLOAT,
    time_value FLOAT,
    business_impact FLOAT,
    uncertainty_score FLOAT,
    metadata JSONB,
    priority INTEGER,
    label_ids JSONB,
    snippet TEXT,
    internal_date BIGINT,
    size_estimate INTEGER,
    message_parts JSONB,
    draft_id VARCHAR,
    draft_message JSONB,
    attachments JSONB
)
"""

COMPANY_CONTEXT_TABLE = """
CREATE TABLE IF NOT EXISTS company_context (
    id VARCHAR PRIMARY KEY,
    company_name VARCHAR NOT NULL,
    context_text TEXT,
    source VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
)
"""

DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR PRIMARY KEY,
    title VARCHAR,
    content TEXT,
    content_type VARCHAR,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR DEFAULT 'new'
)
"""

TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    description TEXT,
    status VARCHAR DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    due_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
)
"""

AI_FEEDBACK_TABLE = """
CREATE TABLE IF NOT EXISTS ai_feedback (
    id VARCHAR PRIMARY KEY,
    source_table VARCHAR NOT NULL,
    source_id VARCHAR NOT NULL,
    feedback_type VARCHAR NOT NULL,
    feedback_content JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_details JSONB,
    resolution_status VARCHAR DEFAULT 'pending'
)
"""


def initialize_schema():
    """Initialize the database schema by creating all required tables.

    This will ensure all tables defined in the schema are created if they don't exist.
    """
    try:
        # First create schema version tracking table
        db_manager.execute_query(SCHEMA_VERSION_TABLE)
        logger.info("Schema version table initialized")

        # Create change tracking tables
        db_manager.execute_query(CHANGE_LOG_TABLE)
        db_manager.execute_query(SYNC_STATUS_TABLE)
        db_manager.execute_query(SYNC_CONFLICTS_TABLE)
        logger.info("Change tracking tables initialized")

        # Create core tables
        db_manager.execute_query(EMAILS_TABLE)
        db_manager.execute_query(EMAIL_ANALYSES_TABLE)
        db_manager.execute_query(COMPANY_CONTEXT_TABLE)
        db_manager.execute_query(DOCUMENTS_TABLE)
        db_manager.execute_query(TASKS_TABLE)
        db_manager.execute_query(AI_FEEDBACK_TABLE)
        logger.info("Core tables initialized")

        # If no version record exists, insert initial version
        current_version = get_current_version()
        if current_version == 0:
            db_manager.execute_query(
                """
                INSERT INTO schema_versions (version, description, status)
                VALUES (1, 'Initial schema creation', 'applied')
                """
            )
            logger.info("Set initial schema version to 1")

        return True
    except Exception as e:
        logger.error(f"Failed to initialize schema: {e}")
        return False


def get_current_version() -> int:
    """Get the current schema version from the database.

    Returns:
        int: The current schema version, or 0 if no version exists

    """
    try:
        result = db_manager.execute_query(
            """
            SELECT MAX(version) FROM schema_versions
            WHERE status = 'applied'
            """
        )
        if result and result[0][0] is not None:
            return result[0][0]
        return 0
    except Exception as e:
        logger.error(f"Failed to get current schema version: {e}")
        return 0


def apply_migration(version: int, description: str, sql_statements: list[str]) -> bool:
    """Apply a database migration.

    Args:
        version: The version number to migrate to
        description: Description of the migration
        sql_statements: List of SQL statements to execute

    Returns:
        bool: True if migration was successful, False otherwise

    """
    current_version = get_current_version()
    if version <= current_version:
        logger.warning(
            f"Migration to version {version} skipped (current: {current_version})"
        )
        return False

    # Record migration attempt
    try:
        db_manager.execute_query(
            """
            INSERT INTO schema_versions (version, description, status)
            VALUES (%s, %s, %s)
            """,
            (version, description, "pending"),
        )

        # Execute each SQL statement
        for statement in sql_statements:
            db_manager.execute_query(statement)

        # Update migration status
        db_manager.execute_query(
            """
            UPDATE schema_versions
            SET status = 'applied', applied_at = CURRENT_TIMESTAMP
            WHERE version = %s
            """,
            (version,),
        )

        logger.info(f"Successfully applied migration to version {version}")
        return True
    except Exception as e:
        # Record error
        db_manager.execute_query(
            """
            UPDATE schema_versions
            SET status = 'failed', error_message = %s
            WHERE version = %s
            """,
            (str(e), version),
        )
        logger.error(f"Failed to apply migration to version {version}: {e}")
        return False


def verify_schema_consistency():
    """Verify schema consistency using PostgreSQL information schema."""
    try:
        # Get table list from PostgreSQL
        result = db_manager.execute_query("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        postgres_tables = {row[0] for row in result} if result else set()

        # Compare against expected tables
        expected_tables = {
            "emails",
            "email_analyses",
            "company_context",
            "documents",
            "tasks",
            "ai_feedback",
            "schema_versions",
            "change_log",
            "sync_status",
            "sync_conflicts",
        }

        missing_tables = expected_tables - postgres_tables
        if missing_tables:
            raise DatabaseConnectionError(
                f"Missing tables: {', '.join(missing_tables)}"
            )

        # Verify table structures
        for table_name in expected_tables:
            # Get column info from PostgreSQL
            columns = db_manager.execute_query(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)

            # Compare with expected schema (would need schema definition)
            # This is simplified - would need actual schema definition to compare
            if not columns:
                raise DatabaseConnectionError(
                    f"Table {table_name} exists but has no columns"
                )

        logger.info("Schema consistency verified")
        return True

    except Exception as e:
        logger.error(f"Schema consistency check failed: {e}")
        return False


__all__ = [
    "TABLES",
    "initialize_schema",
    "get_current_version",
    "apply_migration",
    "verify_schema_consistency",
]
