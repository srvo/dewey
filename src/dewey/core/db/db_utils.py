"""Database utility functions for the Dewey project.

This module provides helper functions for common database operations.
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional, Union

import duckdb

from .database import get_duckdb_connection, ensure_table_exists
from .models import TABLE_SCHEMAS, TABLE_INDEXES

logger = logging.getLogger(__name__)


def initialize_crm_database(
    database_name: str = "crm.duckdb",
    data_dir: Optional[str] = None,
    existing_db_path: Optional[str] = None
) -> duckdb.DuckDBPyConnection:
    """Initialize the CRM database with all required tables.
    
    Args:
        database_name: Name of the database file
        data_dir: Directory to store the database file
        existing_db_path: Path to an existing database file to use instead
        
    Returns:
        A DuckDB connection to the initialized database
    """
    # Check if we should use an existing database file
    if existing_db_path and os.path.exists(existing_db_path):
        logger.info(f"Using existing database at {existing_db_path}")
        try:
            # Get a connection to the existing database
            conn = duckdb.connect(existing_db_path)
            return conn
        except Exception as e:
            logger.warning(f"Failed to connect to existing database at {existing_db_path}: {e}")
            logger.info("Falling back to creating a new database")
    
    # Get a connection to the database
    conn = get_duckdb_connection(database_name=database_name, data_dir=data_dir)
    
    # Create tables if they don't exist
    for table_name, schema_sql in TABLE_SCHEMAS.items():
        ensure_table_exists(conn, table_name, schema_sql)
    
    # Create indexes
    for table_name, indexes in TABLE_INDEXES.items():
        for index_sql in indexes:
            try:
                conn.execute(index_sql)
            except Exception as e:
                logger.warning(f"Error creating index: {e}")
    
    return conn


def check_database_schema(db_path: str) -> Dict[str, List[str]]:
    """Check the schema of an existing database.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        Dictionary with table names as keys and lists of column names as values
    """
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return {}
    
    try:
        conn = duckdb.connect(db_path, read_only=True)
        
        # Get list of tables
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        
        schema = {}
        for table in tables:
            table_name = table[0]
            # Get columns for each table
            columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            schema[table_name] = [col[1] for col in columns]  # col[1] is the column name
        
        conn.close()
        return schema
        
    except Exception as e:
        logger.error(f"Error checking database schema: {e}")
        return {}


def store_email(
    conn: duckdb.DuckDBPyConnection,
    email_data: Dict[str, Any]
) -> bool:
    """Store an email in the database.
    
    Args:
        conn: DuckDB connection
        email_data: Dictionary containing email data
        
    Returns:
        True if the email was stored successfully, False otherwise
    """
    try:
        # Check if email already exists
        result = conn.execute(
            "SELECT msg_id FROM email_analyses WHERE msg_id = ?",
            [email_data.get('id')]
        ).fetchone()
        
        if result:
            logger.info(f"Email {email_data.get('id')} already exists in database")
            return False
        
        # Prepare data for insertion
        params = [
            email_data.get('id'),
            email_data.get('threadId'),
            email_data.get('subject', ''),
            email_data.get('from', ''),
            email_data.get('analysis_date', ''),
            json.dumps(email_data.get('raw_analysis', {})),
            email_data.get('automation_score', 0.0),
            email_data.get('content_value', 0.0),
            email_data.get('human_interaction', 0.0),
            email_data.get('time_value', 0.0),
            email_data.get('business_impact', 0.0),
            email_data.get('uncertainty_score', 0.0),
            json.dumps(email_data.get('metadata', {})),
            email_data.get('priority', 0),
            json.dumps(email_data.get('labelIds', [])),
            email_data.get('snippet', ''),
            int(email_data.get('internalDate', 0)),
            int(email_data.get('sizeEstimate', 0)),
            json.dumps(email_data.get('message_parts', {})),
            email_data.get('draftId'),
            json.dumps(email_data.get('draftMessage', {})) if email_data.get('draftMessage') else None,
            json.dumps(email_data.get('attachments', []))
        ]
        
        # Insert email
        conn.execute("""
            INSERT INTO email_analyses
            (msg_id, thread_id, subject, from_address, analysis_date, raw_analysis,
             automation_score, content_value, human_interaction, time_value, business_impact,
             uncertainty_score, metadata, priority, label_ids, snippet, internal_date,
             size_estimate, message_parts, draft_id, draft_message, attachments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, params)
        
        logger.info(f"Stored email {email_data.get('id')} in database")
        return True
        
    except Exception as e:
        logger.error(f"Error storing email {email_data.get('id')}: {e}")
        return False


def store_contact(
    conn: duckdb.DuckDBPyConnection,
    contact_data: Dict[str, Any]
) -> Optional[int]:
    """Store a contact in the database.
    
    Args:
        conn: DuckDB connection
        contact_data: Dictionary containing contact data
        
    Returns:
        Contact ID if stored successfully, None otherwise
    """
    try:
        # Check if contact already exists
        result = conn.execute(
            "SELECT id, first_seen FROM contacts WHERE email = ?",
            [contact_data.get('email')]
        ).fetchone()
        
        if result:
            contact_id, first_seen = result
            
            # Update last_seen
            conn.execute(
                "UPDATE contacts SET last_seen = ?, name = COALESCE(?, name) WHERE id = ?",
                [
                    contact_data.get('last_seen'),
                    contact_data.get('name'),
                    contact_id
                ]
            )
            
            logger.debug(f"Updated contact {contact_data.get('email')} in database")
            return contact_id
        
        # Insert new contact
        conn.execute("""
            INSERT INTO contacts
            (name, email, company, title, phone, linkedin, first_seen, last_seen, notes, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            contact_data.get('name'),
            contact_data.get('email'),
            contact_data.get('company'),
            contact_data.get('title'),
            contact_data.get('phone'),
            contact_data.get('linkedin'),
            contact_data.get('first_seen'),
            contact_data.get('last_seen'),
            contact_data.get('notes'),
            json.dumps(contact_data.get('metadata', {}))
        ])
        
        # Get the ID of the inserted contact
        result = conn.execute(
            "SELECT id FROM contacts WHERE email = ?",
            [contact_data.get('email')]
        ).fetchone()
        
        if result:
            logger.info(f"Stored contact {contact_data.get('email')} in database")
            return result[0]
        
        return None
        
    except Exception as e:
        logger.error(f"Error storing contact {contact_data.get('email')}: {e}")
        return None 