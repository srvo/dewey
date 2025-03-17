#!/usr/bin/env python3
"""
Contact Enrichment Module

This module extracts contact information from emails and enriches the contacts database.
"""

import re
import uuid
import logging
import duckdb
import os
import yaml
import structlog
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

# Default regex patterns for contact extraction
DEFAULT_PATTERNS = {
    "name": r"(?:^|\n)([A-Z][a-z]+(?: [A-Z][a-z]+)+)(?:\n|$)",
    "job_title": r"(?:^|\n)([A-Za-z]+(?:\s+[A-Za-z]+){0,3}?)(?:\s+at\s+|\s*[,|]\s*)",
    "company": r"(?:at|@|with)\s+([A-Z][A-Za-z0-9\s&]+(?:Inc|LLC|Ltd|Co|Corp|Corporation|Company))",
    "phone": r"(?:Phone|Tel|Mobile|Cell)(?::|.)?(?:\s+)?((?:\+\d{1,3}[-\.\s]?)?(?:\(?\d{3}\)?[-\.\s]?)?\d{3}[-\.\s]?\d{4})",
    "linkedin_url": r"(?:LinkedIn|Profile)(?::|.)?(?:\s+)?(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)"
}

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_path = os.path.expanduser("~/dewey/config/dewey.yaml")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                return config.get("contact_extraction", {})
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
    return {}

def get_duckdb_connection(db_path: Optional[str] = None) -> duckdb.DuckDBPyConnection:
    """Get a connection to the DuckDB database."""
    if db_path is None:
        db_path = os.path.expanduser("~/dewey_emails.duckdb")
    
    try:
        # Try to connect to MotherDuck first
        try:
            conn = duckdb.connect("md:dewey_emails")
            logger.info("Connected to MotherDuck")
            return conn
        except Exception as e:
            logger.warning(f"Failed to connect to MotherDuck: {str(e)}")
            
        # Fall back to local database
        conn = duckdb.connect(db_path)
        logger.info(f"Connected to local database at {db_path}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        # Create a new in-memory database as a last resort
        logger.warning("Creating in-memory database")
        return duckdb.connect(":memory:")

def extract_contact_info(email_body: str, patterns: Dict[str, str]) -> Dict[str, str]:
    """
    Extract contact information from email body using regex patterns.
    
    Args:
        email_body: The plain text body of the email
        patterns: Dictionary of regex patterns for different contact fields
        
    Returns:
        Dictionary of extracted contact information
    """
    contact_info = {}
    
    if not email_body:
        return contact_info
    
    # Extract each field using the corresponding pattern
    for field, pattern in patterns.items():
        match = re.search(pattern, email_body)
        if match:
            contact_info[field] = match.group(1).strip()
    
    return contact_info

def create_contacts_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the contacts table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id VARCHAR PRIMARY KEY,
            name VARCHAR,
            email VARCHAR,
            job_title VARCHAR,
            company VARCHAR,
            phone VARCHAR,
            linkedin_url VARCHAR,
            last_contact_date TIMESTAMP,
            email_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def update_contact(conn: duckdb.DuckDBPyConnection, email: str, contact_info: Dict[str, str]) -> str:
    """
    Update or create a contact in the database.
    
    Args:
        conn: DuckDB connection
        email: Email address of the contact
        contact_info: Dictionary of contact information
        
    Returns:
        ID of the updated or created contact
    """
    # Check if contact already exists
    result = conn.execute(
        "SELECT id FROM contacts WHERE email = ?", [email]
    ).fetchone()
    
    contact_id = result[0] if result else str(uuid.uuid4())
    
    if result:
        # Update existing contact
        set_clauses = []
        params = []
        
        for field, value in contact_info.items():
            if value:
                set_clauses.append(f"{field} = ?")
                params.append(value)
        
        if set_clauses:
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            set_clauses.append("email_count = email_count + 1")
            set_clauses.append("last_contact_date = CURRENT_TIMESTAMP")
            
            query = f"""
                UPDATE contacts 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """
            params.append(contact_id)
            conn.execute(query, params)
            logger.info(f"Updated contact: {email}")
    else:
        # Create new contact
        fields = ["id", "email"]
        values = [contact_id, email]
        
        for field, value in contact_info.items():
            if value:
                fields.append(field)
                values.append(value)
        
        fields.extend(["created_at", "updated_at", "email_count", "last_contact_date"])
        values.extend(["CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP", 1, "CURRENT_TIMESTAMP"])
        
        query = f"""
            INSERT INTO contacts ({', '.join(fields)})
            VALUES ({', '.join(['?'] * len(values))})
        """
        conn.execute(query, values)
        logger.info(f"Created new contact: {email}")
    
    return contact_id

def create_contact_processing_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the contact_processing table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contact_processing (
            email_id VARCHAR PRIMARY KEY,
            contact_id VARCHAR,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    """)

def enrich_contacts(batch_size: int = 50, max_emails: int = 100) -> None:
    """
    Extract and enrich contact information from emails.
    
    Args:
        batch_size: Number of emails to process in each batch
        max_emails: Maximum number of emails to process
    """
    logger.info(f"Starting contact enrichment (batch_size={batch_size}, max_emails={max_emails})")
    
    # Load configuration
    config = load_config()
    patterns = config.get("patterns", DEFAULT_PATTERNS)
    
    try:
        # Connect to database
        conn = get_duckdb_connection()
        
        # Create tables if they don't exist
        create_contacts_table(conn)
        create_contact_processing_table(conn)
        
        # Get emails that haven't been processed for contact extraction
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW emails_for_contact_extraction AS
            SELECT e.id, e.from_email, e.plain_body
            FROM emails e
            LEFT JOIN contact_processing cp ON e.id = cp.email_id
            WHERE cp.email_id IS NULL
            AND e.plain_body IS NOT NULL
            LIMIT ?
        """, [max_emails])
        
        # Get count
        count = conn.execute("SELECT COUNT(*) FROM emails_for_contact_extraction").fetchone()[0]
        logger.info(f"Found {count} emails for contact extraction")
        
        if count == 0:
            logger.info("No emails to process")
            return
        
        # Process in batches
        processed_count = 0
        for offset in range(0, count, batch_size):
            batch = conn.execute(f"""
                SELECT id, from_email, plain_body
                FROM emails_for_contact_extraction
                LIMIT {batch_size} OFFSET {offset}
            """).fetchall()
            
            logger.info(f"Processing batch of {len(batch)} emails (offset {offset})")
            
            for row in batch:
                email_id, from_email, plain_body = row
                
                # Extract contact information
                contact_info = extract_contact_info(plain_body, patterns)
                
                # Update or create contact
                contact_id = update_contact(conn, from_email, contact_info)
                
                # Mark email as processed
                conn.execute(
                    "INSERT INTO contact_processing (email_id, contact_id) VALUES (?, ?)",
                    [email_id, contact_id]
                )
                
                processed_count += 1
            
            # Commit after each batch
            conn.commit()
        
        logger.info(f"Processed {processed_count} emails for contact extraction")
    
    except Exception as e:
        logger.error(f"Error in contact enrichment: {str(e)}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract and enrich contact information from emails")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing emails")
    parser.add_argument("--max-emails", type=int, default=100, help="Maximum number of emails to process")
    
    args = parser.parse_args()
    
    enrich_contacts(batch_size=args.batch_size, max_emails=args.max_emails)


