"""Service for enriching email metadata."""

import base64
import structlog
from django.db import transaction
from database.models import Email, AutomatedOperation, EventLog
from .gmail_history_sync import get_gmail_service
from .prioritization import EmailPrioritizer
from django.utils import timezone

logger = structlog.get_logger(__name__)


class EmailEnrichmentService(AutomatedOperation):
    """Service for enriching email metadata like message bodies."""

    def __init__(self):
        super().__init__(entity_type="email", task_type="email_metadata")
        self.service = get_gmail_service()
        self.prioritizer = EmailPrioritizer()

    def extract_message_bodies(self, message_data: dict) -> tuple[str, str]:
        """Extract plain and HTML message bodies from Gmail message data."""
        plain_body = ""
        html_body = ""

        if "payload" in message_data:
            payload = message_data["payload"]

            # Handle simple messages (body directly in payload)
            if "body" in payload and "data" in payload["body"]:
                if payload.get("mimeType") == "text/plain":
                    plain_body = base64.urlsafe_b64decode(
                        payload["body"]["data"]
                    ).decode()
                elif payload.get("mimeType") == "text/html":
                    html_body = base64.urlsafe_b64decode(
                        payload["body"]["data"]
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
                            part["body"]["data"]
                        ).decode()
                    elif (
                        part.get("mimeType") == "text/html"
                        and "body" in part
                        and "data" in part["body"]
                    ):
                        html_body = base64.urlsafe_b64decode(
                            part["body"]["data"]
                        ).decode()

        return plain_body, html_body

    def enrich_email(self, email: Email) -> bool:
        """
        Enrich an email with message body content and priority score.

        Args:
            email: The email to enrich

        Returns:
            bool: True if enrichment was successful
        """
        try:
            enrichment_task = self.create_enrichment_task(email.id)

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
                    }
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

                logger.info(
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
            logger.error(
                "email_enrichment_failed",
                email_id=email.id,
                gmail_id=email.gmail_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            if "enrichment_task" in locals():
                self.fail_task(enrichment_task, str(e))
            return False
