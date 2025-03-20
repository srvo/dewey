"""Unit tests for IMAP email synchronization following project conventions."""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta
import email
from email.message import Message
import imaplib
import json
from typing import List, Dict, Any

from dewey.core.crm.email.imap_import_standalone import IMAPSync

@pytest.fixture
def mock_db_conn() -> MagicMock:
    """Mock database connection with schema verification."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value = MagicMock()
    return mock_conn

@pytest.fixture
def imap_sync(mock_db_conn: MagicMock) -> IMAPSync:
    """IMAPSync instance with mocked dependencies."""
    with patch("dewey.core.db.connection.DatabaseConnection", return_value=mock_db_conn):
        sync = IMAPSync()
        sync.logger = MagicMock()
        return sync

@pytest.fixture
def sample_email_data() -> bytes:
    """Sample email data for testing."""
    msg = Message()
    msg["From"] = "test@example.com"
    msg["To"] = "recipient@example.com"
    msg["Subject"] = "Test Subject"
    msg["Date"] = "Wed, 01 Jan 2023 12:00:00 +0000"
    msg["Message-ID"] = "<123@test>"
    msg.set_payload("Test body")
    return msg.as_bytes()

def test_initialization(imap_sync: IMAPSync) -> None:
    """Test script initialization with proper configuration."""
    assert imap_sync.name == "imap_sync"
    assert imap_sync.config_section == "imap"
    assert imap_sync.requires_db is True
    assert imap_sync.enable_llm is False
    imap_sync.logger.info.assert_called_with("Initialized imap_sync")

def test_database_initialization(imap_sync: IMAPSync, mock_db_conn: MagicMock) -> None:
    """Test database schema and index creation."""
    imap_sync._init_database()
    
    # Verify schema creation
    expected_calls = [call(IMAPSync.EMAIL_SCHEMA)] + \
                     [call(index_sql) for index_sql in IMAPSync.EMAIL_INDEXES]
    mock_db_conn.execute.assert_has_calls(expected_calls, any_order=True)
    assert mock_db_conn.execute.call_count == len(IMAPSync.EMAIL_INDEXES) + 1
    imap_sync.logger.info.assert_any_call("Initializing email database schema")

def test_imap_connection_success(imap_sync: IMAPSync) -> None:
    """Test successful IMAP connection."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        config = {
            "host": "imap.test.com",
            "port": 993,
            "user": "test",
            "password": "pass",
            "mailbox": "INBOX"
        }
        imap_sync._connect_imap(config)
        
        mock_imap.return_value.login.assert_called_once_with("test", "pass")
        mock_imap.return_value.select.assert_called_once_with("INBOX")
        imap_sync.logger.info.assert_any_call(
            "Connecting to IMAP server imap.test.com:993")

def test_imap_connection_failure(imap_sync: IMAPSync) -> None:
    """Test IMAP connection error handling."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap.return_value.login.side_effect = imaplib.IMAP4.error("Login failed")
        
        with pytest.raises(RuntimeError):
            imap_sync._connect_imap({})
            
        imap_sync.logger.error.assert_called_with(
            "IMAP connection failed: Login failed", exc_info=True)

@pytest.mark.parametrize("header,expected", [
    ("=?utf-8?B?VGhpcyBpcyBhIHRlc3Q=?=", "This is a test"),
    ("=?iso-8859-1?Q?Test_=E4=FC=6E?=", "Test äüñ"),
    ("Plain Text Header", "Plain Text Header"),
])
def test_decode_email_header(imap_sync: IMAPSync, header: str, expected: str) -> None:
    """Test email header decoding with various encodings."""
    assert imap_sync._decode_email_header(header) == expected

def test_parse_email_message(imap_sync: IMAPSync, sample_email_data: bytes) -> None:
    """Test email message parsing with valid data."""
    parsed = imap_sync._parse_email_message(sample_email_data)
    
    assert parsed["subject"] == "Test Subject"
    assert parsed["from"] == "test@example.com"
    assert parsed["message_id"] == "<123@test>"
    assert parsed["body_text"] == "Test body"
    assert "raw_analysis" in parsed
    assert json.loads(parsed["raw_analysis"])["headers"]["Subject"] == "Test Subject"

def test_parse_email_invalid_date(imap_sync: IMAPSync) -> None:
    """Test email parsing with invalid date format."""
    msg = Message()
    msg["Date"] = "Invalid Date Format"
    msg.set_payload("Test body")
    
    parsed = imap_sync._parse_email_message(msg.as_bytes())
    assert parsed["date"] is None
    assert parsed["raw_date"] == "Invalid Date Format"

def test_store_email_success(imap_sync: IMAPSync, mock_db_conn: MagicMock) -> None:
    """Test successful email storage in database."""
    email_data = {
        "msg_id": "123",
        "thread_id": "456",
        "subject": "Test",
        "from": "test@example.com",
        "raw_analysis": "{}",
        "batch_id": "20240101"
    }
    
    result = imap_sync._store_email(email_data, "20240101")
    assert result is True
    mock_db_conn.execute.assert_called_once()
    imap_sync.logger.debug.assert_called_with("Stored email 123")

def test_store_email_conflict(imap_sync: IMAPSync, mock_db_conn: MagicMock) -> None:
    """Test email storage conflict handling."""
    mock_db_conn.execute.side_effect = Exception("UNIQUE constraint failed")
    
    result = imap_sync._store_email({"msg_id": "123"}, "20240101")
    assert result is False
    imap_sync.logger.error.assert_called_with("Error storing email: UNIQUE constraint failed")

def test_full_sync_flow(imap_sync: IMAPSync, mock_db_conn: MagicMock) -> None:
    """Test complete sync workflow with mock data."""
    with patch.object(imap_sync, "_connect_imap") as mock_connect, \
         patch.object(imap_sync, "_fetch_emails") as mock_fetch:
        
        mock_imap = MagicMock()
        mock_connect.return_value = mock_imap
        mock_fetch.return_value = None  # _fetch_emails handles storage
        
        imap_sync.run()
        
        # Verify workflow steps
        imap_sync.logger.info.assert_any_call("Starting execution of imap_sync")
        mock_connect.assert_called_once()
        mock_fetch.assert_called_once_with(mock_imap, imap_sync.parse_args())
        imap_sync.logger.info.assert_any_call("IMAP sync completed successfully")

@pytest.mark.parametrize("days_back,max_emails,batch_size", [
    (7, 1000, 10),
    (30, 500, 20),
    (1, 100, 5),
])
def test_fetch_emails_parameters(imap_sync: IMAPSync, days_back: int, 
                               max_emails: int, batch_size: int) -> None:
    """Test email fetching with different parameters."""
    with patch("imaplib.IMAP4_SSL") as mock_imap, \
         patch.object(imap_sync, "_store_email") as mock_store:
        
        mock_imap.return_value.search.return_value = ("OK", [b"1 2 3"])
        mock_imap.return_value.fetch.return_value = ("OK", [(b"", b"email data")])
        
        imap_sync._fetch_emails(
            mock_imap.return_value,
            days_back=days_back,
            max_emails=max_emails,
            batch_size=batch_size
        )
        
        assert mock_store.call_count == min(3, max_emails)

def test_fetch_emails_empty_result(imap_sync: IMAPSync) -> None:
    """Test email fetching with empty search results."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap.return_value.search.return_value = ("OK", [b""])
        
        imap_sync._fetch_emails(mock_imap.return_value)
        imap_sync.logger.info.assert_called_with("Import completed. Total emails processed: 0")

