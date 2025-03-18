#!/usr/bin/env python3
"""
CSV Contact Integration Script
=============================

This script integrates contact information from various CSV files into the unified_contacts table
in the MotherDuck database, focusing on individuals.
"""

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import duckdb
import pandas as pd

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"csv_contact_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("csv_contact_integration")

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

def process_client_intake_questionnaire(file_path: str) -> List[Dict]:
    """Process the Client Intake Questionnaire CSV file.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        List of contact dictionaries
    """
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Read {len(df)} rows from {file_path}")
        
        contacts = []
        for _, row in df.iterrows():
            # Extract email
            email = row.get('Email Address')
            if not email or pd.isna(email):
                continue
                
            # Extract name
            full_name = row.get("What's your name?")
            if pd.isna(full_name):
                full_name = None
                
            # Extract first and last name
            first_name = None
            last_name = None
            if full_name and ' ' in full_name:
                parts = full_name.split(' ', 1)
                first_name = parts[0]
                last_name = parts[1]
            elif full_name:
                first_name = full_name
                
            # Extract phone
            phone = row.get("What's the best phone number to reach you on?")
            if pd.isna(phone):
                phone = None
                
            # Extract company/job
            job = row.get("What do you do for a living? ")
            if pd.isna(job):
                job = None
                
            # Extract address
            address = row.get("What's your home address (including City, State, and ZIP code)")
            if pd.isna(address):
                address = None
                
            # Extract country (default to US if not specified)
            country = "United States"
            
            # Create metadata
            metadata = {
                "pronouns": row.get("What are your pronouns? ") if not pd.isna(row.get("What are your pronouns? ")) else None,
                "retirement_plans": row.get("Do you plan to retire or make other major life changes in the next 5-10 years? ") if not pd.isna(row.get("Do you plan to retire or make other major life changes in the next 5-10 years? ")) else None,
                "investment_amount": row.get("Approximately how much money would you like us to manage for you?") if not pd.isna(row.get("Approximately how much money would you like us to manage for you?")) else None,
                "account_type": row.get("What kind of accounts are these assets currently held in? ") if not pd.isna(row.get("What kind of accounts are these assets currently held in? ")) else None,
                "net_worth": row.get("What's your approximate net worth? ") if not pd.isna(row.get("What's your approximate net worth? ")) else None,
                "annual_income": row.get("What's your approximate annual salary (or self-employment income)?") if not pd.isna(row.get("What's your approximate annual salary (or self-employment income)?")) else None,
                "investment_objective": row.get("What is your primary investment objective for these assets? ") if not pd.isna(row.get("What is your primary investment objective for these assets? ")) else None,
                "time_horizon": row.get("When you think about \"the long term,\" how far in the future is that for you? ") if not pd.isna(row.get("When you think about \"the long term,\" how far in the future is that for you? ")) else None,
                "risk_tolerance": row.get("If the market was down 25%, what action would you be most likely to take? ") if not pd.isna(row.get("If the market was down 25%, what action would you be most likely to take? ")) else None,
                "interests": row.get("What animates your interest in our firm? Please check all of the boxes that apply.   ") if not pd.isna(row.get("What animates your interest in our firm? Please check all of the boxes that apply.   ")) else None,
                "activism": row.get("What activist and/or volunteer activities are important to you? ") if not pd.isna(row.get("What activist and/or volunteer activities are important to you? ")) else None,
                "ethical_considerations": row.get("Are there any specific ethical considerations you would like to see Invest Vegan address in more detail? ") if not pd.isna(row.get("Are there any specific ethical considerations you would like to see Invest Vegan address in more detail? ")) else None,
                "referral_source": row.get("How did you hear about us?") if not pd.isna(row.get("How did you hear about us?")) else None
            }
            
            # Extract timestamp for dates
            timestamp = row.get('Timestamp')
            if pd.isna(timestamp):
                timestamp = None
                
            contact = {
                'email': email.lower().strip(),
                'full_name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'company': None,
                'job_title': job,
                'phone': phone,
                'country': country,
                'source': 'client_intake_questionnaire',
                'domain': email.split('@')[1] if '@' in email else None,
                'last_interaction_date': timestamp,
                'first_seen_date': timestamp,
                'last_updated': datetime.now().isoformat(),
                'tags': 'client,prospect',
                'notes': f"Address: {address}" if address else None,
                'metadata': json.dumps(metadata)
            }
            
            contacts.append(contact)
            
        logger.info(f"Extracted {len(contacts)} contacts from client intake questionnaire")
        return contacts
    except Exception as e:
        logger.error(f"Error processing client intake questionnaire: {e}")
        return []

