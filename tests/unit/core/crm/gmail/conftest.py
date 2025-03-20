"""Test configuration and fixtures for Gmail tests."""

import os
import tempfile
from datetime import datetime
from typing import Generator, Dict, Any

import pytest
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import HttpMockSequence

@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def mock_gmail_service():
    """Create a mock Gmail service."""
    def _create_mock_service(responses: list):
        http = HttpMockSequence(responses)
        return build('gmail', 'v1', http=http)
    return _create_mock_service

@pytest.fixture
def sample_email_data() -> Dict[str, Any]:
    """Sample email data for testing."""
    return {
        'id': 'msg123',
        'threadId': 'thread123',
        'labelIds': ['INBOX', 'UNREAD'],
        'snippet': 'Email snippet...',
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'John Doe <john@example.com>'},
                {'name': 'To', 'value': 'Jane Smith <jane@example.com>'},
                {'name': 'Subject', 'value': 'Test Email'},
                {'name': 'Date', 'value': 'Mon, 15 Mar 2024 10:00:00 -0700'},
            ],
            'mimeType': 'text/plain',
            'body': {
                'data': 'VGhpcyBpcyBhIHRlc3QgZW1haWw='  # "This is a test email" in base64
            }
        },
        'sizeEstimate': 1024,
        'historyId': '12345'
    }

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables."""
    monkeypatch.setenv('MOTHERDUCK_TOKEN', 'test_token')
    monkeypatch.setenv('GOOGLE_APPLICATION_CREDENTIALS', '/path/to/credentials.json')

@pytest.fixture
def mock_credentials():
    """Create mock Google credentials."""
    return service_account.Credentials.from_service_account_info(
        {
            'type': 'service_account',
            'project_id': 'test-project',
            'private_key_id': 'key-id',
            'private_key': '-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n',
            'client_email': 'test@test-project.iam.gserviceaccount.com',
            'client_id': '123456789',
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
            'client_x509_cert_url': 'https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project.iam.gserviceaccount.com'
        }
    )

@pytest.fixture
def mock_duckdb_connection(temp_db_path):
    """Create a mock DuckDB connection."""
import duckdb
    conn = duckdb.connect(temp_db_path)
    
    # Create necessary tables
    conn.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        id VARCHAR PRIMARY KEY,
        thread_id VARCHAR,
        subject VARCHAR,
        from_email VARCHAR,
        to_email VARCHAR,
        cc_email VARCHAR,
        bcc_email VARCHAR,
        date TIMESTAMP,
        body TEXT,
        snippet TEXT,
        labels JSON,
        attachments JSON,
        size_estimate INTEGER,
        history_id VARCHAR,
        sync_status VARCHAR,
        last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    yield conn
    conn.close()
    
@pytest.fixture
def sample_email_batch() -> list:
    """Generate a batch of sample emails for testing."""
    return [
        {
            'id': f'msg{i}',
            'threadId': f'thread{i}',
            'labelIds': ['INBOX'],
            'snippet': f'Test email {i}',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': f'sender{i}@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': f'Test Subject {i}'},
                    {'name': 'Date', 'value': datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')},
                ],
                'mimeType': 'text/plain',
                'body': {'data': 'VGVzdCBib2R5'}
            },
            'sizeEstimate': 1000 + i
        }
        for i in range(5)
    ] 