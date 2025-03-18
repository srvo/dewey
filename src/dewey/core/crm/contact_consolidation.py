#!/usr/bin/env python3
"""
Contact Consolidation Script
===========================

This script consolidates contact information from various tables in the MotherDuck database
into a single unified_contacts table, focusing on individuals.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import duckdb

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"contact_consolidation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("contact_consolidation")

def connect_to_motherduck(database_name: str = "dewey") -> duckdb.DuckDBPyConnection:
    """Connect to the MotherDuck database.
    
    Args:
        database_name: Name of the MotherDuck database
        
    Returns:
        DuckDB connection
    """
    try:
        conn = duckdb.connect(f"md:{database_name}")
        logger.info(f"Connected to MotherDuck database: {database_name}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to MotherDuck database: {e}")
        raise

def create_unified_contacts_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the unified_contacts table if it doesn't exist.
    
    Args:
        conn: DuckDB connection
    """
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS unified_contacts (
            email VARCHAR PRIMARY KEY,
            first_name VARCHAR,
            last_name VARCHAR,
            full_name VARCHAR,
            company VARCHAR,
            job_title VARCHAR,
            phone VARCHAR,
            country VARCHAR,
            source VARCHAR,
            domain VARCHAR,
            last_interaction_date TIMESTAMP,
            first_seen_date TIMESTAMP,
            last_updated TIMESTAMP,
            tags VARCHAR,
            notes VARCHAR,
            metadata JSON
        )
        """)
        logger.info("Created or verified unified_contacts table")
    except Exception as e:
        logger.error(f"Error creating unified_contacts table: {e}")
        raise

def extract_contacts_from_crm(conn: duckdb.DuckDBPyConnection) -> List[Dict]:
    """Extract contacts from CRM-related tables.
    
    Args:
        conn: DuckDB connection
        
    Returns:
        List of contact dictionaries
    """
    try:
        # We'll use crm_contacts as the primary source since all three CRM tables have the same schema
        result = conn.execute("""
        SELECT 
            email,
            name as full_name,
            CASE 
                WHEN POSITION(' ' IN name) > 0 
                THEN TRIM(SUBSTR(name, 1, POSITION(' ' IN name) - 1)) 
                ELSE name 
            END as first_name,
            CASE 
                WHEN POSITION(' ' IN name) > 0 
                THEN TRIM(SUBSTR(name, POSITION(' ' IN name) + 1)) 
                ELSE NULL 
            END as last_name,
            NULL as company,
            NULL as job_title,
            NULL as phone,
            NULL as country,
            source,
            domain,
            event_time as last_interaction_date,
            event_time as first_seen_date,
            last_updated,
            NULL as tags,
            event_summary as notes,
            NULL as metadata
        FROM crm_contacts
        """).fetchall()
        
        contacts = []
        for row in result:
            contact = {
                'email': row[0],
                'full_name': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'company': row[4],
                'job_title': row[5],
                'phone': row[6],
                'country': row[7],
                'source': row[8],
                'domain': row[9],
                'last_interaction_date': row[10],
                'first_seen_date': row[11],
                'last_updated': row[12],
                'tags': row[13],
                'notes': row[14],
                'metadata': row[15]
            }
            contacts.append(contact)
        
        logger.info(f"Extracted {len(contacts)} contacts from CRM tables")
        return contacts
    except Exception as e:
        logger.error(f"Error extracting contacts from CRM tables: {e}")
        return []

def extract_contacts_from_emails(conn: duckdb.DuckDBPyConnection) -> List[Dict]:
    """Extract contacts from email-related tables.
    
    Args:
        conn: DuckDB connection
        
    Returns:
        List of contact dictionaries
    """
    try:
        # Extract from crm_emails
        result = conn.execute("""
        SELECT DISTINCT
            from_email as email,
            from_name as full_name,
            CASE 
                WHEN POSITION(' ' IN from_name) > 0 
                THEN TRIM(SUBSTR(from_name, 1, POSITION(' ' IN from_name) - 1)) 
                ELSE from_name 
            END as first_name,
            CASE 
                WHEN POSITION(' ' IN from_name) > 0 
                THEN TRIM(SUBSTR(from_name, POSITION(' ' IN from_name) + 1)) 
                ELSE NULL 
            END as last_name,
            NULL as company,
            NULL as job_title,
            NULL as phone,
            NULL as country,
            'email' as source,
            SUBSTR(from_email, POSITION('@' IN from_email) + 1) as domain,
            date as last_interaction_date,
            date as first_seen_date,
            date as last_updated,
            NULL as tags,
            subject as notes,
            NULL as metadata
        FROM crm_emails
        WHERE from_email IS NOT NULL AND from_email != ''
        """).fetchall()
        
        contacts = []
        for row in result:
            contact = {
                'email': row[0],
                'full_name': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'company': row[4],
                'job_title': row[5],
                'phone': row[6],
                'country': row[7],
                'source': row[8],
                'domain': row[9],
                'last_interaction_date': row[10],
                'first_seen_date': row[11],
                'last_updated': row[12],
                'tags': row[13],
                'notes': row[14],
                'metadata': row[15]
            }
            contacts.append(contact)
        
        # Extract from activedata_email_analyses
        result = conn.execute("""
        SELECT DISTINCT
            from_address as email,
            NULL as full_name,
            NULL as first_name,
            NULL as last_name,
            NULL as company,
            NULL as job_title,
            NULL as phone,
            NULL as country,
            'email_analysis' as source,
            SUBSTR(from_address, POSITION('@' IN from_address) + 1) as domain,
            analysis_date as last_interaction_date,
            analysis_date as first_seen_date,
            analysis_date as last_updated,
            NULL as tags,
            subject as notes,
            raw_analysis as metadata
        FROM activedata_email_analyses
        WHERE from_address IS NOT NULL AND from_address != ''
        """).fetchall()
        
        for row in result:
            contact = {
                'email': row[0],
                'full_name': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'company': row[4],
                'job_title': row[5],
                'phone': row[6],
                'country': row[7],
                'source': row[8],
                'domain': row[9],
                'last_interaction_date': row[10],
                'first_seen_date': row[11],
                'last_updated': row[12],
                'tags': row[13],
                'notes': row[14],
                'metadata': row[15]
            }
            contacts.append(contact)
        
        logger.info(f"Extracted {len(contacts)} contacts from email tables")
        return contacts
    except Exception as e:
        logger.error(f"Error extracting contacts from email tables: {e}")
        return []

def extract_contacts_from_subscribers(conn: duckdb.DuckDBPyConnection) -> List[Dict]:
    """Extract contacts from subscriber-related tables.
    
    Args:
        conn: DuckDB connection
        
    Returns:
        List of contact dictionaries
    """
    try:
        # Extract from input_data_subscribers
        result = conn.execute("""
        SELECT 
            email,
            name as full_name,
            CASE 
                WHEN POSITION(' ' IN name) > 0 
                THEN TRIM(SUBSTR(name, 1, POSITION(' ' IN name) - 1)) 
                ELSE name 
            END as first_name,
            CASE 
                WHEN POSITION(' ' IN name) > 0 
                THEN TRIM(SUBSTR(name, POSITION(' ' IN name) + 1)) 
                ELSE NULL 
            END as last_name,
            NULL as company,
            NULL as job_title,
            NULL as phone,
            NULL as country,
            'subscriber' as source,
            SUBSTR(email, POSITION('@' IN email) + 1) as domain,
            created_at as last_interaction_date,
            created_at as first_seen_date,
            updated_at as last_updated,
            status as tags,
            attributes as notes,
            NULL as metadata
        FROM input_data_subscribers
        WHERE email IS NOT NULL AND email != ''
        """).fetchall()
        
        contacts = []
        for row in result:
            contact = {
                'email': row[0],
                'full_name': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'company': row[4],
                'job_title': row[5],
                'phone': row[6],
                'country': row[7],
                'source': row[8],
                'domain': row[9],
                'last_interaction_date': row[10],
                'first_seen_date': row[11],
                'last_updated': row[12],
                'tags': row[13],
                'notes': row[14],
                'metadata': row[15]
            }
            contacts.append(contact)
        
        # Extract from input_data_EIvirgin_csvSubscribers
        # This table has a complex schema, so we'll extract what we can
        result = conn.execute("""
        SELECT 
            "Email Address" as email,
            "Name" as full_name,
            "ContactExport_20160912_First Name" as first_name,
            "ContactExport_20160912_Last Name" as last_name,
            "EmployerName" as company,
            "Job Title" as job_title,
            NULL as phone,
            "Country" as country,
            'EI_subscriber' as source,
            "Email Domain" as domain,
            "LAST_CHANGED" as last_interaction_date,
            "OPTIN_TIME" as first_seen_date,
            "LAST_CHANGED" as last_updated,
            NULL as tags,
            "NOTES" as notes,
            NULL as metadata
        FROM input_data_EIvirgin_csvSubscribers
        WHERE "Email Address" IS NOT NULL AND "Email Address" != ''
        """).fetchall()
        
        for row in result:
            contact = {
                'email': row[0],
                'full_name': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'company': row[4],
                'job_title': row[5],
                'phone': row[6],
                'country': row[7],
                'source': row[8],
                'domain': row[9],
                'last_interaction_date': row[10],
                'first_seen_date': row[11],
                'last_updated': row[12],
                'tags': row[13],
                'notes': row[14],
                'metadata': row[15]
            }
            contacts.append(contact)
        
        logger.info(f"Extracted {len(contacts)} contacts from subscriber tables")
        return contacts
    except Exception as e:
        logger.error(f"Error extracting contacts from subscriber tables: {e}")
        return []

def extract_contacts_from_blog_signups(conn: duckdb.DuckDBPyConnection) -> List[Dict]:
    """Extract contacts from blog signup form responses.
    
    Args:
        conn: DuckDB connection
        
    Returns:
        List of contact dictionaries
    """
    try:
        result = conn.execute("""
        SELECT 
            email,
            name as full_name,
            CASE 
                WHEN POSITION(' ' IN name) > 0 
                THEN TRIM(SUBSTR(name, 1, POSITION(' ' IN name) - 1)) 
                ELSE name 
            END as first_name,
            CASE 
                WHEN POSITION(' ' IN name) > 0 
                THEN TRIM(SUBSTR(name, POSITION(' ' IN name) + 1)) 
                ELSE NULL 
            END as last_name,
            company,
            NULL as job_title,
            phone,
            NULL as country,
            'blog_signup' as source,
            SUBSTR(email, POSITION('@' IN email) + 1) as domain,
            date as last_interaction_date,
            date as first_seen_date,
            date as last_updated,
            CASE WHEN wants_newsletter THEN 'newsletter' ELSE NULL END as tags,
            message as notes,
            raw_content as metadata
        FROM input_data_blog_signup_form_responses
        WHERE email IS NOT NULL AND email != ''
        """).fetchall()
        
        contacts = []
        for row in result:
            contact = {
                'email': row[0],
                'full_name': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'company': row[4],
                'job_title': row[5],
                'phone': row[6],
                'country': row[7],
                'source': row[8],
                'domain': row[9],
                'last_interaction_date': row[10],
                'first_seen_date': row[11],
                'last_updated': row[12],
                'tags': row[13],
                'notes': row[14],
                'metadata': row[15]
            }
            contacts.append(contact)
        
        logger.info(f"Extracted {len(contacts)} contacts from blog signup form responses")
        return contacts
    except Exception as e:
        logger.error(f"Error extracting contacts from blog signup form responses: {e}")
        return []

def merge_contacts(contacts: List[Dict]) -> Dict[str, Dict]:
    """Merge contacts by email, prioritizing more complete information.
    
    Args:
        contacts: List of contact dictionaries
        
    Returns:
        Dictionary of merged contacts keyed by email
    """
    merged_contacts = {}
    
    for contact in contacts:
        email = contact['email']
        if not email:
            continue
            
        email = email.lower().strip()
        
        if email not in merged_contacts:
            merged_contacts[email] = contact
            continue
            
        # Merge with existing contact, prioritizing non-null values
        existing = merged_contacts[email]
        for key, value in contact.items():
            if key == 'email':
                continue
                
            # For all other fields, prefer non-null values
            if value is not None and existing[key] is None:
                existing[key] = value
                
    logger.info(f"Merged contacts into {len(merged_contacts)} unique contacts")
    return merged_contacts

def insert_unified_contacts(conn: duckdb.DuckDBPyConnection, contacts: Dict[str, Dict]) -> None:
    """Insert merged contacts into the unified_contacts table.
    
    Args:
        conn: DuckDB connection
        contacts: Dictionary of merged contacts keyed by email
    """
    try:
        # Clear existing data
        conn.execute("DELETE FROM unified_contacts")
        logger.info("Cleared existing data from unified_contacts table")
        
        # Insert new data in batches
        batch_size = 100
        contact_items = list(contacts.items())
        total_contacts = len(contact_items)
        total_batches = (total_contacts + batch_size - 1) // batch_size
        
        logger.info(f"Inserting {total_contacts} contacts in {total_batches} batches of {batch_size}")
        
        for batch_idx in range(0, total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_contacts)
            batch = contact_items[start_idx:end_idx]
            
            logger.info(f"Processing batch {batch_idx + 1}/{total_batches} ({start_idx} to {end_idx - 1})")
            
            for email, contact in batch:
                try:
                    conn.execute("""
                    INSERT INTO unified_contacts (
                        email, first_name, last_name, full_name, company, job_title, 
                        phone, country, source, domain, last_interaction_date, 
                        first_seen_date, last_updated, tags, notes, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        contact['email'],
                        contact['first_name'],
                        contact['last_name'],
                        contact['full_name'],
                        contact['company'],
                        contact['job_title'],
                        contact['phone'],
                        contact['country'],
                        contact['source'],
                        contact['domain'],
                        contact['last_interaction_date'],
                        contact['first_seen_date'],
                        contact['last_updated'],
                        contact['tags'],
                        contact['notes'],
                        json.dumps(contact['metadata']) if contact['metadata'] is not None else None
                    ])
                except Exception as e:
                    logger.error(f"Error inserting contact {email}: {e}")
            
            logger.info(f"Completed batch {batch_idx + 1}/{total_batches}")
        
        logger.info(f"Inserted {total_contacts} contacts into unified_contacts table")
    except Exception as e:
        logger.error(f"Error inserting contacts into unified_contacts table: {e}")
        raise

