```python
"""Contact merging system powered by PydanticAI."""

from typing import Dict, List, Optional

import structlog
from django.db import transaction
from django.utils import timezone
from python_ulid import ULID

from syzygy.ai.contact_agents import ContactMergeAgent
from .models import Contact, EnrichmentSource, EnrichmentTask

logger = structlog.get_logger(__name__)


class ContactMerger:
    """Handles intelligent contact merging with AI-powered decision making."""

    def __init__(self) -> None:
        """Initializes the ContactMerger with a logger and AI agent."""
        self.logger = logger.bind(component="ContactMerger")
        self.agent = ContactMergeAgent()

    async def _analyze_contact_similarity(
        self, target_contact: Contact, candidate: Contact
    ) -> Dict:
        """Analyzes the similarity between two contacts using the AI agent.

        Args:
            target_contact: The primary contact.
            candidate: The contact to compare against.

        Returns:
            A dictionary containing the similarity analysis results.
        """
        target_enrichment = EnrichmentSource.objects.filter(
            entity_type="contact", entity_id=target_contact.id, valid_to__isnull=True
        ).first()

        candidate_enrichment = EnrichmentSource.objects.filter(
            entity_type="contact", entity_id=candidate.id, valid_to__isnull=True
        ).first()

        contact1_data = {
            "id": target_contact.id,
            "email": target_contact.email,
            "name": target_contact.name,
            "enrichment": target_enrichment.data if target_enrichment else {},
        }

        contact2_data = {
            "id": candidate.id,
            "email": candidate.email,
            "name": candidate.name,
            "enrichment": candidate_enrichment.data if candidate_enrichment else {},
        }

        similarity = await self.agent.analyze_contacts(contact1_data, contact2_data)

        return {
            "contact": contact2_data,
            "similarity": similarity.dict(),
            "needs_review": similarity.confidence < 0.9,
        }

    async def find_merge_candidates(self, contact_id: str) -> List[Dict]:
        """Find potential merge candidates for a contact.

        Args:
            contact_id: Contact identifier.

        Returns:
            List of potential merge candidates with similarity scores.
        """
        try:
            target_contact = Contact.objects.get(id=contact_id)

            email_base = target_contact.email.split("@")[0]
            similar_emails = Contact.objects.exclude(id=contact_id).filter(
                email__icontains=email_base
            )

            candidates = []
            for candidate in similar_emails:
                similarity_data = await self._analyze_contact_similarity(
                    target_contact, candidate
                )
                if (
                    similarity_data["similarity"]["should_merge"]
                    or similarity_data["similarity"]["confidence"] < 0.9
                ):
                    candidates.append(similarity_data)

            return candidates

        except Contact.DoesNotExist:
            self.logger.error("contact_not_found", contact_id=contact_id)
            raise
        except Exception as e:
            self.logger.error(
                "merge_candidate_search_failed",
                contact_id=contact_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def process_merge_candidates(self, contact_id: str) -> Dict:
        """Process merge candidates for a contact.

        Args:
            contact_id: Contact identifier.

        Returns:
            Dict containing processing results.
        """
        try:
            candidates = await self.find_merge_candidates(contact_id)

            results = {
                "processed": len(candidates),
                "auto_merged": 0,
                "needs_review": 0,
                "errors": [],
            }

            for candidate in candidates:
                try:
                    if not candidate["needs_review"]:
                        await self.merge_contacts(
                            primary_id=contact_id,
                            secondary_id=candidate["contact"]["id"],
                        )
                        results["auto_merged"] += 1
                    else:
                        EnrichmentTask.objects.create(
                            id=str(ULID()),
                            entity_type="contact",
                            entity_id=contact_id,
                            task_type="merge_review",
                            status="pending",
                            metadata={
                                "candidate_id": candidate["contact"]["id"],
                                "similarity": candidate["similarity"],
                            },
                        )
                        results["needs_review"] += 1

                except Exception as e:
                    self.logger.error(
                        "candidate_processing_failed",
                        contact_id=contact_id,
                        candidate_id=candidate["contact"]["id"],
                        error=str(e),
                        exc_info=True,
                    )
                    results["errors"].append(
                        {"contact_id": candidate["contact"]["id"], "error": str(e)}
                    )

            return results

        except Exception as e:
            self.logger.error(
                "merge_processing_failed",
                contact_id=contact_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def merge_contacts(self, primary_id: str, secondary_id: str) -> None:
        """Merge two contacts, keeping the primary and archiving the secondary.

        Args:
            primary_id: ID of the contact to keep.
            secondary_id: ID of the contact to merge into primary.
        """
        try:
            with transaction.atomic():
                primary = Contact.objects.get(id=primary_id)
                secondary = Contact.objects.get(id=secondary_id)

                EnrichmentSource.objects.filter(
                    entity_type="contact",
                    entity_id=secondary_id,
                    valid_to__isnull=True,
                ).update(valid_to=timezone.now())

                EnrichmentSource.objects.create(
                    id=str(ULID()),
                    entity_type="contact",
                    entity_id=primary_id,
                    source_type="merge",
                    data={
                        "merged_from": secondary.id,
                        "merged_at": timezone.now().isoformat(),
                        "original_data": {
                            "email": secondary.email,
                            "name": secondary.name,
                            "category": secondary.category,
                            "metadata": secondary.metadata,
                        },
                    },
                    confidence=1.0,
                    valid_from=timezone.now(),
                )

                secondary.status = "merged"
                secondary.metadata = {
                    **(secondary.metadata or {}),
                    "merged_into": primary_id,
                    "merged_at": timezone.now().isoformat(),
                }
                secondary.save()

                self.logger.info(
                    "contacts_merged", primary_id=primary_id, secondary_id=secondary_id
                )

        except Contact.DoesNotExist:
            self.logger.error(
                "merge_contact_not_found",
                primary_id=primary_id,
                secondary_id=secondary_id,
            )
            raise
        except Exception as e:
            self.logger.error(
                "merge_failed",
                primary_id=primary_id,
                secondary_id=secondary_id,
                error=str(e),
                exc_info=True,
            )
            raise
```
