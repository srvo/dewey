"""Tests for the EmailProcessingService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from database.models import Contact, Email
from django.utils import timezone
from email_processing.service import EmailProcessingService


@pytest.fixture
def mock_gmail_client():
    """Create a mock Gmail client for testing."""
    client = MagicMock()
    client.get_message.return_value = {
        "id": "12345",
        "threadId": "67890",
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Subject", "value": "Test Subject"},
                {"name": "Date", "value": "Thu, 25 Jan 2024 10:00:00 -0800"},
            ],
        },
        "snippet": "Test message content",
        "raw": "raw message data",
    }
    return client


@pytest.fixture
def mock_email():
    """Create a mock Email instance."""
    email = create_autospec(Email, instance=True)
    email.id = 1
    email.gmail_id = "12345"
    email.subject = "Test Subject"
    email.received_at = timezone.now()
    return email


@pytest.fixture
def mock_contact():
    """Create a mock Contact instance."""
    contact = create_autospec(Contact, instance=True)
    contact.id = 1
    contact.email = "sender@example.com"
    return contact


class TestEmailProcessingService:
    """Tests for the EmailProcessingService."""

    def test_process_new_emails(
        self,
        mock_gmail_client,
        mock_email,
        mock_contact,
        db,
    ) -> None:
        """Test processing multiple new emails."""
        with (
            patch(
                "database.models.Contact.objects.get_or_create",
            ) as mock_get_or_create,
            patch("database.models.Email.objects.create") as mock_create_email,
            patch(
                "database.models.EmailContactAssociation.objects.create",
            ),
        ):
            mock_create_email.return_value = mock_email
            mock_get_or_create.return_value = (mock_contact, True)

            service = EmailProcessingService(gmail_client=mock_gmail_client)
            result = service.process_new_emails(["12345"])

            assert result == 1
            mock_create_email.assert_called_once_with(
                gmail_id="12345",
                thread_id="67890",
                subject="Test Subject",
                raw_content="raw message data",
                received_at=datetime(
                    2024,
                    1,
                    25,
                    18,
                    0,
                    tzinfo=UTC,
                ),  # -0800 converted to UTC
            )
            mock_get_or_create.assert_any_call(email="sender@example.com")

    def test_single_email_processing(
        self,
        mock_gmail_client,
        mock_email,
        mock_contact,
        db,
    ) -> None:
        """Test processing a single email."""
        with (
            patch(
                "database.models.Contact.objects.get_or_create",
            ) as mock_get_or_create,
            patch("database.models.Email.objects.create") as mock_create_email,
            patch(
                "database.models.EmailContactAssociation.objects.create",
            ),
        ):
            mock_create_email.return_value = mock_email
            mock_get_or_create.return_value = (mock_contact, True)

            service = EmailProcessingService(gmail_client=mock_gmail_client)
            email_data = mock_gmail_client.get_message.return_value
            result = service._process_single_email(email_data)

            assert result is True
            mock_create_email.assert_called_once()
            mock_get_or_create.assert_any_call(email="sender@example.com")

    def test_contact_processing_duplicate_contacts(
        self,
        mock_gmail_client,
        mock_email,
        mock_contact,
        db,
    ) -> None:
        """Test processing duplicate contacts."""
        with (
            patch(
                "database.models.Contact.objects.get_or_create",
            ) as mock_get_or_create,
            patch("database.models.Email.objects.create") as mock_create_email,
            patch(
                "database.models.EmailContactAssociation.objects.create",
            ),
        ):
            mock_create_email.return_value = mock_email
            mock_get_or_create.return_value = (mock_contact, False)

            service = EmailProcessingService(gmail_client=mock_gmail_client)
            email_data = mock_gmail_client.get_message.return_value
            result = service._process_single_email(email_data)

            assert result is True
            mock_get_or_create.assert_any_call(email="sender@example.com")

    def test_error_handling_database_failure(
        self,
        mock_gmail_client,
        mock_contact,
        db,
    ) -> None:
        """Test handling of database errors."""
        with (
            patch(
                "database.models.Contact.objects.get_or_create",
            ) as mock_get_or_create,
            patch("database.models.Email.objects.create") as mock_create_email,
        ):
            mock_get_or_create.return_value = (mock_contact, True)
            mock_create_email.side_effect = Exception("Database error")

            service = EmailProcessingService(gmail_client=mock_gmail_client)
            email_data = mock_gmail_client.get_message.return_value
            result = service._process_single_email(email_data)

            assert not result
            # Don't check get_or_create call since it won't be called due to the error

    def test_successful_email_processing(
        self,
        mock_gmail_client,
        mock_email,
        mock_contact,
        db,
    ) -> None:
        """Test successful processing of an email."""
        with (
            patch(
                "database.models.Contact.objects.get_or_create",
            ) as mock_get_or_create,
            patch("database.models.Email.objects.create") as mock_create_email,
            patch(
                "database.models.EmailContactAssociation.objects.create",
            ),
        ):
            mock_create_email.return_value = mock_email
            mock_get_or_create.return_value = (mock_contact, True)

            service = EmailProcessingService(gmail_client=mock_gmail_client)
            email_data = mock_gmail_client.get_message.return_value
            result = service._process_single_email(email_data)

            assert result is True
            mock_get_or_create.assert_any_call(email="sender@example.com")
