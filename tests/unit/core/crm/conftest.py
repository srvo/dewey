"""Common test fixtures for CRM tests."""
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import pandas as pd
import duckdb
import json
from dewey.core.crm.gmail.models import RawEmail
from dewey.core.crm.enrichment.contact_enrichment import ContactEnrichmentService

@pytest.fixture
def sample_email_data():
    """Create sample email data."""
    return RawEmail(
        gmail_id="msg123",
        thread_id="thread123",
        subject="Test Email",
        snippet="This is a test email",
        plain_body="Hello, this is a test email body.",
        html_body="<p>Hello, this is a test email body.</p>",
        from_name="John Doe",
        from_email="john@example.com",
        to_addresses=["recipient@example.com"],
        cc_addresses=[],
        bcc_addresses=[],
        received_date=datetime.now(),
        labels=["INBOX"],
        size_estimate=1024
    )

@pytest.fixture
def sample_contact_data():
    """Create sample contact data."""
    return {
        "email": "john@example.com",
        "full_name": "John Doe",
        "first_name": "John",
        "last_name": "Doe",
        "company": "Example Corp",
        "job_title": "Software Engineer",
        "phone": "+1234567890",
        "country": "US",
        "source": "email",
        "domain": "example.com",
        "last_interaction_date": datetime.now().isoformat(),
        "first_seen_date": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "tags": "client",
        "notes": "Met at conference",
        "metadata": json.dumps({"key": "value"})
    }

@pytest.fixture
def mock_gmail_service():
    """Create a mock Gmail service."""
    mock = MagicMock()
    mock.users().messages().list().execute.return_value = {
        "messages": [{"id": "msg123", "threadId": "thread123"}],
        "nextPageToken": None
    }
    mock.users().messages().get().execute.return_value = {
        "id": "msg123",
        "threadId": "thread123",
        "snippet": "Test email",
        "payload": {
            "headers": [
                {"name": "From", "value": "John Doe <john@example.com>"},
                {"name": "Subject", "value": "Test Email"}
            ],
            "parts": [{"body": {"data": "SGVsbG8="}}]
        }
    }
    return mock

@pytest.fixture
def mock_db_connection():
    """Create a mock database connection."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []
    return conn

@pytest.fixture
def test_db(tmp_path):
    """Create a test database."""
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    
    # Create test tables
    conn.execute("""
        CREATE TABLE crm_contacts (
            email VARCHAR,
            name VARCHAR,
            company VARCHAR,
            title VARCHAR,
            first_seen_date TIMESTAMP,
            last_seen_date TIMESTAMP,
            metadata JSON
        )
    """)
    
    conn.execute("""
        CREATE TABLE crm_emails (
            thread_id VARCHAR PRIMARY KEY,
            from_email VARCHAR,
            from_name VARCHAR,
            subject VARCHAR,
            date TIMESTAMP,
            body TEXT,
            metadata JSON
        )
    """)
    
    conn.execute("""
        CREATE TABLE contact_processing (
            id VARCHAR PRIMARY KEY,
            email_id VARCHAR,
            contact_id VARCHAR,
            created_at TIMESTAMP
        )
    """)
    
    # Insert sample data
    conn.execute("""
        INSERT INTO crm_contacts VALUES (
            'test@example.com',
            'John Doe',
            'Example Corp',
            'Engineer',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP,
            '{"source": "test"}'
        )
    """)
    
    return conn

@pytest.fixture
def sample_csv_data(tmp_path):
    """Create sample CSV files for testing."""
    # Client Contact Master
    client_master = tmp_path / "client_contact_master.csv"
    client_master.write_text("""Subscriber,first_name,last_name,Location,Subscribed,Sent,Opens,Clicks
john@example.com,John,Doe,US,2024-01-01,10,5,2""")
    
    # Blog Signup Form
    blog_signup = tmp_path / "blog_signup.csv"
    blog_signup.write_text("""Email,Name,Company,Phone,Message,Date,Newsletter
jane@example.com,Jane Smith,Tech Corp,123456789,Interested in your blog,2024-01-02,Yes""")
    
    # Onboarding Form
    onboarding = tmp_path / "onboarding.csv"
    onboarding.write_text("""Email,Name,Company,Phone,Message,Date,Newsletter
bob@example.com,Bob Wilson,Dev Inc,987654321,Starting onboarding,2024-01-03,Yes""")
    
    return {
        "client_master": str(client_master),
        "blog_signup": str(blog_signup),
        "onboarding": str(onboarding)
    }

@pytest.fixture
def mock_enrichment_service():
    """Create a mock enrichment service."""
    service = MagicMock(spec=ContactEnrichmentService)
    service.enrich_contact.return_value = {
        "enriched": True,
        "data": {
            "company": "Example Corp",
            "title": "Software Engineer",
            "linkedin_url": "https://linkedin.com/in/johndoe"
        }
    }
    return service

@pytest.fixture
def sample_gmail_checkpoint(tmp_path):
    """Create a sample Gmail checkpoint file."""
    checkpoint = {
        "last_sync": datetime.now().isoformat(),
        "last_message_id": "msg123",
        "processed_threads": ["thread123"]
    }
    checkpoint_file = tmp_path / "gmail_checkpoint.json"
    checkpoint_file.write_text(json.dumps(checkpoint))
    return str(checkpoint_file) 