"""Service for enriching email metadata."""
from __future__ import annotations

import base64
from typing import Tuple, Any

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_connection
from dewey.llm import llm_utils
from database.models import AutomatedOperation, Email, EventLog
from django.db import transaction
from django.utils import timezone
import structlog


class EmailEnrichmentService(BaseScript):
    """Service for enriching email metadata like message bodies.

    Inherits from BaseScript and provides methods to extract email content,
    prioritize emails, and update email records in the database.
    """

    def __init__(self, config_section: str = 'crm') -> None:
        """Initialize EmailEnrichmentService.

        Args:
            config_section: The configuration section to use. Defaults to 'crm'.
        """
        super().__init__(config_section=config_section, requires_db=True)
        self.service = self.get_gmail_service()
        self.prioritizer = llm_utils.EmailPrioritizer()

    def get_gmail_service(self):
        """Get the Gmail service object.

        Returns:
            The Gmail service object.
        """
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials

            # Load credentials from config
            credentials_config = self.get_config_value('gmail_credentials')
            if not credentials_config:
                raise ValueError(
                    "Gmail credentials not found in configuration."
                )

            credentials = Credentials(**credentials_config)
            return build('gmail', 'v1', credentials=credentials)
        except Exception as e:
            self.logger.error(f"Error getting Gmail service: {e}")
            raise

    def run(self) -> None:
        """Placeholder for a run method.

        In a real implementation, this would likely drive the email
        enrichment process, possibly by querying for emails that need
        enrichment and calling `enrich_email` on them.
        """
        self.logger.info("EmailEnrichmentService run method called.")
        pass

    def extract_message_bodies(self, message_data: dict) -> Tuple[str, str]:
        """Extract plain and HTML message bodies from Gmail message data.

        Args:
            message_data: A dictionary containing the Gmail message data.

        Returns:
            A tuple containing the plain text body and the HTML body.
        """
        plain_body = ""
        html_body = ""

        if "payload" in message_data:
            payload = message_data["payload"]

            # Handle simple messages (body directly in payload)
            if "body" in payload and "data" in payload["body"]:
                if payload.get("mimeType") == "text/plain":
                    plain_body = base64.urlsafe_b64decode(
                        payload["body"]["data"],
                    ).decode()
                elif payload.get("mimeType") == "text/html":
                    html_body = base64.urlsafe_b64decode(
                        payload["body"]["data"],
                    ).decode()

            # Handle multipart messages (body in parts)
            if "parts" in payload:
                for part in payload["parts"]:
                    if (
                        part.get("mimeType") == "text/plain"
                        and "body" in part
                        and "data" in part["body"]
                    ):
                        plain_body = base64.urlsafe_b64decode(
                            part["body"]["data"],
                        ).decode()
                    elif (
                        part.get("mimeType") == "text/html"
                        and "body" in part
                        and "data" in part["body"]
                    ):
                        html_body = base64.urlsafe_b64decode(
                            part["body"]["data"],
                        ).decode()

        return plain_body, html_body

    def enrich_email(self, email: Email) -> bool:
        """Enrich an email with message body content and priority score.

        Args:
            email: The email to enrich.

        Returns:
            True if enrichment was successful, False otherwise.
        """
        enrichment_task = self.create_enrichment_task(email.id)

        try:
            # Get full message data
            message_data = (
                self.service.users()
                .messages()
                .get(userId="me", id=email.gmail_id, format="full")
                .execute()
            )

            # Extract message content
            plain_body, html_body = self.extract_message_bodies(message_data)

            # Score the email with enhanced prioritization
            priority, confidence, reason = self.prioritizer.score_email(email)

            with transaction.atomic():
                # Update email with new content and priority
                if plain_body or html_body:
                    email.plain_body = plain_body
                    email.html_body = html_body

                email.importance = priority
                email.email_metadata.update(
                    {
                        "priority_confidence": confidence,
                        "priority_reason": reason,
                        "priority_updated_at": timezone.now().isoformat(),
                    },
                )
                email.save()

                # Create event log for priority scoring
                EventLog.objects.create(
                    event_type="EMAIL_PRIORITY_SCORED",
                    email=email,
                    details={
                        "priority": priority,
                        "confidence": confidence,
                        "reason": reason,
                        "timestamp": timezone.now().isoformat(),
                    },
                    performed_by="email_enrichment",
                )

                self.complete_task(
                    enrichment_task,
                    result={
                        "plain_body_length": len(plain_body) if plain_body else 0,
                        "html_body_length": len(html_body) if html_body else 0,
                        "priority": priority,
                        "confidence": confidence,
                        "reason": reason,
                    },
                )

                self.logger.info(
                    "email_enriched",
                    email_id=email.id,
                    gmail_id=email.gmail_id,
                    plain_body_length=len(plain_body) if plain_body else 0,
                    html_body_length=len(html_body) if html_body else 0,
                    priority=priority,
                    confidence=confidence,
                    reason=reason,
                )
                return True

        except Exception as e:
            self.logger.exception(
                "email_enrichment_failed",
                email_id=email.id,
                gmail_id=email.gmail_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            if "enrichment_task" in locals():
                self.fail_task(enrichment_task, str(e))
            return False

    def create_enrichment_task(self, email_id: int) -> AutomatedOperation:
        """Create an automated operation task for email enrichment.

        Args:
            email_id: The ID of the email to enrich.

        Returns:
            The created AutomatedOperation object.
        """
        try:
            task = AutomatedOperation.objects.create(
                operation_type="email_enrichment",
                target_id=email_id,
                status="pending",
                start_time=timezone.now(),
            )
            self.logger.info(f"Created enrichment task {task.id} for email {email_id}")
            return task
        except Exception as e:
            self.logger.error(
                f"Failed to create enrichment task for email {email_id}: {e}"
            )
            raise

    def complete_task(
        self, task: AutomatedOperation, result: dict[str, Any]
    ) -> None:
        """Mark an automated operation task as completed.

        Args:
            task: The AutomatedOperation object to complete.
            result: A dictionary containing the results of the operation.
        """
        try:
            task.status = "completed"
            task.end_time = timezone.now()
            task.result = result
            task.save()
            self.logger.info(f"Completed enrichment task {task.id} with result: {result}")
        except Exception as e:
            self.logger.error(f"Failed to complete enrichment task {task.id}: {e}")
            raise

    def fail_task(self, task: AutomatedOperation, error_message: str) -> None:
        """Mark an automated operation task as failed.

        Args:
            task: The AutomatedOperation object to fail.
            error_message: The error message associated with the failure.
        """
        try:
            task.status = "failed"
            task.end_time = timezone.now()
            task.error_message = error_message
            task.save()
            self.logger.error(
                f"Enrichment task {task.id} failed with error: {error_message}"
            )
        except Exception as e:
            self.logger.error(f"Failed to fail enrichment task {task.id}: {e}")
            raise
