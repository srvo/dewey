import pytest
from database.models import Email, RawEmail
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone


class EmailProcessingIntegrationTests(TestCase):
    """Integration tests for email processing."""

    def test_email_creation(self) -> None:
        """Test successful email creation."""
        email: Email = Email.objects.create(
            gmail_id="test123",
            subject="Test Email",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            received_at=timezone.now(),
            raw_content="This is a test email body.",
        )
        assert email.subject == "Test Email"
        assert email.from_email == "test@example.com"
        assert email.to_emails == ["recipient@example.com"]

    def test_invalid_email_creation(self) -> None:
        """Test handling of invalid email creation (missing fields)."""
        with pytest.raises(IntegrityError):
            Email.objects.create(
                subject="Test Email",
                # Missing from_email and received_at
            )

    def test_raw_email_creation(self) -> None:
        """Test successful raw email creation."""
        Email.objects.create(
            gmail_id="test123",
            subject="Test Email",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            received_at=timezone.now(),
            raw_content="This is a test email body.",
        )
        raw_email: RawEmail = RawEmail.objects.create(
            gmail_message_id="msg123",
            thread_id="thread1",
            history_id="hist1",
            raw_data={"content": "Raw email data"},
        )
        assert raw_email.gmail_message_id == "msg123"
        assert raw_email.raw_data["content"] == "Raw email data"

    def test_invalid_raw_email_creation(self) -> None:
        """Test handling of invalid raw email creation (missing fields)."""
        with pytest.raises(IntegrityError):
            RawEmail.objects.create(
                # Missing gmail_message_id and raw_data
                thread_id="thread1",
                history_id="hist1",
            )

    def test_email_processing_error_handling(self) -> None:
        """Test error handling during email processing."""
        Email.objects.create(
            gmail_id="test123",
            subject="Test Email",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            received_at=timezone.now(),
            raw_content="This is a test email body.",
        )

        with pytest.raises(IntegrityError):
            RawEmail.objects.create(
                gmail_message_id="msg123",
                thread_id="thread1",
                history_id="hist1",
                raw_data=None,  # Invalid raw data
            )
