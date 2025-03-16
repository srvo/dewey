"""Email triage and prioritization workflow."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sentry_sdk
import structlog
from email_processing.prioritization.priority_rules import EmailPriorities
from pydantic import BaseModel, Field

from ..base import SyzygyAgent

if TYPE_CHECKING:
    from ..agents.adversarial import AdversarialAgent
    from ..agents.client_advocate import ClientAdvocate
    from ..agents.ghostwriter import SloanGhostwriter
    from ..agents.rag import RAGAgent

logger = structlog.get_logger(__name__)


class EmailMetadata(BaseModel):
    """Email metadata for triage."""

    message_id: str
    from_address: str
    to_addresses: list[str]
    cc_addresses: list[str]
    subject: str
    date: datetime
    thread_id: str | None
    labels: list[str]
    has_attachments: bool


class EmailContent(BaseModel):
    """Email content for analysis."""

    text_content: str
    html_content: str | None
    quoted_text: str | None
    signature: str | None
    attachments: list[dict[str, Any]]


class EmailClassification(BaseModel):
    """Classification of email type and priority."""

    category: str  # marketing, personal, client, etc.
    priority: int = Field(ge=0, le=4)
    confidence: float = Field(ge=0, le=1)
    requires_response: bool
    response_deadline: datetime | None
    action_items: list[str]
    context_refs: list[str]


class ResponseDraft(BaseModel):
    """Draft response to email."""

    content: str
    tone: str
    key_points: list[str]
    needs_review: bool
    confidence: float = Field(ge=0, le=1)
    alternative_versions: list[str] | None


class BatchProcessingResult(BaseModel):
    """Results from batch email processing."""

    total_processed: int
    successful: int
    failed: int
    skipped_llm: int
    processing_time: float
    errors: list[dict[str, Any]]


class EmailTriageWorkflow:
    """Orchestrator for email triage and response workflow.

    Features:
    - Deterministic rules first
    - Multi-stage email analysis
    - Priority determination
    - Response drafting
    - Client relationship integration
    - Knowledge base lookup
    - Batch processing support
    """

    def __init__(
        self,
        rag_agent: RAGAgent,
        ghostwriter: SloanGhostwriter,
        client_advocate: ClientAdvocate,
        adversarial: AdversarialAgent,
    ) -> None:
        """Initialize the workflow."""
        self.rag_agent = rag_agent
        self.ghostwriter = ghostwriter
        self.client_advocate = client_advocate
        self.adversarial = adversarial

        # Initialize priority rules
        self.priority_rules = EmailPriorities()

        # Initialize agents for different complexity levels
        self.triage_agent = SyzygyAgent(
            task_type="email_triage",
            model="mistral-7b-instruct",
        )
        self.analysis_agent = SyzygyAgent(
            task_type="email_analysis",
            model="mixtral-8x7b",
        )

    async def _apply_priority_rules(
        self,
        metadata: EmailMetadata,
        content: EmailContent,
    ) -> dict[str, Any]:
        """Apply deterministic priority rules.

        Args:
            metadata: Email metadata
            content: Email content

        Returns:
            Priority determination

        """
        try:
            with sentry_sdk.start_span(op="priority_rules"):
                return self.priority_rules.determine_priority(
                    metadata=metadata.dict(),
                    content=content.dict() if content else None,
                )
        except Exception as e:
            logger.exception("Error applying priority rules", error=str(e))
            sentry_sdk.capture_exception(e)
            return {
                "priority": 2,  # Default to medium priority
                "category": "unknown",
                "requires_response": False,
                "confidence": 0.0,
                "rule_matched": None,
                "needs_llm": True,
            }

    async def _initial_triage(
        self,
        metadata: EmailMetadata,
        content: EmailContent,
    ) -> dict[str, Any]:
        """Perform initial quick triage using basic model."""
        with sentry_sdk.start_span(op="initial_triage"):
            return await self.triage_agent.run(
                messages=[
                    {
                        "role": "system",
                        "content": f"""Quickly classify this email:

From: {metadata.from_address}
Subject: {metadata.subject}
Date: {metadata.date}
Labels: {metadata.labels}

Content:
{content.text_content[:500]}  # Limit for quick analysis

Classify:
1. Likely category (marketing, personal, client, etc.)
2. Initial priority (0-4)
3. Response needed (yes/no)
4. Time sensitivity
5. Key entities mentioned""",
                    },
                ],
                model="mistral-7b-instruct",
                metadata={"message_id": metadata.message_id},
            )

    async def _detailed_analysis(
        self,
        metadata: EmailMetadata,
        content: EmailContent,
        initial_triage: dict[str, Any],
    ) -> EmailClassification:
        """Perform detailed analysis using mid-tier model."""
        with sentry_sdk.start_span(op="detailed_analysis"):
            # Get client context if relevant
            client_context = None
            if initial_triage["category"] == "client":
                client_profile = await self.client_advocate.analyze_client(
                    {"email": metadata.from_address},
                )
                client_context = client_profile.dict()

            # Look up relevant knowledge
            context_refs = []
            if initial_triage["priority"] >= 2:
                search_results = await self.rag_agent.search(
                    content.text_content,
                    limit=3,
                )
                context_refs = [r.id for r in search_results]

            result = await self.analysis_agent.run(
                messages=[
                    {
                        "role": "system",
                        "content": f"""Analyze this email in detail:

Metadata:
{metadata.dict()}

