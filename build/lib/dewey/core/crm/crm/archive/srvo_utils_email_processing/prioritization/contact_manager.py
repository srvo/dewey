"""Integrated contact management system for creating and enriching contacts from emails."""

from typing import Dict, List, Optional
from python_ulid import ULID
import structlog
from django.db import transaction
from django.utils import timezone
from pydantic import BaseModel, Field
from pydantic.ai import ai_fn

from .models import Contact, EnrichmentTask, EnrichmentSource
from .contact_enrichment import ContactEnricher, PATTERNS
from .contact_merger import ContactMerger

logger = structlog.get_logger(__name__)


class CategoryPrediction(BaseModel):
    """Category prediction with confidence score."""

    category: str = Field(..., description="Predicted category name")
    confidence: float = Field(
        ..., description="Confidence score for the prediction (0-1)"
    )
    reasoning: str = Field(..., description="Explanation for the category prediction")


@ai_fn(
    description="""
Determine contact categories with confidence scores.

Instructions:
1. Analyze contact data including:
   - Email domain
   - Company information
   - Job title
   - Interaction patterns
2. Return multiple possible categories with confidence scores
3. Consider categories:
   - business: Business/corporate contacts
   - academic: Educational/research contacts
   - consultant: Independent consultants/advisors
   - individual: Personal/individual contacts
   - newsletter: Newsletter/automated senders
   - support: Customer support/service contacts
"""
)
def determine_contact_category(contact_data: Dict) -> List[CategoryPrediction]:
    pass  # PydanticAI will implement this