def process_client_contact_master(file_path: str) -> List[Dict]:
    """Process the Client Contact Master CSV file.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        List of contact dictionaries
    """
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Read {len(df)} rows from {file_path}")
        
        contacts = []
        for _, row in df.iterrows():
            # Extract email
            email = row.get('Subscriber')
            if not email or pd.isna(email):
                continue
                
            # Extract first and last name
            first_name = row.get('first_name')
            if pd.isna(first_name):
                first_name = None
                
            last_name = row.get('last_name')
            if pd.isna(last_name):
                last_name = None
                
            # Construct full name
            full_name = None
            if first_name and last_name:
                full_name = f"{first_name} {last_name}"
            elif first_name:
                full_name = first_name
            elif last_name:
                full_name = last_name
                
            # Extract location
            location = row.get('Location')
            if pd.isna(location):
                location = None
                
            # Extract subscription date
            subscribed = row.get('Subscribed')
            if pd.isna(subscribed):
                subscribed = None
                
            # Create metadata
            metadata = {
                "sent": row.get('Sent') if not pd.isna(row.get('Sent')) else None,
                "opens": row.get('Opens') if not pd.isna(row.get('Opens')) else None,
                "clicks": row.get('Clicks') if not pd.isna(row.get('Clicks')) else None,
                "match_to_main": row.get('Match to main?') if not pd.isna(row.get('Match to main?')) else None
            }
            
            contact = {
                'email': email.lower().strip(),
                'full_name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'company': None,
                'job_title': None,
                'phone': None,
                'country': location,
                'source': 'client_contact_master',
                'domain': email.split('@')[1] if '@' in email else None,
                'last_interaction_date': subscribed,
                'first_seen_date': subscribed,
                'last_updated': datetime.now().isoformat(),
                'tags': 'subscriber',
                'notes': None,
                'metadata': json.dumps(metadata)
            }
            
            contacts.append(contact)
            
        logger.info(f"Extracted {len(contacts)} contacts from client contact master")
        return contacts
    except Exception as e:
        logger.error(f"Error processing client contact master: {e}")
        return []

def process_blog_signup_form(file_path: str) -> List[Dict]:
    """Process the Blog Signup Form Responses CSV file.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        List of contact dictionaries
    """
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Read {len(df)} rows from {file_path}")
        
        contacts = []
        for _, row in df.iterrows():
            # Extract email
            email = row.get('email')
            if not email or pd.isna(email):
                continue
                
            # Extract name
            full_name = row.get('name')
            if pd.isna(full_name):
                full_name = None
                
            # Extract first and last name
            first_name = None
            last_name = None
            if full_name and ' ' in full_name:
                parts = full_name.split(' ', 1)
                first_name = parts[0]
                last_name = parts[1]
            elif full_name:
                first_name = full_name
                
            # Extract phone
            phone = row.get('phone')
            if pd.isna(phone):
                phone = None
                
            # Extract company
            company = row.get('company')
            if pd.isna(company):
                company = None
                
            # Extract message
            message = row.get('message')
            if pd.isna(message):
                message = None
                
            # Extract key points
            key_points = row.get('key_points')
            if pd.isna(key_points):
                key_points = None
                
            # Extract newsletter preference
            wants_newsletter = row.get('wants_newsletter')
            if pd.isna(wants_newsletter):
                wants_newsletter = None
                
            # Extract date
            date = row.get('date')
            if pd.isna(date):
                date = None
                
            # Create metadata
            metadata = {
                "key_points": key_points,
                "wants_newsletter": wants_newsletter
            }
            
            contact = {
                'email': email.lower().strip(),
                'full_name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'company': company,
                'job_title': None,
                'phone': phone,
                'country': None,
                'source': 'blog_signup_form',
                'domain': email.split('@')[1] if '@' in email else None,
                'last_interaction_date': date,
                'first_seen_date': date,
                'last_updated': datetime.now().isoformat(),
                'tags': 'blog_signup',
                'notes': message,
                'metadata': json.dumps(metadata)
            }
            
            contacts.append(contact)
            
        logger.info(f"Extracted {len(contacts)} contacts from blog signup form")
        return contacts
    except Exception as e:
        logger.error(f"Error processing blog signup form: {e}")
        return []

