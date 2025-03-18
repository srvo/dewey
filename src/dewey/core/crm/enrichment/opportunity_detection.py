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
import pytest
import duckdb
import structlog
import os
import json
from pathlib import Path
from src.dewey.core.crm.enrichment.opportunity_detection import (
    detect_opportunities_in_email,
    update_contact_opportunities,
    detect_opportunities,
    load_config,
    get_duckdb_connection,
    create_contacts_table,
    create_opportunity_processing_table
)
import yaml

@pytest.fixture
def temp_duckdb_conn():
    """Create in-memory DuckDB connection for each test."""
    conn = duckdb.connect(':memory:')
    yield conn
    conn.close()

@pytest.fixture
def mock_config(tmp_path):
    """Create mock config file with custom patterns."""
    config_dir = tmp_path / "dewey" / "config"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "dewey.yaml"
    custom_patterns = {
        "patterns": {
            "demo_request": r"(?i)demo",
            "test_pattern": r"(?i)test"
        }
    }
    with open(config_path, "w") as f:
        yaml.safe_dump({"opportunity_detection": custom_patterns}, f)
    original_path = os.environ.get("DEWEY_CONFIG_PATH")
    os.environ["DEWEY_CONFIG_PATH"] = str(tmp_path)
    yield
    if original_path:
        os.environ["DEWEY_CONFIG_PATH"] = original_path
    else:
        del os.environ["DEWEY_CONFIG_PATH"]

@pytest.fixture
def setup_tables(temp_duckdb_conn):
    """Create necessary database tables."""
    conn = temp_duckdb_conn
    create_contacts_table(conn)
    create_opportunity_processing_table(conn)
    # Create emails table (required by main function)
    conn.execute('''
        CREATE TABLE emails (
            id VARCHAR PRIMARY KEY,
            from_email VARCHAR,
            plain_body TEXT
        )
    ''')
    return conn

def test_detect_opportunities_in_email_positive():
    """Test pattern matching with positive examples."""
    email_body = "Schedule a demo. Cancel old plan. Need pricing info."
    expected = {
        "demo_request": True,
        "cancellation": True,
        "pricing_inquiry": True
    }
    actual = detect_opportunities_in_email(email_body, DEFAULT_PATTERNS)
    assert all([actual[k] == v for k, v in expected.items()])

def test_detect_opportunities_in_email_negative():
    """Test no matches return empty dict."""
    email_body = "This email has no opportunities mentioned"
    result = detect_opportunities_in_email(email_body, DEFAULT_PATTERNS)
    assert not any(result.values())

def test_update_contact_opportunities_new_contact(setup_tables):
    """Test creating new contact with opportunities."""
    conn = setup_tables
    email = "test@example.com"
    opportunities = {"demo_request": True}
    
    update_contact_opportunities(conn, email, opportunities)
    
    # Verify new contact created
    contact = conn.execute("SELECT * FROM contacts WHERE email=?", [email]).fetchone()
    assert contact["has_demo_request"] is True
    assert conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0] == 1

def test_update_contact_opportunities_existing_contact(setup_tables):
    """Test updating existing contact with new opportunities."""
    conn = setup_tables
    email = "existing@example.com"
    initial_ops = {"demo_request": True}
    update_ops = {"cancellation": True}
    
    # Create initial contact
    update_contact_opportunities(conn, email, initial_ops)
    
    # Update with new opportunities
    update_contact_opportunities(conn, email, update_ops)
    
    contact = conn.execute("SELECT * FROM contacts WHERE email=?", [email]).fetchone()
    assert contact["has_demo_request"] is True
    assert contact["has_cancellation"] is True

def test_detect_opportunities_happy_path(setup_tables):
    """Test full workflow with sample emails."""
    conn = setup_tables
    emails_to_insert = [
        ("email1", "user1@example.com", "Schedule demo please"),
        ("email2", "user2@example.com", "Cancel my subscription"),
        ("email3", "user3@example.com", "Need pricing details")
    ]
    conn.executemany(
        "INSERT INTO emails (id, from_email, plain_body) VALUES (?, ?, ?)",
        emails_to_insert
    )
    
    detect_opportunities(batch_size=2, max_emails=3)
    
    processed = conn.execute("SELECT * FROM opportunity_processing").fetchall()
    assert len(processed) == 3
    
    contacts = conn.execute("SELECT * FROM contacts").fetchall()
    assert len(contacts) == 3
    assert any(c["has_demo_request"] for c in contacts)
    assert any(c["has_cancellation"] for c in contacts)
    assert any(c["has_pricing_inquiry"] for c in contacts)

def test_load_config_with_custom_patterns(mock_config):
    """Test loading custom patterns from config file."""
    config = load_config()
    assert "test_pattern" in config["patterns"]
    assert config["patterns"]["demo_request"] == r"(?i)demo"

def test_get_duckdb_connection_motherduck_failure(monkeypatch):
    """Test fallback to local connection when MotherDuck fails."""
    def mock_connect(*args):
        if args[0] == "md:dewey_emails":
            raise Exception("MotherDuck connection failed")
        return duckdb.connect(*args)
    
    monkeypatch.setattr(duckdb, "connect", mock_connect)
    
    conn = get_duckdb_connection()
    assert conn.execute("pragma;").fetchone()["memory"] == True

def test_detect_opportunities_no_emails(setup_tables):
    """Test when no emails to process."""
    detect_opportunities()
    
    count = setup_tables.execute("SELECT COUNT(*) FROM opportunity_processing").fetchone()[0]
    assert count == 0
