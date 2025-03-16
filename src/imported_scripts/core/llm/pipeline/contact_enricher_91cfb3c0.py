"""Contact enrichment system for extracting and storing contact information from emails."""

from __future__ import annotations

import re

import structlog
from django.utils import timezone
from python_ulid import ULID

from .models import EnrichmentSource, EnrichmentTask

logger = structlog.get_logger(__name__)

# Core patterns for contact extraction
PATTERNS = {
    "name_email": r"([^<\n]*?)\s*<([^>]+)>",  # Matches "Name <email@domain.com>"
    "company": r"(?i)(?:at|@)\s*([A-Za-z0-9][A-Za-z0-9\s&-]+(?:\s+(?:LLC|Inc|Ltd))?)",
    "linkedin": r"LinkedIn:\s*(linkedin\.com/in/[a-zA-Z0-9_-]+)",
}


def extract_contact_info_from_patterns(email_content: str) -> dict:
    """Extract contact information from email content using predefined patterns.

    Args:
    ----
        email_content: Raw email content to parse.

    Returns:
    -------
        Dict: Containing extracted contact information with confidence scores.

    """
    info: dict = {}
    confidence: dict = {}

    for field, pattern in PATTERNS.items():
        matches = re.findall(pattern, email_content)
        if matches:
            if field == "name_email" and len(matches[0]) == 2:
                info["name"] = matches[0][0].strip()
                info["email"] = matches[0][1].strip()
                confidence["name"] = 0.9
                confidence["email"] = 1.0
            else:
                info[field] = matches[0].strip()
                confidence[field] = 0.9

    return {"data": info, "confidence": confidence}


class ContactEnricher:
    """Extracts and stores contact information from email content."""

    def __init__(self) -> None:
        """Initializes the ContactEnricher with a logger."""
        self.logger = logger.bind(component="ContactEnricher")

    def extract_contact_info(self, email_content: str) -> dict:
        """Extract contact information from email content.

        Args:
        ----
            email_content: Raw email content to parse.

        Returns:
        -------
            Dict: Containing extracted contact information with confidence scores.

        """
        return extract_contact_info_from_patterns(email_content)

    def store_enrichment(
        self,
        contact_id: str,
        data: dict,
        confidence: float,
    ) -> str:
        """Store enrichment data for a contact.

        Args:
        ----
            contact_id: Contact identifier.
            data: Dictionary of enrichment data.
            confidence: Overall confidence score.

        Returns:
        -------
            str: ULID source identifier.

        """
        source_id = str(ULID())

        self.logger.info(
            "storing_enrichment",
            source_id=source_id,
            contact_id=contact_id,
            confidence=confidence,
        )

        try:
            # Mark previous sources as invalid
            EnrichmentSource.objects.filter(
                entity_type="contact",
                entity_id=contact_id,
                valid_to__isnull=True,
            ).update(valid_to=timezone.now())

            # Create new source
            source = EnrichmentSource.objects.create(
                id=source_id,
                source_type="email_content",
                entity_type="contact",
                entity_id=contact_id,
                data=data,
                confidence=confidence,
            )

            return source.id

        except Exception as e:
            self.logger.error(
                "failed_to_store_enrichment",
                source_id=source_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def create_enrichment_task(
        self,
        contact_id: str,
        task_type: str,
        metadata: dict | None = None,
    ) -> str:
        """Create a new enrichment task.

        Args:
        ----
            contact_id: Contact identifier.
            task_type: Type of enrichment task.
            metadata: Optional task metadata.

        Returns:
        -------
            str: Task identifier.

        """
        task_id = str(ULID())

        self.logger.info(
            "creating_enrichment_task",
            task_id=task_id,
            contact_id=contact_id,
            task_type=task_type,
            metadata=metadata,
        )

        try:
            task = EnrichmentTask.objects.create(
                id=task_id,
                entity_type="contact",
                entity_id=contact_id,
                task_type=task_type,
                metadata=metadata or {},
            )
            return task.id

        except Exception as e:
            self.logger.error("failed_to_create_task", error=str(e), exc_info=True)
            raise

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        """Update task status and results.

        Args:
        ----
            task_id: Task identifier.
            status: New status.
            result: Optional task results.
            error: Optional error message.

        """
        self.logger.info(
            "updating_task_status",
            task_id=task_id,
            status=status,
            result=result,
            error=error,
        )

        try:
            task = EnrichmentTask.objects.get(id=task_id)
            task.status = status
            task.attempts += 1
            task.last_attempt = timezone.now()

            if result is not None:
                task.result = result
            if error is not None:
                task.error_message = error

            task.save()

        except EnrichmentTask.DoesNotExist:
            self.logger.exception("task_not_found", task_id=task_id)
            raise
        except Exception as e:
            self.logger.error(
                "failed_to_update_task",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def enrich_contact(self, contact_id: str, email_content: str) -> dict:
        """Enrich contact information from email content.

        Args:
        ----
            contact_id: Contact identifier to enrich.
            email_content: Email content to extract information from.

        Returns:
        -------
            Dict: Containing enrichment results.

        """
        # Create enrichment task
        task_id = self.create_enrichment_task(
            contact_id=contact_id,
            task_type="contact_info",
            metadata={"source": "email_content"},
        )

        try:
            # Extract contact information
            enrichment_result = self.extract_contact_info(email_content)

            if enrichment_result["data"]:
                confidence = sum(enrichment_result["confidence"].values()) / len(
                    enrichment_result["confidence"],
                )
                source_id = self.store_enrichment(
                    contact_id=contact_id,
                    data=enrichment_result["data"],
                    confidence=confidence,
                )

                # Update task as completed
                self.update_task_status(
                    task_id=task_id,
                    status="completed",
                    result={"source_id": source_id, **enrichment_result},
                )

                return {
                    "task_id": task_id,
                    "source_id": source_id,
                    "status": "success",
                    **enrichment_result,
                }

            # Update task as completed but no data found
            self.update_task_status(
                task_id=task_id,
                status="completed",
                result={"message": "No contact information found"},
            )

            return {
                "task_id": task_id,
                "status": "success",
                "message": "No contact information found",
            }

        except Exception as e:
            self.logger.error(
                "enrichment_failed",
                contact_id=contact_id,
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )

            # Update task as failed
            self.update_task_status(task_id=task_id, status="failed", error=str(e))

            return {"task_id": task_id, "status": "error", "error": str(e)}
