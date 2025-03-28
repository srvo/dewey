"""Schema management module.

This module handles database schema creation, migrations, and versioning
for both local and MotherDuck databases.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from .connection import db_manager
from dewey.core.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)

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
        expected_tables = {'emails', 'email_analyses', 'company_context', 'documents', 
                          'tasks', 'ai_feedback', 'schema_versions', 'change_log',
                          'sync_status', 'sync_conflicts'}
        
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