def main():
    """Main function to consolidate contacts."""
    parser = argparse.ArgumentParser(description="Consolidate contact information from various tables")
    parser.add_argument("--database", default="dewey", help="MotherDuck database name")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Connect to MotherDuck
        conn = connect_to_motherduck(args.database)
        
        # Create unified_contacts table
        create_unified_contacts_table(conn)
        
        # Extract contacts from various sources
        crm_contacts = extract_contacts_from_crm(conn)
        email_contacts = extract_contacts_from_emails(conn)
        subscriber_contacts = extract_contacts_from_subscribers(conn)
        blog_signup_contacts = extract_contacts_from_blog_signups(conn)
        
        # Combine all contacts
        all_contacts = crm_contacts + email_contacts + subscriber_contacts + blog_signup_contacts
        logger.info(f"Total contacts extracted: {len(all_contacts)}")
        
        # Merge contacts
        merged_contacts = merge_contacts(all_contacts)
        
        # Insert into unified_contacts table
        insert_unified_contacts(conn, merged_contacts)
        
        logger.info("Contact consolidation completed successfully")
        
    except Exception as e:
        logger.error(f"Error in contact consolidation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() import pytest
import duckdb
from datetime import datetime
from src.dewey.core.crm.contact_consolidation import (
    connect_to_motherduck,
    create_unified_contacts_table,
    extract_contacts_from_crm,
    extract_contacts_from_emails,
    extract_contacts_from_subscribers,
    extract_contacts_from_blog_signups,
    merge_contacts,
    insert_unified_contacts
)

@pytest.fixture
def test_db():
    """Fixture providing in-memory DuckDB connection with test tables"""
    conn = duckdb.connect(':memory:')
    # Create test tables
    conn.execute("""
        CREATE TABLE crm_contacts (
            email VARCHAR,
            name VARCHAR,
            source VARCHAR,
            domain VARCHAR,
            event_time TIMESTAMP,
            event_summary VARCHAR,
            last_updated TIMESTAMP
        );
    """)
    conn.execute("INSERT INTO crm_contacts VALUES ('test@example.com', 'John Doe', 'CRM', 'example.com', '2023-01-01', 'Test', '2023-01-01')")
    
    conn.execute("""
        CREATE TABLE crm_emails (
            from_email VARCHAR,
            from_name VARCHAR,
            date TIMESTAMP,
            subject VARCHAR
        );
    """)
    conn.execute("INSERT INTO crm_emails VALUES ('sender@example.com', 'Alice Smith', '2023-01-02', 'Hello')")
    
    conn.execute("""
        CREATE TABLE input_data_subscribers (
            email VARCHAR,
            name VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            status VARCHAR,
            attributes VARCHAR
        );
    """)
    conn.execute("INSERT INTO input_data_subscribers VALUES ('subscriber@example.com', 'Bob Brown', '2023-01-03', '2023-01-03', 'active', 'test')")
    
    conn.execute("""
        CREATE TABLE input_data_blog_signup_form_responses (
            email VARCHAR,
            name VARCHAR,
            company VARCHAR,
            phone VARCHAR,
            date TIMESTAMP,
            wants_newsletter BOOLEAN,
            message VARCHAR,
            raw_content VARCHAR
        );
    """)
    conn.execute("INSERT INTO input_data_blog_signup_form_responses VALUES ('blog@example.com', 'Charlie', 'Widgets Inc', '555-1234', '2023-01-04', true, 'Sign me up', 'raw data')")
    
    # Create activedata_email_analyses table
    conn.execute("""
        CREATE TABLE activedata_email_analyses (
            from_address VARCHAR,
            analysis_date TIMESTAMP,
            subject VARCHAR,
            raw_analysis VARCHAR
        );
    """)
    conn.execute("INSERT INTO activedata_email_analyses VALUES ('test_analysis@example.com', '2023-01-02', 'Analysis Subject', '{\"key\": \"value\"}')")
    
    # Create input_data_EIvirgin_csvSubscribers table
    conn.execute("""
        CREATE TABLE input_data_EIvirgin_csvSubscribers (
            "Email Address" VARCHAR,
            "Name" VARCHAR,
            "ContactExport_20160912_First Name" VARCHAR,
            "ContactExport_20160912_Last Name" VARCHAR,
            "EmployerName" VARCHAR,
            "Job Title" VARCHAR,
            "Country" VARCHAR,
            "Email Domain" VARCHAR,
            "LAST_CHANGED" TIMESTAMP,
            "OPTIN_TIME" TIMESTAMP,
            "NOTES" VARCHAR
        );
    """)
    conn.execute("INSERT INTO input_data_EIvirgin_csvSubscribers VALUES ('ei@example.com', 'EI Contact', 'First', 'Last', 'Company', 'Title', 'Country', 'domain.com', '2023-01-01', '2023-01-02', 'Notes')")
    
    yield conn
    conn.close()

def test_connect_to_motherduck():
    """Verify database connection establishment"""
    conn = connect_to_motherduck()
    assert isinstance(conn, duckdb.DuckDBPyConnection)
    conn.close()

def test_create_unified_contacts_table(test_db):
    """Validate unified_contacts table creation"""
    create_unified_contacts_table(test_db)
    tables = test_db.execute("SHOW TABLES;").fetchall()
    assert ('unified_contacts',) in tables

def test_extract_crm_contacts(test_db):
    """Verify CRM contact extraction"""
    contacts = extract_contacts_from_crm(test_db)
    assert len(contacts) == 1
    contact = contacts[0]
    assert contact['email'] == 'test@example.com'
    assert contact['first_name'] == 'John'
    assert contact['last_name'] == 'Doe'
    assert contact['source'] == 'CRM'

def test_extract_email_contacts(test_db):
    """Verify email contact extraction"""
    contacts = extract_contacts_from_emails(test_db)
    assert len(contacts) == 1
    contact = contacts[0]
    assert contact['email'] == 'sender@example.com'
    assert contact['source'] == 'email'
    assert contact['domain'] == 'example.com'

def test_extract_subscriber_contacts(test_db):
    """Validate subscriber data extraction"""
    contacts = extract_contacts_from_subscribers(test_db)
    assert len(contacts) == 1
    contact = contacts[0]
    assert contact['email'] == 'subscriber@example.com'
    assert contact['tags'] == 'active'
    assert contact['source'] == 'subscriber'

def test_extract_blog_contacts(test_db):
    """Test blog signup extraction"""
    contacts = extract_contacts_from_blog_signups(test_db)
    assert len(contacts) == 1
    contact = contacts[0]
    assert contact['company'] == 'Widgets Inc'
    assert contact['tags'] == 'newsletter'
    assert contact['phone'] == '555-1234'

def test_merge_contacts():
    """Test contact merging logic"""
    contact1 = {
        'email': 'test@example.com',
        'first_name': 'John',
        'last_name': None,
        'company': 'ABC'
    }
    contact2 = {
        'email': 'test@example.com',
        'first_name': None,
        'last_name': 'Doe',
        'company': None
    }
    
    merged = merge_contacts([contact1, contact2])
    merged_contact = merged['test@example.com']
    assert merged_contact['first_name'] == 'John'
    assert merged_contact['last_name'] == 'Doe'
    assert merged_contact['company'] == 'ABC'

def test_insert_contacts(test_db):
    """Validate unified contacts insertion"""
    create_unified_contacts_table(test_db)
    test_contacts = {
        'test@example.com': {
            'email': 'test@example.com',
            'first_name': 'Alice',
            'last_name': 'Smith',
            'domain': 'test.com',
            'metadata': {'test': True}
        }
    }
    
    insert_unified_contacts(test_db, test_contacts)
    result = test_db.execute("SELECT * FROM unified_contacts").fetchall()
    assert len(result) == 1
    row = result[0]
    assert row.email == 'test@example.com'
    assert row.metadata == '{"test": true}'

def test_full_consolidation_flow(test_db):
    """End-to-end consolidation test"""
    create_unified_contacts_table(test_db)
    
    crm_contacts = extract_contacts_from_crm(test_db)
    email_contacts = extract_contacts_from_emails(test_db)
    subscriber_contacts = extract_contacts_from_subscribers(test_db)
    blog_contacts = extract_contacts_from_blog_signups(test_db)
    
    merged = merge_contacts(crm_contacts + email_contacts + subscriber_contacts + blog_contacts)
    insert_unified_contacts(test_db, merged)
    
    count = test_db.execute("SELECT COUNT(*) FROM unified_contacts").fetchone()[0]
    assert count == 5  # Now includes EI and activedata sources
    
    # Verify merged data
    alice = test_db.execute("SELECT * FROM unified_contacts WHERE email='sender@example.com'").fetchone()
    assert alice.first_name == 'Alice'
    assert alice.source == 'email'

# New test for activedata extraction
def test_extract_email_contacts_activedata(test_db):
    """Verify extraction from activedata_email_analyses"""
    contacts = extract_contacts_from_emails(test_db)
    assert len(contacts) == 2
    activedata_contact = next(c for c in contacts if c['source'] == 'email_analysis')
    assert activedata_contact['email'] == 'test_analysis@example.com'
    assert activedata_contact['metadata'] == '{"key": "value"}'

# New test for EIvirgin subscribers
def test_extract_subscribers_ei(test_db):
    """Test extraction from input_data_EIvirgin_csvSubscribers"""
    contacts = extract_contacts_from_subscribers(test_db)
    assert len(contacts) == 2
    ei_contact = next(c for c in contacts if c['source'] == 'EI_subscriber')
    assert ei_contact['email'] == 'ei@example.com'
    assert ei_contact['company'] == 'Company'
    assert ei_contact['job_title'] == 'Title'

# Test merging with case-insensitive email
def test_merge_case_insensitive_email():
    """Test merging contacts with same email in different cases"""
    contact1 = {'email': 'Test@example.com', 'first_name': 'John'}
    contact2 = {'email': 'test@example.com', 'last_name': 'Doe'}
    merged = merge_contacts([contact1, contact2])
    assert len(merged) == 1
    merged_contact = merged['test@example.com']
    assert merged_contact['first_name'] == 'John'
    assert merged_contact['last_name'] == 'Doe'

# Test inserting with null metadata
def test_insert_contacts_with_null_metadata(test_db):
    """Test inserting contact with null metadata"""
    create_unified_contacts_table(test_db)
    test_contacts = {
        'test@example.com': {
            'email': 'test@example.com',
            'first_name': 'Alice',
            'metadata': None
        }
    }
    insert_unified_contacts(test_db, test_contacts)
    result = test_db.execute("SELECT metadata FROM unified_contacts WHERE email=?", ('test@example.com',)).fetchone()
    assert result[0] is None

# Test extracting CRM with no data
def test_extract_crm_no_data(test_db):
    """Test extracting CRM contacts with no data"""
    test_db.execute("DELETE FROM crm_contacts")
    contacts = extract_contacts_from_crm(test_db)
    assert len(contacts) == 0

# Add test helper functions
def get_test_data():
    return {
        "crm_contacts": [
            {"email": "test@example.com", "name": "John Doe", "source": "CRM", "domain": "example.com",
             "event_time": datetime(2023, 1, 1), "event_summary": "Test", "last_updated": datetime(2023, 1, 1)},
        ],
        "crm_emails": [
            {"from_email": "sender@example.com", "from_name": "Alice Smith", "date": datetime(2023, 1, 2),
             "subject": "Hello"},
        ],
        "input_data_subscribers": [
            {"email": "subscriber@example.com", "name": "Bob Brown", "created_at": datetime(2023, 1, 3),
             "updated_at": datetime(2023, 1, 3), "status": "active", "attributes": "test"},
        ],
        "blog_signups": [
            {"email": "blog@example.com", "name": "Charlie", "company": "Widgets Inc", "phone": "555-1234",
             "date": datetime(2023, 1, 4), "wants_newsletter": True, "message": "Sign me up", "raw_content": "raw data"}
        ]
    }
import duckdb
from datetime import datetime

def create_test_tables(conn):
    """Helper function to create standardized test tables"""
    conn.execute("""
        CREATE TABLE crm_contacts (
            email VARCHAR,
            name VARCHAR,
            source VARCHAR,
            domain VARCHAR,
            event_time TIMESTAMP,
            event_summary VARCHAR,
            last_updated TIMESTAMP
        );
    """)
    # Create other test tables here
