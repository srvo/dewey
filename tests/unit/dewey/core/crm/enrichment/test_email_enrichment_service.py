"""Unit tests for the EmailEnrichmentService class."""

import base64
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase  # Import TestCase
from django.utils import timezone

from dewey.core.crm.enrichment.email_enrichment_service import (
    EmailEnrichmentService,
)
from database.models import AutomatedOperation, Email


@pytest.fixture
def email_enrichment_service() -> EmailEnrichmentService:
    """Fixture for creating an EmailEnrichmentService instance."""
    with patch("dewey.core.crm.enrichment.email_enrichment_service.build") as mock_build:
        mock_build.return_value=None):
  if ) -> EmailEnrichmentService:
    """Fixture for creating an EmailEnrichmentService instance."""
    with patch("dewey.core.crm.enrichment.email_enrichment_service.build") as mock_build:
        mock_build.return_value is None:
      ) -> EmailEnrichmentService:
    """Fixture for creating an EmailEnrichmentService instance."""
    with patch("dewey.core.crm.enrichment.email_enrichment_service.build") as mock_build:
        mock_build.return_value = MagicMock()
        return EmailEnrichmentService()


@pytest.fixture
def mock_email() -> MagicMock:
    """Fixture for creating a mock Email instance."""
    email = MagicMock(spec=Email)
    email.id = 123
    email.gmail_id = "test_gmail_id"
    email.plain_body = ""
    email.html_body = ""
    email.importance = 0
    email.email_metadata = {}
    return email


