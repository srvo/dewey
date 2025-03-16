from datetime import UTC, datetime

from django.test import TestCase

from .models import GmailMessage, GoogleCalendarEvent, GoogleContact, GoogleDocument


class GoogleCalendarEventTest(TestCase):
    def setUp(self) -> None:
        self.event = GoogleCalendarEvent.objects.create(
            google_id="test123",
            summary="Test Event",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
        )

    def test_event_creation(self) -> None:
        assert self.event.google_id == "test123"
        assert self.event.summary == "Test Event"


class GoogleContactTest(TestCase):
    def setUp(self) -> None:
        self.contact = GoogleContact.objects.create(
            google_id="contact123",
            name="John Doe",
            email="john@example.com",
        )

    def test_contact_creation(self) -> None:
        assert self.contact.google_id == "contact123"
        assert self.contact.name == "John Doe"


class GoogleDocumentTest(TestCase):
    def setUp(self) -> None:
        self.doc = GoogleDocument.objects.create(
            google_id="doc123",
            title="Important Document",
            mime_type="application/pdf",
        )

    def test_document_creation(self) -> None:
        assert self.doc.google_id == "doc123"
        assert self.doc.title == "Important Document"


class GmailMessageTest(TestCase):
    def setUp(self) -> None:
        self.message = GmailMessage.objects.create(
            google_id="msg123",
            subject="Test Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
        )

    def test_message_creation(self) -> None:
        assert self.message.google_id == "msg123"
        assert self.message.subject == "Test Email"
