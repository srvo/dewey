"""Unit tests for IMAP email synchronization."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import email
from imaplib import IMAP4_SSL

from dewey.core.crm.email.imap_import_standalone import IMAPSync

@pytest.fixture
def imap_sync():
    """IMAPSync instance with mocked dependencies"""
    with patch("dewey.core.db.connection.DatabaseConnection") as mock_db:
        sync = IMAPSync()
        sync.db_conn = mock_db
        sync.logger = MagicMock()
        return sync

def test_initialization(imap_sync):
    """Test script initializes with proper configuration"""
    assert imap_sync.name == "imap_sync"
    assert imap_sync.config_section == "imap"
    assert imap_sync.requires_db is True

def test_database_initialization(imap_sync):
    """Test database schema initialization"""
    imap_sync._init_database()
    imap_sync.db_conn.execute.assert_any_call(IMAPSync.EMAIL_SCHEMA)
    assert imap_sync.db_conn.execute.call_count == len(IMAPSync.EMAIL_INDEXES) + 1

def test_imap_connection(imap_sync):
    """Test IMAP connection flow"""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        imap_sync._connect_imap({
            "host": "imap.test.com",
            "port": 993,
            "user": "test",
            "password": "pass",
            "mailbox": "INBOX"
        })
        mock_imap.return_value.login.assert_called_with("test", "pass")
        mock_imap.return_value.select.assert_called_with("INBOX")

def test_full_sync_flow(imap_sync):
    """Test complete sync workflow"""
    with patch.object(imap_sync, "_search_emails") as mock_search, \
         patch.object(imap_sync, "_fetch_email_batches") as mock_fetch, \
         patch.object(imap_sync, "_store_emails") as mock_store:
        
        mock_search.return_value = ["1", "2", "3"]
        mock_fetch.return_value = [{"msg_id": "1"}, {"msg_id": "2"}]
        
        imap_sync.run()
        
        mock_store.assert_called_with([{"msg_id": "1"}, {"msg_id": "2"}])
        imap_sync.logger.info.assert_any_call("IMAP sync completed successfully")

def test_error_handling(imap_sync):
    """Test error handling during sync"""
    with patch.object(imap_sync, "_connect_imap", side_effect=Exception("Test error")):
        with pytest.raises(Exception):
            imap_sync.run()
        imap_sync.logger.error.assert_called_with("IMAP sync failed: Test error", exc_info=True)