class ContactManager:
    """Manages contact lifecycle including creation, enrichment, and categorization."""

    def __init__(self):
        self.logger = logger.bind(component="ContactManager")
        self.enricher = ContactEnricher()
        self.merger = ContactMerger()

    def process_new_emails(self, emails: List[Dict]) -> Dict:
        """Process new emails to create and enrich contacts.

        Args:
            emails: List of email dictionaries containing at least:
                   - from_email: Sender's email
                   - from_name: Sender's name
                   - content: Email content
                   - subject: Email subject

        Returns:
            Dict containing processing results
        """
        results = {
            "processed": 0,
            "created": 0,
            "enriched": 0,
            "merge_candidates": 0,
            "errors": [],
        }

        for email in emails:
            try:
                with transaction.atomic():
                    # Create or get contact
                    contact_id, created = self.create_or_get_contact(
                        email=email["from_email"], name=email["from_name"]
                    )
                    results["processed"] += 1
                    if created:
                        results["created"] += 1

                    # Enrich contact with email content
                    enrichment_result = self.enricher.enrich_contact(
                        contact_id=contact_id,
                        email_content=f"{email['subject']}\n{email['content']}",
                    )

                    if (
                        enrichment_result["status"] == "success"
                        and "data" in enrichment_result
                    ):
                        results["enriched"] += 1

                        # Update contact categorization
                        self.update_contact_category(
                            contact_id=contact_id,
                            enrichment_data=enrichment_result["data"],
                        )

                        # Check for merge candidates
                        merge_candidates = self.merger.find_merge_candidates(contact_id)
                        if merge_candidates:
                            results["merge_candidates"] += len(merge_candidates)
                            self._handle_merge_candidates(contact_id, merge_candidates)

            except Exception as e:
                self.logger.error(
                    "email_processing_failed",
                    email=email["from_email"],
                    error=str(e),
                    exc_info=True,
                )
                results["errors"].append(
                    {"email": email["from_email"], "error": str(e)}
                )

        return results

    def create_or_get_contact(
        self, email: str, name: Optional[str] = None
    ) -> tuple[str, bool]:
        """Create a new contact if it doesn't exist.

        Args:
            email: Contact's email address
            name: Optional contact name

        Returns:
            Tuple[str, bool]: (Contact ID, whether created)
        """
        try:
            # Try to get existing contact
            contact = Contact.objects.filter(email=email).first()
            if contact:
                return contact.id, False

            # Create new contact
            contact_id = str(ULID())
            contact = Contact.objects.create(
                id=contact_id, email=email, name=name, enrichment_status="pending"
            )

            self.logger.info("contact_created", contact_id=contact_id, email=email)
            return contact_id, True

        except Exception as e:
            self.logger.error(
                "contact_creation_failed", email=email, error=str(e), exc_info=True
            )
            raise

    def update_contact_category(self, contact_id: str, enrichment_data: Dict):
        """Update contact categorization based on enrichment data.

        Args:
            contact_id: Contact identifier
            enrichment_data: Dictionary of enriched contact data
        """
        try:
            # Get AI-powered category analysis
            categories = determine_contact_category(
                {
                    "enrichment": enrichment_data,
                    "history": self.get_contact_history(contact_id),
                }
            )

            # Get highest confidence category
            primary_category = max(categories.items(), key=lambda x: x[1])[0]

            Contact.objects.filter(id=contact_id).update(
                category=primary_category,
                enrichment_status="completed",
                metadata={
                    "categories": categories,
                    "last_categorized": timezone.now().isoformat(),
                },
            )

            self.logger.info(
                "contact_categorized",
                contact_id=contact_id,
                category=primary_category,
                confidence=categories[primary_category],
            )

        except Exception as e:
            self.logger.error(
                "categorization_failed",
                contact_id=contact_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def _handle_merge_candidates(self, contact_id: str, candidates: List[Dict]):
        """Handle potential contact merge candidates.

        Args:
            contact_id: Primary contact ID
            candidates: List of merge candidates with similarity scores
        """
        try:
            for candidate in candidates:
                if (
                    candidate["decision"].should_merge
                    and candidate["decision"].confidence >= 0.9
                ):
                    # Auto-merge high-confidence matches
                    self.merger.merge_contacts(
                        primary_id=contact_id, secondary_id=candidate["contact"]["id"]
                    )
                elif candidate["decision"].needs_review:
                    # Create review task for manual verification
                    EnrichmentTask.objects.create(
                        id=str(ULID()),
                        entity_type="contact",
                        entity_id=contact_id,
                        task_type="merge_review",
                        status="pending",
                        metadata={
                            "candidate_id": candidate["contact"]["id"],
                            "similarity": candidate["similarity"].dict(),
                            "decision": candidate["decision"].dict(),
                        },
                    )

        except Exception as e:
            self.logger.error(
                "merge_candidate_handling_failed",
                contact_id=contact_id,
                error=str(e),
                exc_info=True,
            )
            # Log error but don't raise to continue processing other candidates

    def get_contact_history(self, contact_id: str) -> Dict:
        """Get contact's enrichment history.

        Args:
            contact_id: Contact identifier

        Returns:
            Dict containing contact's enrichment history
        """
        try:
            # Get contact details
            contact = Contact.objects.get(id=contact_id)

            # Get all enrichment sources for contact
            sources = EnrichmentSource.objects.filter(
                entity_type="contact", entity_id=contact_id
            ).order_by("-valid_from")

            # Get all enrichment tasks for contact
            tasks = EnrichmentTask.objects.filter(
                entity_type="contact", entity_id=contact_id
            ).order_by("-created_at")

            return {
                "contact": {
                    "id": contact.id,
                    "email": contact.email,
                    "name": contact.name,
                    "category": contact.category,
                    "enrichment_status": contact.enrichment_status,
                    "created_at": contact.created_at,
                    "metadata": contact.metadata,
                },
                "sources": [
                    {
                        "id": source.id,
                        "data": source.data,
                        "confidence": source.confidence,
                        "valid_from": source.valid_from,
                        "valid_to": source.valid_to,
                    }
                    for source in sources
                ],
                "tasks": [
                    {
                        "id": task.id,
                        "type": task.task_type,
                        "status": task.status,
                        "result": task.result,
                        "created_at": task.created_at,
                    }
                    for task in tasks
                ],
            }

        except Contact.DoesNotExist:
            self.logger.error("contact_not_found", contact_id=contact_id)
            raise
        except Exception as e:
            self.logger.error(
                "history_retrieval_failed",
                contact_id=contact_id,
                error=str(e),
                exc_info=True,
            )
            raise
