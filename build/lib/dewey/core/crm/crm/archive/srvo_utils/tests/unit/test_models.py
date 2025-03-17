from datetime import datetime

import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase

from database.models import (
    Config,
    Contact,
    Email,
    EmailLabelHistory,
    EventLog,
    MessageThreadAssociation,
    RawEmail,
    Message,
    Thread,
)

pytestmark = pytest.mark.django_db


class EmailModelTests(TestCase):
    def test_email_creation(self):
        """Test valid email creation"""
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

        self.assertIsNotNone(email.id)
        self.assertEqual(email.gmail_id, "test123")
        self.assertEqual(email.thread_id, "thread1")
        self.assertEqual(email.subject, "Test Email")
        self.assertEqual(email.from_email, "test@example.com")
        self.assertIsInstance(email.received_at, datetime)
        self.assertEqual(email.raw_content, "Test content")
        self.assertEqual(email.labels, ["INBOX"])
        self.assertFalse(email.processed)  # Test default value

    def test_required_fields(self):
        """Test that required fields are enforced"""
        with self.assertRaises(ValidationError):
            email = Email()
            email.full_clean()  # Triggers validation

    def test_to_emails_validation(self):
        """Test validation of to_emails field"""
        with self.assertRaises(ValidationError):
            email = Email(
                gmail_id="test123",
                from_email="test@example.com",
                received_at=datetime.utcnow(),
                to_emails="not-a-list",  # Invalid type
            )
            email.full_clean()


class ContactModelTests(TestCase):
    def test_contact_creation(self):
        contact = Contact.objects.create(
            primary_email="test@example.com", first_name="Test", last_name="User"
        )

        self.assertIsNotNone(contact.id)
        self.assertEqual(contact.primary_email, "test@example.com")
        self.assertEqual(contact.first_name, "Test")
        self.assertEqual(contact.last_name, "User")

    def test_email_uniqueness(self):
        """Test that email field is unique"""
        Contact.objects.create(primary_email="test@example.com")
        with self.assertRaises(ValidationError):
            Contact(primary_email="test@example.com").full_clean()


class RawEmailModelTests(TestCase):
    """Tests for RawEmail model."""

    def test_checksum_calculation(self):
        """Test checksum calculation and verification"""
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
    def test_event_log_creation(self):
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

        self.assertIsNotNone(event.id)
        self.assertEqual(event.event_type, "EMAIL_PROCESSED")
        self.assertEqual(event.email, email)
        self.assertEqual(event.details, {"action": "processed"})


class ConfigModelTests(TestCase):
    def test_config_creation(self):
        config = Config.objects.create(key="test_key", value="test_value")

        self.assertIsNotNone(config.id)
        self.assertEqual(config.key, "test_key")
        self.assertEqual(config.value, "test_value")


class EmailLabelHistoryTests(TestCase):
    def test_label_history_creation(self):
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

        self.assertIsNotNone(history.id)
        self.assertEqual(history.email, email)
        self.assertEqual(history.label_id, "INBOX")
        self.assertEqual(history.action, "ADDED")


class MessageThreadAssociationTests(TestCase):
    def test_thread_association_creation(self):
        """Test creating a message-thread association."""
        message = Message.objects.create(
            subject="Test Message", body="Test Body", sender="test@example.com"
        )
        thread = Thread.objects.create(subject="Test Thread")
        association = MessageThreadAssociation.objects.create(
            message=message, thread=thread
        )
        self.assertIsNotNone(association.id)
        self.assertEqual(association.message, message)
        self.assertEqual(association.thread, thread)
