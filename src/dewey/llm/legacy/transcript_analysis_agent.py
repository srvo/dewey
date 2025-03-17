
# Refactored from: transcript_analysis_agent
# Date: 2025-03-16T16:19:10.583560
# Refactor Version: 1.0
"""Agent for analyzing meeting transcripts to extract action items and content.

This module provides functionality to:
- Extract actionable items from meeting transcripts
- Identify potential content opportunities
- Link analysis results to client records
- Create follow-up activities in the system

The analysis uses the Phi-2 language model for precise language understanding
and preservation of original phrasing while extracting key information.

Key Features:
- Action item extraction with context preservation
- Content opportunity identification
- Automatic activity creation
- Client record linking
- Confidence scoring for extracted items
- Transcript location tracking
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field

from ...models import Activity, Client
from ..base import SyzygyAgent

if TYPE_CHECKING:
    from datetime import datetime

logger = structlog.get_logger(__name__)


class ActionItem(BaseModel):
    """Represents an action item extracted from a meeting transcript.

    Attributes
    ----------
        description (str): The action to be taken, using original phrasing when possible
        priority (int): Priority level from 0 (low) to 4 (critical)
        due_date (Optional[datetime]): Deadline if mentioned in transcript
        assigned_to (Optional[str]): Person responsible if identified
        context (str): Surrounding conversation context for the action
        confidence (float): Model's confidence in extraction (0.0 to 1.0)
        transcript_location (Dict[str, Any]): Location in transcript including:
            - timestamp: When it was mentioned
            - speaker: Who mentioned it
            - section: Which part of meeting it occurred in

    """

    description: str
    priority: int = Field(ge=0, le=4)
    due_date: datetime | None
    assigned_to: str | None
    context: str
    confidence: float = Field(ge=0, le=1)
    transcript_location: dict[str, Any]  # timestamp, speaker, etc.


class ContentOpportunity(BaseModel):
    """Represents a potential content opportunity identified in a transcript.

    Attributes
    ----------
        topic (str): Main subject or theme of the opportunity
        source_quote (str): Exact quote from transcript that inspired the idea
        suggested_title (str): Proposed title for the content piece
        key_points (List[str]): Main points to cover in the content
        content_type (str): Type of content suggested (blog, newsletter, etc.)
        audience (str): Target audience for the content
        confidence (float): Model's confidence in opportunity relevance (0.0 to 1.0)
        transcript_location (Dict[str, Any]): Location in transcript including:
            - timestamp: When it was mentioned
            - speaker: Who mentioned it
            - section: Which part of meeting it occurred in

    """

    topic: str
    source_quote: str
    suggested_title: str
    key_points: list[str]
    content_type: str  # blog, newsletter, knowledge_base, etc.
    audience: str
    confidence: float = Field(ge=0, le=1)
    transcript_location: dict[str, Any]


class TranscriptAnalysisAgent(SyzygyAgent):
    """Agent for analyzing meeting transcripts to extract actionable insights.

    This agent uses the Phi-2 language model to:
    - Extract action items with surrounding context
    - Identify potential content opportunities
    - Preserve original language and phrasing
    - Link analysis results to client records
    - Create follow-up activities in the system

    The analysis process includes:
    1. Transcript parsing and segmentation
    2. Action item extraction with context
    3. Content opportunity identification
    4. Confidence scoring for extracted items
    5. Client record linking (if available)
    6. Activity creation for action items

    Example Usage:
        agent = TranscriptAnalysisAgent()
        analysis = await agent.analyze_transcript(
            transcript="Meeting discussion...",
            client=client_record,
            meeting_date=datetime.now()
        )
    """

    def __init__(self) -> None:
        """Initialize the transcript analysis agent.

        Sets up the agent with:
        - Phi-2 language model for precise analysis
        - Task type configuration
        - Model parameters optimized for transcript analysis

        The Phi-2 model is chosen for its ability to:
        - Preserve original phrasing while extracting key information
        - Understand context and nuance in conversations
        - Handle complex sentence structures
        - Maintain high accuracy with relatively low computational cost
        """
        super().__init__(
            task_type="transcript_analysis",
            model="microsoft/phi-2",  # Using Phi-2 for precise language preservation
        )

    async def analyze_transcript(
        self,
        transcript: str,
        client: Client | None = None,
        meeting_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Analyze a meeting transcript to extract actionable insights.

        This is the main entry point for transcript analysis. It processes the
        transcript to identify action items and content opportunities, optionally
        linking them to a client record and creating follow-up activities.

        Args:
        ----
            transcript (str): The full text of the meeting transcript
            client (Optional[Client]): Associated client record if available
            meeting_date (Optional[datetime]): Date of the meeting for context

        Returns:
        -------
            Dict[str, Any]: Analysis results containing:
                - action_items: List of extracted action items
                - content_opportunities: List of identified content ideas
                - analysis_metadata: Metadata about the analysis process

        The analysis process includes:
        1. Transcript parsing and segmentation
        2. Action item extraction with context
        3. Content opportunity identification
        4. Confidence scoring for extracted items
        5. Client record linking (if available)
        6. Activity creation for action items

        """
        # Extract action items
        action_items = await self._extract_action_items(
            transcript,
            client,
            meeting_date,
        )

        # Create activities for action items
        if client:
            await self._create_activities(action_items, client)

        # Identify content opportunities
        content_opps = await self._identify_content(transcript)

        return {
            "action_items": [item.dict() for item in action_items],
            "content_opportunities": [opp.dict() for opp in content_opps],
            "analysis_metadata": {
                "client_id": client.id if client else None,
                "meeting_date": meeting_date,
                "transcript_length": len(transcript),
                "model_used": self.model,
            },
        }

    async def _extract_action_items(
        self,
        transcript: str,
        client: Client | None = None,
        meeting_date: datetime | None = None,
    ) -> list[ActionItem]:
        """Extract action items from transcript.

        Uses Phi-2 to identify commitments, follow-ups, and tasks while
        preserving original language where possible.
        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": """Extract action items from this meeting transcript.
                For each action item:
                1. Use exact quotes or minimal paraphrasing
                2. Identify who it's assigned to
                3. Note any mentioned deadlines
                4. Assess priority based on language and context
                5. Include surrounding context
                6. Note location in transcript (timestamp/speaker)

                Format as a list of JSON objects.""",
                },
                {
                    "role": "user",
                    "content": f"Meeting date: {meeting_date}\nTranscript:\n{transcript}",
                },
            ],
            metadata={
                "client_id": client.id if client else None,
                "meeting_date": meeting_date,
            },
        )

        return [ActionItem(**item) for item in result]

    async def _identify_content(self, transcript: str) -> list[ContentOpportunity]:
        """Identify content opportunities in transcript.

        Looks for:
        - Questions answered in detail
        - Novel explanations or analogies
        - Interesting insights or perspectives
        - Common client concerns addressed
        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": """Identify content opportunities in this transcript.
                Look for:
                1. Detailed answers to questions
                2. Novel explanations or analogies
                3. Unique insights or perspectives
                4. Common concerns being addressed

                For each opportunity:
                1. Extract exact quotes
                2. Suggest a title
                3. List key points
                4. Recommend content type
                5. Identify target audience
                6. Note location in transcript

                Format as a list of JSON objects.""",
                },
                {"role": "user", "content": transcript},
            ],
        )

        return [ContentOpportunity(**opp) for opp in result]

    async def _create_activities(
        self,
        action_items: list[ActionItem],
        client: Client,
    ) -> None:
        """Create activities for action items.

        Creates an activity record for each action item, linked to the client.
        """
        for item in action_items:
            await Activity.objects.create(
                activity_type="action_item",
                client=client,
                summary=item.description,
                description=item.context,
                priority=item.priority,
                due_date=item.due_date,
                status="pending",
                metadata={
                    "transcript_location": item.transcript_location,
                    "confidence": item.confidence,
                    "assigned_to": item.assigned_to,
                },
            )