def process_onboarding_form(file_path: str) -> List[Dict]:
    """Process the Onboarding Form Responses CSV file.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        List of contact dictionaries
    """
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Read {len(df)} rows from {file_path}")
        
        contacts = []
        for _, row in df.iterrows():
            # Extract email
            email = row.get('email')
            if not email or pd.isna(email):
                continue
                
            # Extract name
            full_name = row.get('name')
            if pd.isna(full_name):
                full_name = None
                
            # Extract first and last name
            first_name = None
            last_name = None
            if full_name and ' ' in full_name:
                parts = full_name.split(' ', 1)
                first_name = parts[0]
                last_name = parts[1]
            elif full_name:
                first_name = full_name
                
            # Extract phone
            phone = row.get('phone')
            if pd.isna(phone):
                phone = None
                
            # Extract company
            company = row.get('company')
            if pd.isna(company):
                company = None
                
            # Extract message
            message = row.get('message')
            if pd.isna(message):
                message = None
                
            # Extract key points
            key_points = row.get('key_points')
            if pd.isna(key_points):
                key_points = None
                
            # Extract newsletter preference
            wants_newsletter = row.get('wants_newsletter')
            if pd.isna(wants_newsletter):
                wants_newsletter = None
                
            # Extract date
            date = row.get('date')
            if pd.isna(date):
                date = None
                
            # Create metadata
            metadata = {
                "key_points": key_points,
                "wants_newsletter": wants_newsletter
            }
            
            contact = {
                'email': email.lower().strip(),
                'full_name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'company': company,
                'job_title': None,
                'phone': phone,
                'country': None,
                'source': 'onboarding_form',
                'domain': email.split('@')[1] if '@' in email else None,
                'last_interaction_date': date,
                'first_seen_date': date,
                'last_updated': datetime.now().isoformat(),
                'tags': 'onboarding,client',
                'notes': message,
                'metadata': json.dumps(metadata)
            }
            
            contacts.append(contact)
            
        logger.info(f"Extracted {len(contacts)} contacts from onboarding form")
        return contacts
    except Exception as e:
        logger.error(f"Error processing onboarding form: {e}")
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

def update_unified_contacts(conn: duckdb.DuckDBPyConnection, contacts: Dict[str, Dict]) -> None:
    """Update the unified_contacts table with new contact information.
    
    Args:
        conn: DuckDB connection
        contacts: Dictionary of contacts keyed by email
    """
    try:
        # Check if unified_contacts table exists
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='unified_contacts'").fetchone()
        if not result:
            logger.error("unified_contacts table does not exist")
            return
            
        # Process contacts in batches
        batch_size = 100
        contact_items = list(contacts.items())
        total_contacts = len(contact_items)
        total_batches = (total_contacts + batch_size - 1) // batch_size
        
        logger.info(f"Updating {total_contacts} contacts in {total_batches} batches of {batch_size}")
        
        updated_count = 0
        inserted_count = 0
        
        for batch_idx in range(0, total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_contacts)
            batch = contact_items[start_idx:end_idx]
            
            logger.info(f"Processing batch {batch_idx + 1}/{total_batches} ({start_idx} to {end_idx - 1})")
            
            for email, contact in batch:
                try:
                    # Check if contact exists
                    result = conn.execute(f"SELECT email FROM unified_contacts WHERE email = '{email}'").fetchone()
                    
                    if result:
                        # Update existing contact
                        conn.execute("""
                        UPDATE unified_contacts SET
                            first_name = CASE WHEN ? IS NOT NULL THEN ? ELSE first_name END,
                            last_name = CASE WHEN ? IS NOT NULL THEN ? ELSE last_name END,
                            full_name = CASE WHEN ? IS NOT NULL THEN ? ELSE full_name END,
                            company = CASE WHEN ? IS NOT NULL THEN ? ELSE company END,
                            job_title = CASE WHEN ? IS NOT NULL THEN ? ELSE job_title END,
                            phone = CASE WHEN ? IS NOT NULL THEN ? ELSE phone END,
                            country = CASE WHEN ? IS NOT NULL THEN ? ELSE country END,
                            source = CASE WHEN source IS NULL THEN ? ELSE source || ',' || ? END,
                            domain = CASE WHEN ? IS NOT NULL THEN ? ELSE domain END,
                            last_interaction_date = CASE WHEN ? IS NOT NULL THEN ? ELSE last_interaction_date END,
                            first_seen_date = CASE WHEN first_seen_date IS NULL THEN ? ELSE first_seen_date END,
                            last_updated = ?,
                            tags = CASE WHEN tags IS NULL THEN ? ELSE tags || ',' || ? END,
                            notes = CASE WHEN ? IS NOT NULL THEN ? ELSE notes END,
                            metadata = CASE WHEN metadata IS NULL THEN ? ELSE metadata END
                        WHERE email = ?
                        """, [
                            contact['first_name'], contact['first_name'],
                            contact['last_name'], contact['last_name'],
                            contact['full_name'], contact['full_name'],
                            contact['company'], contact['company'],
                            contact['job_title'], contact['job_title'],
                            contact['phone'], contact['phone'],
                            contact['country'], contact['country'],
                            contact['source'], contact['source'],
                            contact['domain'], contact['domain'],
                            contact['last_interaction_date'], contact['last_interaction_date'],
                            contact['first_seen_date'],
                            contact['last_updated'],
                            contact['tags'], contact['tags'],
                            contact['notes'], contact['notes'],
                            contact['metadata'],
                            email
                        ])
                        updated_count += 1
                    else:
                        # Insert new contact
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
                            contact['metadata']
                        ])
                        inserted_count += 1
                except Exception as e:
                    logger.error(f"Error updating contact {email}: {e}")
            
            logger.info(f"Completed batch {batch_idx + 1}/{total_batches}")
        
        logger.info(f"Updated {updated_count} contacts and inserted {inserted_count} contacts in unified_contacts table")
    except Exception as e:
        logger.error(f"Error updating unified_contacts table: {e}")
        raise