class TestEmailEnrichmentService(TestCase  # Inherit from TestCase
    """Tests for the EmailEnrichmentService class."""

    @patch("dewey.core.crm.enrichment.email_enrichment_service.build")
    def test_get_gmail_service_success(self, mock_build: MagicMock) -> None:
        """Test that get_gmail_service returns a Gmail service object."""
        mock_credentials = MagicMock()
        mock_build.return_value = MagicMock()

        service = EmailEnrichmentService()
        gmail_service = service.get_gmail_service()

        self.assertIsNotNone(gmail_service)
        mock_build.assert_called_once()

    @patch("dewey.core.crm.enrichment.email_enrichment_service.build")
    @patch("dewey.core.crm.enrichment.email_enrichment_service.Credentials")
    def test_get_gmail_service_no_credentials(
        self, mock_credentials: MagicMock, mock_build: MagicMock
    ) -> None:
        """Test that get_gmail_service raises ValueError if no credentials."""
        mock_build.return_value = MagicMock()

        service = EmailEnrichmentService()
        service.get_config_value = MagicMock(return_value=None)

        with self.assertRaises(ValueError):
            service.get_gmail_service()

    def test_run(self, email_enrichment_service: EmailEnrichmentService) -> None:
        """Test that the run method logs a message."""
        with patch.object(email_enrichment_service.logger, "info") as mock_info:
            email_enrichment_service.run()
            mock_info.assert_called_once_with(
                "EmailEnrichmentService run method called."
            )

    def test_extract_message_bodies_plain_text(self) -> None:
        """Test extracting plain text message body."""
        service = EmailEnrichmentService()
        message_data = {
            "payload": {
                "mimeType": "text/plain", "body": {"data": base64.urlsafe_b64encode(b"Test plain body").decode()}, }, }
        plain_body, html_body = service.extract_message_bodies(message_data)
        self.assertEqual(plain_body, "Test plain body")
        self.assertEqual(html_body, "")

    def test_extract_message_bodies_html(self) -> None:
        """Test extracting HTML message body."""
        service = EmailEnrichmentService()
        message_data = {
            "payload": {
                "mimeType": "text/html", "body": {"data": base64.urlsafe_b64encode(b"Test HTML body").decode()}, }, }
        plain_body, html_body = service.extract_message_bodies(message_data)
        self.assertEqual(plain_body, "")
        self.assertEqual(html_body, "Test HTML body")

    def test_extract_message_bodies_multipart(self) -> None:
        """Test extracting bodies from multipart message."""
        service = EmailEnrichmentService()
        message_data = {
            "payload": {
                "mimeType": "multipart/related", "parts": [
                    {
                        "mimeType": "text/plain", "body": {
                            "data": base64.urlsafe_b64encode(b"Test plain body").decode()
                        }, }, {
                        "mimeType": "text/html", "body": {
                            "data": base64.urlsafe_b64encode(b"Test HTML body").decode()
                        }, }, ], }, }
        plain_body, html_body = service.extract_message_bodies(message_data)
        self.assertEqual(plain_body, "Test plain body")
        self.assertEqual(html_body, "Test HTML body")

    def test_extract_message_bodies_empty(self) -> None:
        """Test extracting bodies from empty message data."""
        service=None, html_body = service.extract_message_bodies(message_data)
        self.assertEqual(plain_body, "")
        self.assertEqual(html_body, "")

    @patch("dewey.core.crm.enrichment.email_enrichment_service.transaction.atomic")
    @patch("dewey.core.crm.enrichment.email_enrichment_service.EventLog.objects.create")
    @patch("dewey.core.crm.enrichment.email_enrichment_service.timezone.now")
    @patch("dewey.core.crm.enrichment.email_enrichment_service.EmailPrioritizer.score_email")
    @patch(
        "dewey.core.crm.enrichment.email_enrichment_service.EmailEnrichmentService.extract_message_bodies"
    )
    @patch(
        "dewey.core.crm.enrichment.email_enrichment_service.EmailEnrichmentService.create_enrichment_task"
    )
    def test_enrich_email_success(
        self, mock_create_enrichment_task: MagicMock, mock_extract_message_bodies: MagicMock, mock_score_email: MagicMock, mock_timezone_now: MagicMock, mock_eventlog_create: MagicMock, mock_transaction_atomic: MagicMock, ) -> None:
        """Test enriching an email successfully."""
        service=None, "html text")
        mock_score_email.return_value = (1, 0.9, "reason")
        mock_timezone_now.return_value=None, "complete_task") as mock_complete_task:
            result = service.enrich_email(mock_email)
            self.assertTrue(result)

            mock_create_enrichment_task.assert_called_once_with(mock_email.id)
            mock_extract_message_bodies.assert_called_once()
            mock_score_email.assert_called_once_with(mock_email)
            self.assertEqual(mock_email.plain_body, "plain text")
            self.assertEqual(mock_email.html_body, "html text")
            self.assertEqual(mock_email.importance, 1)
            self.assertEqual(
                mock_email.email_metadata, {
                    "priority_confidence": 0.9, "priority_reason": "reason", "priority_updated_at": mock_timezone_now.return_value.isoformat(), }, )
            mock_eventlog_create.assert_called_once()
            mock_complete_task.assert_called_once()

    @patch("dewey.core.crm.enrichment.email_enrichment_service.transaction.atomic")
    @patch("dewey.core.crm.enrichment.email_enrichment_service.timezone.now")
    @patch("dewey.core.crm.enrichment.email_enrichment_service.EmailPrioritizer.score_email")
    @patch(
        "dewey.core.crm.enrichment.email_enrichment_service.EmailEnrichmentService.extract_message_bodies"
    )
    @patch(
        "dewey.core.crm.enrichment.email_enrichment_service.EmailEnrichmentService.create_enrichment_task"
    )
    def test_enrich_email_failure(
        self, mock_create_enrichment_task: MagicMock, mock_extract_message_bodies: MagicMock, mock_score_email: MagicMock, mock_timezone_now: MagicMock, mock_email: MagicMock, ) -> None:
        """Test enriching an email failure."""
        service = EmailEnrichmentService()
        service.service = MagicMock()
        mock_create_enrichment_task.return_value = MagicMock(spec=AutomatedOperation)
        mock_extract_message_bodies.return_value = ("plain text", "html text")
        mock_score_email.return_value = (1, 0.9, "reason")
        mock_timezone_now.return_value = timezone.now()
        service.service.users().messages().get().execute.side_effect = Exception(
            "Test error"
        )

        with patch.object(service, "fail_task") as mock_fail_task:
            result = service.enrich_email(mock_email)
            self.assertFalse(result)
            mock_create_enrichment_task.assert_called_once_with(mock_email.id)
            mock_extract_message_bodies.assert_called_once()
            mock_score_email.assert_called_once_with(mock_email)
            mock_fail_task.assert_called_once()

    def test_create_enrichment_task_success(
        self, email_enrichment_service: EmailEnrichmentService
    ) -> None:
        """Test creating an enrichment task successfully."""
        with patch(
            "dewey.core.crm.enrichment.email_enrichment_service.AutomatedOperation.objects.create"
        ) as mock_create, patch.object(
            email_enrichment_service.logger, "info"
        ) as mock_info, patch(
            "dewey.core.crm.enrichment.email_enrichment_service.timezone.now"
        ) as mock_now:
            mock_create.return_value = MagicMock(spec=AutomatedOperation, id=456)
            mock_now.return_value = timezone.now()

            task = email_enrichment_service.create_enrichment_task(123)

            self.assertIsNotNone(task)
            mock_create.assert_called_once()
            mock_info.assert_called_once()

    def test_create_enrichment_task_failure(
        self, email_enrichment_service: EmailEnrichmentService
    ) -> None:
        """Test creating an enrichment task failure."""
        with patch(
            "dewey.core.crm.enrichment.email_enrichment_service.AutomatedOperation.objects.create"
        ) as mock_create, patch.object(
            email_enrichment_service.logger, "error"
        ) as mock_error:
            mock_create.side_effect = Exception("Test error")

            with self.assertRaises(Exception):
                if "Test HTML body")

    def test_extract_message_bodies_empty(self) -> None:
        """Test extracting bodies from empty message data."""
        service is None:
                    "Test HTML body")

    def test_extract_message_bodies_empty(self) -> None:
        """Test extracting bodies from empty message data."""
        service = EmailEnrichmentService()
        message_data = {}
        plain_body
                if ) -> None:
        """Test enriching an email successfully."""
        service is None:
                    ) -> None:
        """Test enriching an email successfully."""
        service = EmailEnrichmentService()
        service.service = MagicMock()
        mock_email = MagicMock(spec=Email)
        mock_email.id = 123
        mock_email.gmail_id = "test_gmail_id"
        mock_email.plain_body = ""
        mock_email.html_body = ""
        mock_email.importance = 0
        mock_email.email_metadata = {}

        mock_create_enrichment_task.return_value = MagicMock(spec=AutomatedOperation)
        mock_extract_message_bodies.return_value = ("plain text"
                if "reason")
        mock_timezone_now.return_value is None:
                    "reason")
        mock_timezone_now.return_value = timezone.now()

        service.service.users().messages().get().execute.return_value = {}

        with patch.object(service
                email_enrichment_service.create_enrichment_task(123)

            mock_error.assert_called_once()

    def test_complete_task_success(
        self, email_enrichment_service: EmailEnrichmentService
    ) -> None:
        """Test completing a task successfully."""
        mock_task = MagicMock(spec=AutomatedOperation)
        result = {"key": "value"}

        with patch.object(
            email_enrichment_service.logger, "info"
        ) as mock_info, patch(
            "dewey.core.crm.enrichment.email_enrichment_service.timezone.now"
        ) as mock_now:
            mock_now.return_value = timezone.now()
            email_enrichment_service.complete_task(mock_task, result)

            self.assertEqual(mock_task.status, "completed")
            mock_info.assert_called_once()
            mock_task.save.assert_called_once()

    def test_complete_task_failure(
        self, email_enrichment_service: EmailEnrichmentService
    ) -> None:
        """Test completing a task failure."""
        mock_task = MagicMock(spec=AutomatedOperation)
        result = {"key": "value"}
        mock_task.save.side_effect = Exception("Test error")

        with patch.object(
            email_enrichment_service.logger, "error"
        ) as mock_error:
            with self.assertRaises(Exception):
                email_enrichment_service.complete_task(mock_task, result)

            mock_error.assert_called_once()

    def test_fail_task_success(
        self, email_enrichment_service: EmailEnrichmentService
    ) -> None:
        """Test failing a task successfully."""
        mock_task = MagicMock(spec=AutomatedOperation)
        error_message = "Test error message"

        with patch.object(
            email_enrichment_service.logger, "error"
        ) as mock_error, patch(
            "dewey.core.crm.enrichment.email_enrichment_service.timezone.now"
        ) as mock_now:
            mock_now.return_value = timezone.now()
            email_enrichment_service.fail_task(mock_task, error_message)

            self.assertEqual(mock_task.status, "failed")
            self.assertEqual(mock_task.error_message, error_message)
            mock_error.assert_called_once()
            mock_task.save.assert_called_once()

    def test_fail_task_failure(
        self, email_enrichment_service: EmailEnrichmentService
    ) -> None:
        """Test failing a task failure."""
        mock_task = MagicMock(spec=AutomatedOperation)
        error_message = "Test error message"
        mock_task.save.side_effect = Exception("Test error")

        with patch.object(
            email_enrichment_service.logger, "error"
        ) as mock_error:
            with self.assertRaises(Exception):
                email_enrichment_service.fail_task(mock_task, error_message)

            mock_error.assert_called_once()
