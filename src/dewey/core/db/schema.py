"""Schema management module.

This module handles database schema creation, migrations, and versioning
for both local and MotherDuck databases.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from .connection import db_manager, DatabaseConnectionError

logger = logging.getLogger(__name__)

# Schema version tracking table
SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_versions (
    id INTEGER PRIMARY KEY,
    version INTEGER NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    checksum VARCHAR(64),
    status TEXT DEFAULT 'pending',
    error_message TEXT
)
"""

# Change tracking tables
CHANGE_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS change_log (
    id INTEGER PRIMARY KEY,
    table_name VARCHAR NOT NULL,
    operation VARCHAR NOT NULL,
    record_id VARCHAR NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR,
    details JSON
)
"""

SYNC_STATUS_TABLE = """
CREATE TABLE IF NOT EXISTS sync_status (
    id INTEGER PRIMARY KEY,
    sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR NOT NULL,
    message TEXT,
    details JSON
)
"""

SYNC_CONFLICTS_TABLE = """
CREATE TABLE IF NOT EXISTS sync_conflicts (
    id INTEGER PRIMARY KEY,
    table_name VARCHAR NOT NULL,
    record_id VARCHAR NOT NULL,
    operation VARCHAR NOT NULL,
    error_message TEXT,
    sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE,
    resolution_time TIMESTAMP,
    resolution_details JSON
)
"""

# Core tables
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
    to_addresses JSON,
    cc_addresses JSON,
    bcc_addresses JSON,
    received_date TIMESTAMP,
    labels JSON,
    size_estimate INTEGER,
    is_draft BOOLEAN,
    is_sent BOOLEAN,
    is_read BOOLEAN,
    is_starred BOOLEAN,
    is_trashed BOOLEAN,
    attachments JSON,
    raw_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    analysis_date TIMESTAMP,
    raw_analysis JSON,
    automation_score FLOAT,
    content_value FLOAT,
    human_interaction FLOAT,
    time_value FLOAT,
    business_impact FLOAT,
    uncertainty_score FLOAT,
    metadata JSON,
    priority INTEGER,
    label_ids JSON,
    snippet TEXT,
    internal_date BIGINT,
    size_estimate INTEGER,
    message_parts JSON,
    draft_id VARCHAR,
    draft_message JSON,
    attachments JSON
)
"""

COMPANY_CONTEXT_TABLE = """
CREATE TABLE IF NOT EXISTS company_context (
    id VARCHAR PRIMARY KEY,
    company_name VARCHAR NOT NULL,
    context_text TEXT,
    source VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
)
"""

DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR PRIMARY KEY,
    title VARCHAR,
    content TEXT,
    content_type VARCHAR,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    due_date TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# List of all tables and their creation SQL
TABLES = {
    'schema_versions': SCHEMA_VERSION_TABLE,
    'change_log': CHANGE_LOG_TABLE,
    'sync_status': SYNC_STATUS_TABLE,
    'sync_conflicts': SYNC_CONFLICTS_TABLE,
    'emails': EMAILS_TABLE,
    'email_analyses': EMAIL_ANALYSES_TABLE,
    'company_context': COMPANY_CONTEXT_TABLE,
    'documents': DOCUMENTS_TABLE,
    'tasks': TASKS_TABLE
}

def initialize_schema(local_only: bool = False):
    """Initialize the database schema.
    
    Args:
        local_only: Whether to only initialize the local database
    """
    try:
        # Create tables in local database
        for table_name, create_sql in TABLES.items():
            db_manager.execute_query(create_sql, for_write=True, local_only=True)
            logger.info(f"Created table {table_name} in local database")
            
        if not local_only:
            # Create tables in MotherDuck
            for table_name, create_sql in TABLES.items():
                db_manager.execute_query(create_sql, for_write=True, local_only=False)
                logger.info(f"Created table {table_name} in MotherDuck")
                
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to initialize schema: {e}")
        
def get_current_version(local_only: bool = False) -> int:
    """Get the current schema version.
    
    Args:
        local_only: Whether to only check the local database
        
    Returns:
        Current schema version number
    """
    try:
        result = db_manager.execute_query("""
            SELECT MAX(version) FROM schema_versions
            WHERE status = 'success'
        """, local_only=local_only)
        
        return result[0][0] if result and result[0][0] else 0
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to get schema version: {e}")
        
def apply_migration(version: int, description: str, sql: str, local_only: bool = False):
    """Apply a schema migration.
    
    Args:
        version: Migration version number
        description: Migration description
        sql: SQL statements to execute
        local_only: Whether to only apply to local database
    """
    try:
        # Start transaction
        db_manager.execute_query("BEGIN TRANSACTION", for_write=True, local_only=local_only)
        
        try:
            # Execute migration SQL
            db_manager.execute_query(sql, for_write=True, local_only=local_only)
            
            # Record successful migration
            db_manager.execute_query("""
                INSERT INTO schema_versions (
                    version, description, status, applied_at
                ) VALUES (?, ?, 'success', CURRENT_TIMESTAMP)
            """, [version, description], for_write=True, local_only=local_only)
            
            # Commit transaction
            db_manager.execute_query("COMMIT", for_write=True, local_only=local_only)
            
            logger.info(f"Successfully applied migration {version}: {description}")
            
        except Exception as e:
            # Record failed migration
            db_manager.execute_query("""
                INSERT INTO schema_versions (
                    version, description, status, error_message, applied_at
                ) VALUES (?, ?, 'failed', ?, CURRENT_TIMESTAMP)
            """, [version, description, str(e)], for_write=True, local_only=local_only)
            
            # Rollback transaction
            db_manager.execute_query("ROLLBACK", for_write=True, local_only=local_only)
            
            raise DatabaseConnectionError(f"Migration {version} failed: {e}")
            
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to apply migration: {e}")
        
def verify_schema_consistency():
    """Verify that local and MotherDuck schemas are consistent."""
    try:
        # Get schema versions
        local_version = get_current_version(local_only=True)
        md_version = get_current_version(local_only=False)
        
        if local_version != md_version:
            raise DatabaseConnectionError(
                f"Schema version mismatch: local={local_version}, MotherDuck={md_version}"
            )
            
        # Compare table structures
        for table_name in TABLES:
            local_schema = db_manager.execute_query(
                f"DESCRIBE {table_name}", local_only=True
            )
            md_schema = db_manager.execute_query(
                f"DESCRIBE {table_name}", local_only=False
            )
            
            if local_schema != md_schema:
                raise DatabaseConnectionError(
                    f"Schema mismatch for table {table_name}"
                )
                
        logger.info("Schema consistency verified")
        return True
        
    except Exception as e:
        logger.error(f"Schema consistency check failed: {e}")
        return False 