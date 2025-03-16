# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Contact-related AI agents."""


from database.models import Contact
from pydantic import BaseModel, Field

from .base import SyzygyAgent


class ContactSimilarity(BaseModel):
    """Similarity analysis between two contacts."""

    name_similarity: float = Field(..., description="Similarity score for names (0-1)")
    email_similarity: float = Field(
        ...,
        description="Similarity score for email addresses (0-1)",
    )
    overall_similarity: float = Field(..., description="Overall similarity score (0-1)")
    should_merge: bool = Field(..., description="Whether the contacts should be merged")
    confidence: float = Field(..., description="Confidence in the merge decision (0-1)")
    reason: str = Field(..., description="Explanation for the merge decision")


class ContactMergeAgent(SyzygyAgent):
    """Agent for analyzing and deciding on contact merges."""

    def get_system_prompt(self) -> str:
        return """You are an expert at analyzing contact information and determining if records should be merged.

        When analyzing contacts, consider:
        1. Name variations and common nicknames
        2. Email patterns and domains
        3. Historical interaction patterns
        4. Company/organization affiliations

        Provide clear reasoning for merge decisions and be conservative when confidence is low.
        """

    async def analyze_contacts(
        self,
        contact1: dict,
        contact2: dict,
    ) -> ContactSimilarity:
        """Analyze two contacts and determine if they should be merged.

        Todo:
        ----
        - Add support for contact history analysis
        - Consider interaction patterns
        - Add company/domain rules
        - Support custom merge rules

        """
        result = await self.run(
            f"Analyze these contacts for potential merging:\nContact 1: {contact1}\nContact 2: {contact2}",
            result_type=ContactSimilarity,
        )
        return result.data


class ContactAgent(SyzygyAgent):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def add_contact(self, email, name):
        """Add a new contact."""
        return Contact.objects.create(email=email, name=name)

    async def remove_contact(self, email) -> None:
        """Remove a contact."""
        Contact.objects.filter(email=email).delete()


# TODO: Add more contact-related agents:
# - ContactCategoryAgent for determining contact categories
# - ContactEnrichmentAgent for enriching contact data
# - ContactPriorityAgent for determining contact importance
"""Contact-related AI agents."""


from database.models import Contact
from pydantic import BaseModel, Field

from .base import SyzygyAgent


class ContactSimilarity(BaseModel):
    """Similarity analysis between two contacts."""

    name_similarity: float = Field(..., description="Similarity score for names (0-1)")
    email_similarity: float = Field(
        ...,
        description="Similarity score for email addresses (0-1)",
    )
    overall_similarity: float = Field(..., description="Overall similarity score (0-1)")
    should_merge: bool = Field(..., description="Whether the contacts should be merged")
    confidence: float = Field(..., description="Confidence in the merge decision (0-1)")
    reason: str = Field(..., description="Explanation for the merge decision")


class ContactMergeAgent(SyzygyAgent):
    """Agent for analyzing and deciding on contact merges."""

    def get_system_prompt(self) -> str:
        return """You are an expert at analyzing contact information and determining if records should be merged.

        When analyzing contacts, consider:
        1. Name variations and common nicknames
        2. Email patterns and domains
        3. Historical interaction patterns
        4. Company/organization affiliations

        Provide clear reasoning for merge decisions and be conservative when confidence is low.
        """

    async def analyze_contacts(
        self,
        contact1: dict,
        contact2: dict,
    ) -> ContactSimilarity:
        """Analyze two contacts and determine if they should be merged.

        Todo:
        ----
        - Add support for contact history analysis
        - Consider interaction patterns
        - Add company/domain rules
        - Support custom merge rules

        """
        result = await self.run(
            f"Analyze these contacts for potential merging:\nContact 1: {contact1}\nContact 2: {contact2}",
            result_type=ContactSimilarity,
        )
        return result.data


class ContactAgent(SyzygyAgent):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def add_contact(self, email, name):
        """Add a new contact."""
        return Contact.objects.create(email=email, name=name)

    async def remove_contact(self, email) -> None:
        """Remove a contact."""
        Contact.objects.filter(email=email).delete()


# TODO: Add more contact-related agents:
# - ContactCategoryAgent for determining contact categories
# - ContactEnrichmentAgent for enriching contact data
# - ContactPriorityAgent for determining contact importance