def main():
    """Main function to integrate CSV contacts."""
    parser = argparse.ArgumentParser(description="Integrate contact information from CSV files")
    parser.add_argument("--database", default="dewey", help="MotherDuck database name")
    parser.add_argument("--input-dir", default="/Users/srvo/input_data", help="Directory containing input CSV files")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Connect to MotherDuck
        conn = connect_to_motherduck(args.database)
        
        # Process CSV files
        contacts = []
        
        # Client Intake Questionnaire
        intake_file = os.path.join(args.input_dir, "Client Intake Questionnaire (Responses) - Form Responses 1.csv")
        if os.path.exists(intake_file):
            contacts.extend(process_client_intake_questionnaire(intake_file))
        else:
            logger.warning(f"Client Intake Questionnaire file not found: {intake_file}")
            
        # Client Contact Master
        contact_master_file = os.path.join(args.input_dir, "Client_Contact Master - 12_6 subscribers.csv")
        if os.path.exists(contact_master_file):
            contacts.extend(process_client_contact_master(contact_master_file))
        else:
            logger.warning(f"Client Contact Master file not found: {contact_master_file}")
            
        # Blog Signup Form Responses
        blog_signup_file = os.path.join(args.input_dir, "legitimate_blog_signup_form_responses.csv")
        if os.path.exists(blog_signup_file):
            contacts.extend(process_blog_signup_form(blog_signup_file))
        else:
            logger.warning(f"Blog Signup Form Responses file not found: {blog_signup_file}")
            
        # Ask a Question Responses (similar structure to blog signup)
        ask_question_file = os.path.join(args.input_dir, "legitimate_ask_a_question_responses.csv")
        if os.path.exists(ask_question_file):
            contacts.extend(process_blog_signup_form(ask_question_file))
        else:
            logger.warning(f"Ask a Question Responses file not found: {ask_question_file}")
            
        # Onboarding Form Responses
        onboarding_file = os.path.join(args.input_dir, "legitimate_onboarding_form_responses.csv")
        if os.path.exists(onboarding_file):
            contacts.extend(process_onboarding_form(onboarding_file))
        else:
            logger.warning(f"Onboarding Form Responses file not found: {onboarding_file}")
            
        logger.info(f"Total contacts extracted from CSV files: {len(contacts)}")
        
        # Merge contacts
        merged_contacts = merge_contacts(contacts)
        
        # Update unified_contacts table
        update_unified_contacts(conn, merged_contacts)
        
        logger.info("CSV contact integration completed successfully")
        
    except Exception as e:
        logger.error(f"Error in CSV contact integration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

import pytest
import pandas as pd
import duckdb
from datetime import datetime
from pathlib import Path
from src.dewey.core.crm.csv_contact_integration import (
    process_client_intake_questionnaire,
    process_client_contact_master,
    process_blog_signup_form,
    process_onboarding_form,
    merge_contacts,
    update_unified_contacts,
    connect_to_motherduck
)

@pytest.fixture
def tmp_csv(tmp_path):
    """Create temporary CSV files for testing"""
    def _create(data, filename='test.csv'):
        df = pd.DataFrame(data)
        path = tmp_path / filename
        df.to_csv(path, index=False)
        return str(path)
    return _create

@pytest.fixture
def duckdb_connection(tmp_path):
    """DuckDB connection with unified_contacts table"""
    conn = duckdb.connect(':memory:')
    conn.execute('''
        CREATE TABLE unified_contacts (
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
            last_interaction_date VARCHAR,
            first_seen_date VARCHAR,
            last_updated VARCHAR,
            tags VARCHAR,
            notes VARCHAR,
            metadata VARCHAR
        )
    ''')
    yield conn
    conn.close()

def test_process_client_intake_questionnaire_valid(tmp_csv):
    """Test valid client intake questionnaire processing"""
    data = [{
        'Email Address': 'john@example.com',
        "What's your name?": 'John Doe',
        "What's the best phone number to reach you on?": '555-1234',
        "What do you do for a living? ": 'Developer',
        "What's your home address (including City, State, and ZIP code)": '123 Main St',
        "What are your pronouns? ": 'He/Him'
    }]
    file_path = tmp_csv(data, 'client_intake.csv')
    
    contacts = process_client_intake_questionnaire(file_path)
    assert len(contacts) == 1
    contact = contacts[0]
    assert contact['email'] == 'john@example.com'
    assert contact['full_name'] == 'John Doe'
    assert contact['metadata'] == json.dumps({
        'pronouns': 'He/Him',
        'job_title': 'Developer',
        'address': '123 Main St'
    })

def test_process_client_intake_missing_email(tmp_csv):
    """Test handling of missing email in intake questionnaire"""
    data = [{
        'Email Address': None,
        "What's your name?": 'Jane Doe'
    }]
    file_path = tmp_csv(data, 'invalid_intake.csv')
    contacts = process_client_intake_questionnaire(file_path)
    assert len(contacts) == 0

def test_process_client_contact_master_missing_subscriber(tmp_csv):
    """Test contact master with missing Subscriber field"""
    data = [{
        'Subscriber': None,
        'first_name': 'Alex'
    }]
    file_path = tmp_csv(data, 'invalid_contact.csv')
    contacts = process_client_contact_master(file_path)
    assert len(contacts) == 0

def test_merge_contacts_multiple_overrides(tmp_csv):
    """Test merging contacts with multiple field overrides"""
    contact1 = {
        'email': 'merge@example.com',
        'first_name': 'Original',
        'last_name': None,
        'country': 'USA'
    }
    contact2 = {
        'email': 'merge@example.com',
        'first_name': None,
        'last_name': 'Merged',
        'country': None
    }
    
    merged = merge_contacts([contact1, contact2])
    assert merged['merge@example.com']['last_name'] == 'Merged'
    assert merged['merge@example.com']['first_name'] == 'Original'
    assert merged['merge@example.com']['country'] == 'USA'

def test_update_unified_contacts_update_existing(duckdb_connection):
    """Test updating existing contact in database"""
    initial_contact = {
        'email': 'existing@example.com',
        'first_name': 'Old',
        'last_updated': datetime.now().isoformat()
    }
    duckdb_connection.execute("""
        INSERT INTO unified_contacts VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, [
        initial_contact['email'],
        initial_contact['first_name'],
        None,
        None,
        None,
        None,
        None,
        None,
        'initial_source',
        None,
        None,
        None,
        initial_contact['last_updated'],
        None,
        None,
        None
    ])
    
    updated_contact = {
        'email': 'existing@example.com',
        'first_name': None,
        'last_name': 'New',
        'source': 'updated_source'
    }
    contacts = {updated_contact['email']: updated_contact}
    update_unified_contacts(duckdb_connection, contacts)
    
    result = duckdb_connection.execute(
        "SELECT last_name, source FROM unified_contacts WHERE email = ?",
        [updated_contact['email']]
    ).fetchone()
    assert result == ('New', 'initial_source,updated_source')

def test_main_missing_files(tmp_path, monkeypatch):
    """Test main function with missing input files"""
    monkeypatch.setattr(
        'src.dewey.core.crm.csv_contact_integration.connect_to_motherduck',
        lambda *a: duckdb.connect(':memory:')
    )
    
    # Create empty input dir with no files
    main_dir = tmp_path / 'empty'
    main_dir.mkdir()
    
    from src.dewey.core.crm.csv_contact_integration import main
    main(['--input-dir', str(main_dir)])
    
    # Verify no contacts were processed
    conn = duckdb.connect(':memory:')
    assert conn.execute("SELECT COUNT(*) FROM unified_contacts").fetchone()[0] == 0

def test_database_connection_failure():
    """Test database connection error handling"""
    with pytest.raises(Exception, match='Error connecting to MotherDuck database'):
        connect_to_motherduck('invalid_database')

def test_missing_table(duckdb_connection):
    """Test database update when table doesn't exist"""
    duckdb_connection.execute("DROP TABLE unified_contacts")
    contacts = {'test@example.com': {'email': 'test@example.com'}}
    update_unified_contacts(duckdb_connection, contacts)
    assert duckdb_connection.execute("SELECT COUNT(*) FROM unified_contacts").fetchone()[0] == 0
