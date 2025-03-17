#!/usr/bin/env python3
"""
Opportunity Detection Module

This module analyzes email content to detect business opportunities.
"""

import re
import os
import json
import logging
import duckdb
import uuid
import yaml
import structlog
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

# Default regex patterns for opportunity detection
DEFAULT_PATTERNS = {
    "demo_request": r"(?i)(?:would like|interested in|request|schedule|book)(?:.{0,30})(?:demo|demonstration|product tour|walkthrough)",
    "cancellation": r"(?i)(?:cancel|terminate|end|discontinue)(?:.{0,30})(?:subscription|service|account|contract)",
    "speaking_opportunity": r"(?i)(?:speak|talk|present|keynote|panel)(?:.{0,30})(?:conference|event|webinar|meetup|summit)",
    "publicity_opportunity": r"(?i)(?:feature|highlight|showcase|interview|article)(?:.{0,30})(?:blog|publication|magazine|podcast|press)",
    "partnership_request": r"(?i)(?:partner|collaborate|alliance|joint venture|work together)(?:.{0,30})(?:opportunity|proposal|idea|initiative)",
    "pricing_inquiry": r"(?i)(?:pricing|quote|cost|price|fee)(?:.{0,30})(?:information|details|structure|model|plan)"
}

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_path = os.path.expanduser("~/dewey/config/dewey.yaml")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                return config.get("opportunity_detection", {})
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

def detect_opportunities_in_email(email_body: str, patterns: Dict[str, str]) -> Dict[str, bool]:
    """
    Detect business opportunities in email content using regex patterns.
    
    Args:
        email_body: The plain text body of the email
        patterns: Dictionary of regex patterns for different opportunity types
        
    Returns:
        Dictionary of opportunity types and boolean values
    """
    opportunities = {}
    
    if not email_body:
        return opportunities
    
    # Check each pattern
    for opportunity_type, pattern in patterns.items():
        match = re.search(pattern, email_body)
        opportunities[opportunity_type] = bool(match)
    
    return opportunities

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

def create_opportunity_processing_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the opportunity_processing table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS opportunity_processing (
            email_id VARCHAR PRIMARY KEY,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            opportunities JSON
        )
    """)

def update_contact_opportunities(conn: duckdb.DuckDBPyConnection, email: str, opportunities: Dict[str, bool]) -> None:
    """
    Update contact record with opportunity flags.
    
    Args:
        conn: DuckDB connection
        email: Email address of the contact
        opportunities: Dictionary of opportunity types and boolean values
    """
    # Check if contact exists
    result = conn.execute(
        "SELECT id FROM contacts WHERE email = ?", [email]
    ).fetchone()
    
    if not result:
        # Create new contact if it doesn't exist
        contact_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO contacts (id, email, created_at, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            [contact_id, email]
        )
        logger.info(f"Created new contact for {email}")
    else:
        contact_id = result[0]
    
    # Update contact with opportunity flags
    set_clauses = []
    params = []
    
    for opportunity_type, detected in opportunities.items():
        if detected:
            field_name = f"has_{opportunity_type}"
            set_clauses.append(f"{field_name} = ?")
            params.append(True)
    
    if set_clauses:
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        
        # Add opportunity fields to contacts table if they don't exist
        for opportunity_type in opportunities.keys():
            field_name = f"has_{opportunity_type}"
            try:
                conn.execute(f"ALTER TABLE contacts ADD COLUMN IF NOT EXISTS {field_name} BOOLEAN DEFAULT FALSE")
            except Exception as e:
                logger.error(f"Error adding column {field_name}: {str(e)}")
        
        # Update contact
        query = f"""
            UPDATE contacts 
            SET {', '.join(set_clauses)}
            WHERE id = ?
        """
        params.append(contact_id)
        conn.execute(query, params)
        
        if any(opportunities.values()):
            logger.info(f"Updated contact {email} with opportunities: {', '.join([k for k, v in opportunities.items() if v])}")

def detect_opportunities(batch_size: int = 50, max_emails: int = 100) -> None:
    """
    Detect business opportunities in emails.
    
    Args:
        batch_size: Number of emails to process in each batch
        max_emails: Maximum number of emails to process
    """
    logger.info(f"Starting opportunity detection (batch_size={batch_size}, max_emails={max_emails})")
    
    # Load configuration
    config = load_config()
    patterns = config.get("patterns", DEFAULT_PATTERNS)
    
    try:
        # Connect to database
        conn = get_duckdb_connection()
        
        # Create tables if they don't exist
        create_contacts_table(conn)
        create_opportunity_processing_table(conn)
        
        # Get emails that haven't been processed for opportunity detection
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW emails_for_opportunity_detection AS
            SELECT e.id, e.from_email, e.plain_body
            FROM emails e
            LEFT JOIN opportunity_processing op ON e.id = op.email_id
            WHERE op.email_id IS NULL
            AND e.plain_body IS NOT NULL
            LIMIT ?
        """, [max_emails])
        
        # Get count
        count = conn.execute("SELECT COUNT(*) FROM emails_for_opportunity_detection").fetchone()[0]
        logger.info(f"Found {count} emails for opportunity detection")
        
        if count == 0:
            logger.info("No emails to process")
            return
        
        # Process in batches
        processed_count = 0
        for offset in range(0, count, batch_size):
            batch = conn.execute(f"""
                SELECT id, from_email, plain_body
                FROM emails_for_opportunity_detection
                LIMIT {batch_size} OFFSET {offset}
            """).fetchall()
            
            logger.info(f"Processing batch of {len(batch)} emails (offset {offset})")
            
            for row in batch:
                email_id, from_email, plain_body = row
                
                # Detect opportunities
                opportunities = detect_opportunities_in_email(plain_body, patterns)
                
                # Update contact with opportunity flags
                update_contact_opportunities(conn, from_email, opportunities)
                
                # Mark email as processed
                conn.execute(
                    "INSERT INTO opportunity_processing (email_id, opportunities) VALUES (?, ?)",
                    [email_id, json.dumps(opportunities)]
                )
                
                processed_count += 1
            
            # Commit after each batch
            conn.commit()
        
        logger.info(f"Processed {processed_count} emails for opportunity detection")
    
    except Exception as e:
        logger.error(f"Error in opportunity detection: {str(e)}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Detect business opportunities in emails")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing emails")
    parser.add_argument("--max-emails", type=int, default=100, help="Maximum number of emails to process")
    
    args = parser.parse_args()
    
    detect_opportunities(batch_size=args.batch_size, max_emails=args.max_emails)
