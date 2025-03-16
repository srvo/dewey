# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

import pytest
from database.models import Email, RawEmail
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone


class EmailProcessingIntegrationTests(TestCase):
    def test_email_creation(self) -> None:
        email = Email.objects.create(
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
        # Test missing required fields
        with pytest.raises(IntegrityError):
            Email.objects.create(
                subject="Test Email",
                # Missing from_email and received_at
            )

    def test_raw_email_creation(self) -> None:
        Email.objects.create(
            gmail_id="test123",
            subject="Test Email",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            received_at=timezone.now(),
            raw_content="This is a test email body.",
        )
        raw_email = RawEmail.objects.create(
            gmail_message_id="msg123",
            thread_id="thread1",
            history_id="hist1",
            raw_data={"content": "Raw email data"},
        )
        assert raw_email.gmail_message_id == "msg123"
        assert raw_email.raw_data["content"] == "Raw email data"

    def test_invalid_raw_email_creation(self) -> None:
        # Test missing required fields
        with pytest.raises(IntegrityError):
            RawEmail.objects.create(
                # Missing gmail_message_id and raw_data
                thread_id="thread1",
                history_id="hist1",
            )

    def test_email_processing_error_handling(self) -> None:
        # Test error handling during email processing
        Email.objects.create(
            gmail_id="test123",
            subject="Test Email",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            received_at=timezone.now(),
            raw_content="This is a test email body.",
        )

        # Test invalid raw data
        with pytest.raises(IntegrityError):
            RawEmail.objects.create(
                gmail_message_id="msg123",
                thread_id="thread1",
                history_id="hist1",
                raw_data=None,  # Invalid raw data
            )
