from datetime import datetime

import pytest
from database.models import (
    Config,
    Contact,
    Email,
    EmailLabelHistory,
    EventLog,
    Message,
    MessageThreadAssociation,
    RawEmail,
    Thread,
)
from django.core.exceptions import ValidationError
from django.test import TestCase

pytestmark = pytest.mark.django_db


class EmailModelTests(TestCase):
    def test_email_creation(self) -> None:
        """Test valid email creation."""
        email = Email.objects.create(
            gmail_id="test123",
            thread_id="thread1",
            subject="Test Email",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            received_at=datetime.utcnow(),
            raw_content="Test content",
            labels=["INBOX"],
            email_metadata={},
        )

        assert email.id is not None
        assert email.gmail_id == "test123"
        assert email.thread_id == "thread1"
        assert email.subject == "Test Email"
        assert email.from_email == "test@example.com"
        assert isinstance(email.received_at, datetime)
        assert email.raw_content == "Test content"
        assert email.labels == ["INBOX"]
        assert not email.processed  # Test default value

    def test_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            email = Email()
            email.full_clean()  # Triggers validation

    def test_to_emails_validation(self) -> None:
        """Test validation of to_emails field."""
        with pytest.raises(ValidationError):
            email = Email(
                gmail_id="test123",
                from_email="test@example.com",
                received_at=datetime.utcnow(),
                to_emails="not-a-list",  # Invalid type
            )
            email.full_clean()


class ContactModelTests(TestCase):
    def test_contact_creation(self) -> None:
        contact = Contact.objects.create(
            primary_email="test@example.com",
            first_name="Test",
            last_name="User",
        )

        assert contact.id is not None
        assert contact.primary_email == "test@example.com"
        assert contact.first_name == "Test"
        assert contact.last_name == "User"

    def test_email_uniqueness(self) -> None:
        """Test that email field is unique."""
        Contact.objects.create(primary_email="test@example.com")
        with pytest.raises(ValidationError):
            Contact(primary_email="test@example.com").full_clean()


class RawEmailModelTests(TestCase):
    """Tests for RawEmail model."""

    def test_checksum_calculation(self) -> None:
        """Test checksum calculation and verification."""
        # Create first raw email
        raw_email1 = RawEmail.objects.create(
            gmail_message_id="msg123",
            thread_id="thread1",
            history_id="hist1",
            raw_data={"test": "data"},
            checksum="initial",  # Add initial checksum
        )

        # Verify checksum was calculated
        assert raw_email1.checksum != "initial"
        assert isinstance(raw_email1.checksum, str)
        assert len(raw_email1.checksum) > 0

        # Create second raw email with different data
        raw_email2 = RawEmail.objects.create(
            gmail_message_id="msg124",
            thread_id="thread1",
            history_id="hist1",
            raw_data={"new": "data"},
            checksum="initial",  # Add initial checksum
        )

        # Verify checksums are different
        assert raw_email1.checksum != raw_email2.checksum


class EventLogModelTests(TestCase):
    def test_event_log_creation(self) -> None:
        email = Email.objects.create(
            gmail_id="test123",
            from_email="test@example.com",
            received_at=datetime.utcnow(),
            to_emails=["recipient@example.com"],
        )
        event = EventLog.objects.create(
            event_type="EMAIL_PROCESSED",
            email=email,
            details={"action": "processed"},
            performed_by="system",
        )

        assert event.id is not None
        assert event.event_type == "EMAIL_PROCESSED"
        assert event.email == email
        assert event.details == {"action": "processed"}


class ConfigModelTests(TestCase):
    def test_config_creation(self) -> None:
        config = Config.objects.create(key="test_key", value="test_value")

        assert config.id is not None
        assert config.key == "test_key"
        assert config.value == "test_value"


class EmailLabelHistoryTests(TestCase):
    def test_label_history_creation(self) -> None:
        email = Email.objects.create(
            gmail_id="test123",
            from_email="test@example.com",
            received_at=datetime.utcnow(),
            to_emails=["recipient@example.com"],
        )
        history = EmailLabelHistory.objects.create(
            email=email,
            label_id="INBOX",
            action="ADDED",
            changed_by="system",
        )

        assert history.id is not None
        assert history.email == email
        assert history.label_id == "INBOX"
        assert history.action == "ADDED"


class MessageThreadAssociationTests(TestCase):
    def test_thread_association_creation(self) -> None:
        """Test creating a message-thread association."""
        message = Message.objects.create(
            subject="Test Message",
            body="Test Body",
            sender="test@example.com",
        )
        thread = Thread.objects.create(subject="Test Thread")
        association = MessageThreadAssociation.objects.create(
            message=message,
            thread=thread,
        )
        assert association.id is not None
        assert association.message == message
        assert association.thread == thread
