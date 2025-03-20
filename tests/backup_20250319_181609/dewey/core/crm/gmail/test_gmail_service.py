"""Tests for Gmail service."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from dewey.core.crm.gmail.gmail_service import GmailService
from dewey.core.crm.gmail.models import RawEmail

class TestGmailService:
    """Test suite for Gmail service."""

    @pytest.fixture
    def service(self, mock_gmail_service, mock_db_connection, tmp_path):
        """Create a GmailService instance."""
        checkpoint_file = tmp_path / "gmail_checkpoint.json"
        with patch("googleapiclient.discovery.build", return_value=mock_gmail_service):
            return GmailService(
                checkpoint_file=str(checkpoint_file),
                batch_size=100,
                database_name="test.duckdb"
            )

    def test_initialization(self, service):
        """Test service initialization."""
        assert service.batch_size == 100
        assert service.service is not None
        assert service.classifier is not None

    def test_build_service(self, service):
        """Test Gmail service building."""
        assert service.service is not None
        service.service.users().messages().list.assert_not_called()

    def test_fetch_emails(self, service, mock_gmail_service):
        """Test email fetching."""
        emails = service.fetch_emails(days=7)
        assert len(emails) > 0
        assert isinstance(emails[0], RawEmail)
        assert emails[0].gmail_id == "msg123"
        assert emails[0].thread_id == "thread123"

    def test_process_email(self, service, sample_email_data):
        """Test email processing."""
        result = service.process_email(sample_email_data)
        assert result is not None
        assert "thread_id" in result
        assert "from_email" in result
        assert "subject" in result

    def test_extract_contacts(self, service, sample_email_data):
        """Test contact extraction from email."""
        contacts = service.extract_contacts(sample_email_data)
        assert len(contacts) > 0
        assert contacts[0]["email"] == "john@example.com"
        assert contacts[0]["full_name"] == "John Doe"

    def test_classify_email(self, service, sample_email_data):
        """Test email classification."""
        classification = service.classifier.classify_email(sample_email_data)
        assert classification is not None
        assert "category" in classification
        assert "confidence" in classification

    def test_checkpoint_management(self, service, sample_gmail_checkpoint):
        """Test checkpoint management."""
        # Save checkpoint
        service.save_checkpoint("msg123", ["thread123"])
        
        # Load checkpoint
        checkpoint = service.load_checkpoint()
        assert checkpoint["last_message_id"] == "msg123"
        assert "thread123" in checkpoint["processed_threads"]

    def test_batch_processing(self, service, mock_gmail_service):
        """Test batch email processing."""
        # Mock multiple pages of results
        mock_gmail_service.users().messages().list().execute.side_effect = [
            {
                "messages": [{"id": f"msg{i}", "threadId": f"thread{i}"} 
                           for i in range(5)],
                "nextPageToken": "token1"
            },
            {
                "messages": [{"id": f"msg{i}", "threadId": f"thread{i}"} 
                           for i in range(5, 10)],
                "nextPageToken": None
            }
        ]
        
        emails = service.fetch_emails(days=7, batch_size=5)
        assert len(emails) == 10
        assert all(isinstance(email, RawEmail) for email in emails)

    def test_error_handling(self, service):
        """Test error handling."""
        # Test with invalid email data
        with pytest.raises(ValueError):
            service.process_email(None)
        
        # Test with network error
        service.service.users().messages().list.side_effect = Exception("Network error")
        with pytest.raises(Exception):
            service.fetch_emails(days=1)

    @pytest.mark.integration
    def test_full_sync_workflow(self, service, mock_gmail_service, test_db):
        """Integration test for full sync workflow."""
        # Setup test data
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg123", "threadId": "thread123"}],
            "nextPageToken": None
        }
        
        # Run sync
        service.import_emails(days=7)
        
        # Verify database state
        result = test_db.execute("""
            SELECT COUNT(*) FROM crm_emails 
            WHERE thread_id = 'thread123'
        """).fetchone()
        assert result[0] == 1
        
        # Verify contacts were extracted
        result = test_db.execute("""
            SELECT COUNT(*) FROM crm_contacts 
            WHERE email = 'john@example.com'
        """).fetchone()
        assert result[0] == 1
        
        # Verify checkpoint was saved
        checkpoint = service.load_checkpoint()
        assert "msg123" in checkpoint["processed_threads"] 