# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:39:31 2025

"""Contact enrichment service for processing and updating contact information."""
from __future__ import annotations

from email.utils import parseaddr

import structlog
from database.models import AutomatedOperation, Contact, EmailContactAssociation
from django.db import transaction

logger = structlog.get_logger(__name__)


class ContactEnrichmentService(AutomatedOperation):
    """Service for enriching contact information from email data."""

    def __init__(self) -> None:
        super().__init__(entity_type="contact", task_type="contact_info")

    def process_contact(
        self,
        email_address: str,
        name: str | None = None,
    ) -> Contact:
        """Process a contact, creating or updating their information.

        Args:
        ----
            email_address: The contact's email address
            name: Optional display name from email header

        Returns:
        -------
            Contact: The created or updated contact

        """
        try:
            with transaction.atomic():
                # Parse name from email if provided in format "Name <email@domain.com>"
                if name:
                    display_name, _ = parseaddr(f"{name} <{email_address}>")
                    if display_name:
                        # Split into first/last name
                        name_parts = display_name.split(maxsplit=1)
                        first_name = name_parts[0]
                        last_name = name_parts[1] if len(name_parts) > 1 else ""
                    else:
                        first_name = ""
                        last_name = ""
                else:
                    first_name = ""
                    last_name = ""

                # Get or create contact
                contact, created = Contact.objects.get_or_create(
                    email=email_address,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                    },
                )

                if created:
                    logger.info(
                        "contact_created",
                        email=email_address,
                        first_name=first_name,
                        last_name=last_name,
                    )

                return contact

        except Exception as e:
            logger.exception(
                "contact_processing_failed",
                email=email_address,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def analyze_contact_interactions(self, contact: Contact) -> dict:
        """Analyze a contact's email interactions to gather insights.

        Args:
        ----
            contact: The contact to analyze

        Returns:
        -------
            Dict containing interaction statistics

        """
        try:
            # Get all email associations for this contact
            associations = EmailContactAssociation.objects.filter(contact=contact)

            # Count interactions by type
            interaction_counts = {
                "from_count": associations.filter(association_type="from").count(),
                "to_count": associations.filter(association_type="to").count(),
                "cc_count": associations.filter(association_type="cc").count(),
                "bcc_count": associations.filter(association_type="bcc").count(),
            }

            # Get first and last interaction dates
            first_interaction = associations.order_by("email__received_at").first()
            last_interaction = associations.order_by("-email__received_at").first()

            return {
                **interaction_counts,
                "total_interactions": sum(interaction_counts.values()),
                "first_interaction_date": (
                    first_interaction.email.received_at if first_interaction else None
                ),
                "last_interaction_date": (
                    last_interaction.email.received_at if last_interaction else None
                ),
            }

        except Exception as e:
            logger.exception(
                "interaction_analysis_failed",
                contact_id=contact.id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def enrich_contact(self, contact: Contact) -> bool:
        """Enrich a contact's information using available data.

        Args:
        ----
            contact: The contact to enrich

        Returns:
        -------
            bool: True if enrichment was successful

        """
        try:
            enrichment_task = self.create_enrichment_task(contact.id)

            with transaction.atomic():
                # Get interaction data
                interaction_data = self.analyze_contact_interactions(contact)

                # Update contact with interaction data
                contact.interaction_count = interaction_data["total_interactions"]
                if interaction_data["last_interaction_date"]:
                    contact.last_interaction = interaction_data["last_interaction_date"]

                # Save updates
                contact.save()

                self.complete_task(
                    enrichment_task,
                    result={
                        "interaction_count": contact.interaction_count,
                        "last_interaction": (
                            contact.last_interaction.isoformat()
                            if contact.last_interaction
                            else None
                        ),
                        "interaction_details": interaction_data,
                    },
                )

                logger.info(
                    "contact_enriched",
                    contact_id=contact.id,
                    email=contact.email,
                    interaction_count=contact.interaction_count,
                    last_interaction=contact.last_interaction,
                )

                return True

        except Exception as e:
            logger.exception(
                "contact_enrichment_failed",
                contact_id=contact.id,
                error=str(e),
                error_type=type(e).__name__,
            )
            if "enrichment_task" in locals():
                self.fail_task(enrichment_task, str(e))
            return False

    def process_email_participants(self, email_data: dict) -> list[Contact]:
        """Process all participants (from, to, cc, bcc) in an email.

        Args:
        ----
            email_data: Dictionary containing email header information

        Returns:
        -------
            List[Contact]: List of processed contacts

        """
        processed_contacts = []

        try:
            # Process sender
            from_header = email_data.get("from", "")
            if from_header:
                display_name, email_address = parseaddr(from_header)
                if email_address:
                    contact = self.process_contact(email_address, display_name)
                    processed_contacts.append(contact)

            # Process recipients
            for field in ["to", "cc", "bcc"]:
                addresses = email_data.get(field, "").split(",")
                for addr in addresses:
                    if addr.strip():
                        display_name, email_address = parseaddr(addr)
                        if email_address:
                            contact = self.process_contact(email_address, display_name)
                            processed_contacts.append(contact)

            return processed_contacts

        except Exception as e:
            logger.exception(
                "participant_processing_failed",
                email_data=email_data,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