Content:
{content.text_content}

Initial Triage:
{initial_triage}

Client Context:
{client_context or "None"}

Knowledge Context:
{context_refs}

Provide:
1. Confirmed category
2. Refined priority (0-4)
3. Response requirements
4. Action items
5. Relevant context
6. Time sensitivity""",
                    },
                ],
                model="mixtral-8x7b",
                metadata={
                    "message_id": metadata.message_id,
                    "initial_priority": initial_triage["priority"],
                },
            )

            return EmailClassification(**result)

    async def _draft_response(
        self,
        metadata: EmailMetadata,
        content: EmailContent,
        classification: EmailClassification,
    ) -> ResponseDraft | None:
        """Draft response if needed using appropriate model."""
        if not classification.requires_response:
            return None

        with sentry_sdk.start_span(op="draft_response"):
            # Get relevant context
            context_data = await self.rag_agent.search(
                f"email thread:{metadata.thread_id} {content.text_content}",
                limit=5,
            )

            # Generate draft
            draft = await self.ghostwriter.generate_draft(
                brief={
                    "topic": f"Response to: {metadata.subject}",
                    "type": "email",
                    "key_points": classification.action_items,
                    "tone": (
                        "professional"
                        if classification.category == "client"
                        else "friendly"
                    ),
                    "target_audience": metadata.from_address,
                    "context": str(context_data),
                },
            )

            # Get critical feedback
            critique = await self.adversarial.analyze_risks(
                draft.content,
                context=f"Email response to {metadata.subject}",
            )

            # Refine if needed
            if critique.critical_issues:
                draft = await self.ghostwriter.refine_content(
                    draft,
                    feedback=str(critique.dict()),
                )

            return ResponseDraft(
                content=draft.content,
                tone=draft.tone_analysis["overall_tone"],
                key_points=draft.key_phrases,
                needs_review=classification.priority >= 3,
                confidence=draft.tone_analysis["confidence"],
                alternative_versions=(
                    await self.ghostwriter.generate_variations(draft.content, count=2)
                    if classification.priority >= 3
                    else None
                ),
            )

    async def process_email(
        self,
        metadata: EmailMetadata,
        content: EmailContent,
    ) -> dict[str, Any]:
        """Process single email through workflow."""
        try:
            with sentry_sdk.start_transaction(
                op="process_email",
                name=metadata.message_id,
            ):
                # Stage 1: Apply deterministic rules
                rule_result = await self._apply_priority_rules(metadata, content)

                # Exit early if rules give high confidence result
                if self.priority_rules.should_skip_llm(rule_result):
                    return {
                        "classification": EmailClassification(
                            category=rule_result["category"],
                            priority=rule_result["priority"],
                            confidence=rule_result["confidence"],
                            requires_response=rule_result["requires_response"],
                            action_items=[],
                            context_refs=[],
                        ),
                        "response_draft": None,
                        "processing_level": "rules_only",
                        "rule_matched": rule_result["rule_matched"],
                    }

                # Stage 2: Initial LLM triage
                initial_triage = await self._initial_triage(metadata, content)

                # Stage 3: Detailed analysis if needed
                classification = await self._detailed_analysis(
                    metadata,
                    content,
                    initial_triage,
                )

                # Stage 4: Draft response if needed
                response_draft = (
                    await self._draft_response(metadata, content, classification)
                    if classification.requires_response
                    else None
                )

                return {
                    "classification": classification,
                    "response_draft": response_draft,
                    "processing_level": "full",
                    "rule_matched": rule_result["rule_matched"],
                }

        except Exception as e:
            logger.exception(
                "Error processing email",
                message_id=metadata.message_id,
                error=str(e),
            )
            sentry_sdk.capture_exception(e)
            raise

    async def process_batch(
        self,
        emails: list[dict[str, Any]],
        batch_size: int = 10,
        max_concurrent: int = 5,
    ) -> BatchProcessingResult:
        """Process batch of emails.

        Args:
            emails: List of email data dictionaries
            batch_size: Size of batches to process
            max_concurrent: Maximum concurrent tasks

        Returns:
            Batch processing results

        """
        start_time = datetime.now()
        results = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped_llm": 0,
            "errors": [],
        }

        # Process in batches
        for i in range(0, len(emails), batch_size):
            batch = emails[i : i + batch_size]
            tasks = []

            # Create tasks for batch
            for email in batch:
                metadata = EmailMetadata(**email["metadata"])
                content = EmailContent(**email["content"])

                task = asyncio.create_task(self.process_email(metadata, content))
                tasks.append((email["metadata"]["message_id"], task))

            # Process batch with concurrency limit
            for chunk in [
                tasks[i : i + max_concurrent]
                for i in range(0, len(tasks), max_concurrent)
            ]:
                for message_id, task in chunk:
                    try:
                        result = await task
                        results["total_processed"] += 1
                        results["successful"] += 1
                        if result["processing_level"] == "rules_only":
                            results["skipped_llm"] += 1

                    except Exception as e:
                        results["total_processed"] += 1
                        results["failed"] += 1
                        results["errors"].append(
                            {"message_id": message_id, "error": str(e)},
                        )
                        logger.exception(
                            "Batch processing error",
                            message_id=message_id,
                            error=str(e),
                        )
                        sentry_sdk.capture_exception(e)

        return BatchProcessingResult(
            **results,
            processing_time=(datetime.now() - start_time).total_seconds(),
        )
