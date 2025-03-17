from django.test import TestCase
from django.db.utils import IntegrityError
from django.utils import timezone
from database.models import Email, RawEmail


class EmailProcessingIntegrationTests(TestCase):
    def test_email_creation(self):
        email = Email.objects.create(
            gmail_id="test123",
            subject="Test Email",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            received_at=timezone.now(),
            raw_content="This is a test email body.",
        )
        self.assertEqual(email.subject, "Test Email")
        self.assertEqual(email.from_email, "test@example.com")
        self.assertEqual(email.to_emails, ["recipient@example.com"])

    def test_invalid_email_creation(self):
        # Test missing required fields
        with self.assertRaises(IntegrityError):
            Email.objects.create(
                subject="Test Email",
                # Missing from_email and received_at
            )

    def test_raw_email_creation(self):
        email = Email.objects.create(
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
        self.assertEqual(raw_email.gmail_message_id, "msg123")
        self.assertEqual(raw_email.raw_data["content"], "Raw email data")

    def test_invalid_raw_email_creation(self):
        # Test missing required fields
        with self.assertRaises(IntegrityError):
            RawEmail.objects.create(
                # Missing gmail_message_id and raw_data
                thread_id="thread1",
                history_id="hist1",
            )

    def test_email_processing_error_handling(self):
        # Test error handling during email processing
        email = Email.objects.create(
            gmail_id="test123",
            subject="Test Email",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            received_at=timezone.now(),
            raw_content="This is a test email body.",
        )

        # Test invalid raw data
        with self.assertRaises(IntegrityError):
            RawEmail.objects.create(
                gmail_message_id="msg123",
                thread_id="thread1",
                history_id="hist1",
                raw_data=None,  # Invalid raw data
            )