def test_email_parsing_edge_cases(imap_sync: IMAPSync) -> None:
    """Test email parsing with edge cases."""
    # Test multipart email
    msg = Message()
    msg["From"] = "test@example.com"
    msg["Subject"] = "Multipart Test"
    msg.add_header("Content-Type", "multipart/alternative")
    
    part1 = Message()
    part1.set_payload("Text part", "utf-8")
    part1.set_type("text/plain")
    
    part2 = Message()
    part2.set_payload("<p>HTML part</p>", "utf-8")
    part2.set_type("text/html")
    
    msg.attach(part1)
    msg.attach(part2)
    
    parsed = imap_sync._parse_email_message(msg.as_bytes())
    assert parsed["body_text"] == "Text part"
    assert parsed["body_html"] == "<p>HTML part</p>"

    # Test attachment handling
    msg = Message()
    msg["Content-Type"] = "multipart/mixed"
    part = Message()
    part["Content-Disposition"] = "attachment; filename=test.txt"
    part.set_payload("Attachment content")
    msg.attach(part)
    
    parsed = imap_sync._parse_email_message(msg.as_bytes())
    assert len(parsed["attachments"]) == 1
    assert parsed["attachments"][0]["filename"] == "test.txt"

def test_error_handling_during_fetch(imap_sync: IMAPSync) -> None:
    """Test error handling during email fetch."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap.return_value.search.side_effect = imaplib.IMAP4.error("Search failed")
        
        with pytest.raises(imaplib.IMAP4.error):
            imap_sync._fetch_emails(mock_imap.return_value)
            
        imap_sync.logger.error.assert_called_with(
            "Error in fetch_emails: Search failed", exc_info=True)

def test_config_override_via_args(imap_sync: IMAPSync) -> None:
    """Test configuration override via command line arguments."""
    with patch("argparse.ArgumentParser.parse_args") as mock_parse:
        mock_args = MagicMock()
        mock_args.username = "custom_user"
        mock_args.password = "custom_pass"
        mock_args.days = 14
        mock_parse.return_value = mock_args
        
        imap_sync.parse_args()
        imap_sync.run()
        
        assert imap_sync.get_config_value("user") == "custom_user"
        imap_sync.logger.info.assert_any_call("Starting email sync with params:")

def test_batch_processing(imap_sync: IMAPSync, mock_db_conn: MagicMock) -> None:
    """Test batch processing of emails."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap.return_value.search.return_value = ("OK", [b"1 2 3 4 5"])
        mock_imap.return_value.fetch.side_effect = [
            ("OK", [(b"1 (RFC822 {11}", b"Email 1"), b")"]),
            ("OK", [(b"2 (RFC822 {11}", b"Email 2"), b")"]),
            ("OK", [(b"3 (RFC822 {11}", b"Email 3"), b")"]),
            ("OK", [(b"4 (RFC822 {11}", b"Email 4"), b")"]),
            ("OK", [(b"5 (RFC822 {11}", b"Email 5"), b")"]),
        ]
        
        imap_sync._fetch_emails(mock_imap.return_value, batch_size=2)
        
        assert mock_db_conn.execute.call_count == 5  # 5 emails stored
        imap_sync.logger.info.assert_any_call("Progress: 2/5 emails processed")
        imap_sync.logger.info.assert_any_call("Progress: 4/5 emails processed")

def test_message_id_deduplication(imap_sync: IMAPSync, mock_db_conn: MagicMock) -> None:
    """Test duplicate message ID handling."""
    mock_db_conn.execute.return_value.fetchall.return_value = [("123",)]
    
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap.return_value.search.return_value = ("OK", [b"1"])
        mock_imap.return_value.fetch.return_value = ("OK", [(b"", b"email data")])
        
        imap_sync._fetch_emails(mock_imap.return_value)
        
        mock_db_conn.execute.assert_not_called()  # Duplicate skipped
        imap_sync.logger.debug.assert_called_with(
            "Message 123 already exists in database, skipping")
