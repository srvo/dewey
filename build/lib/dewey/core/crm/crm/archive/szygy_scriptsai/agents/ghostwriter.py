"""Content generation and refinement agent in Sloan's voice."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import structlog

from ..base import SyzygyAgent
from .chat_history import ChatHistoryAgent

logger = structlog.get_logger(__name__)


class ContentBrief(BaseModel):
    """Brief for content generation."""

    topic: str
    type: str  # email, document, post, etc.
    key_points: List[str]
    tone: str
    target_audience: str
    context: Optional[str]
    constraints: Dict[str, Any] = Field(default_factory=dict)


class StyleGuide(BaseModel):
    """Writing style preferences and patterns."""

    voice_characteristics: List[str]
    common_phrases: List[str]
    avoided_terms: List[str]
    sentence_structure: Dict[str, Any]
    formatting_preferences: Dict[str, Any]


class ContentDraft(BaseModel):
    """A draft of generated content."""

    content: str
    sections: List[Dict[str, str]]
    key_phrases: List[str]
    tone_analysis: Dict[str, float]
    improvement_suggestions: List[str]


class SloanGhostwriter(SyzygyAgent):
    """Agent for generating and refining content in Sloan's voice.

    Features:
    - Voice-matched content generation
    - Style analysis and adaptation
    - Context-aware writing
    - Iterative refinement
    - Format-specific optimization
    """

    def __init__(self, chat_agent: ChatHistoryAgent):
        """Initialize the ghostwriter agent.

        Args:
            chat_agent: Chat history agent for context
        """
        super().__init__(
            task_type="content_generation",
            model="mixtral-8x7b",  # Use sophisticated model for nuanced writing
        )
        self.chat_agent = chat_agent

    async def analyze_writing_style(self) -> StyleGuide:
        """Analyze writing style from chat history."""
        # Get broad context of writing style
        context = await self.chat_agent.get_context(
            query="writing style voice tone communication patterns"
        )

        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Analyze writing style from this context:

Context Summary: {context.summary}
Key Points: {", ".join(context.key_points)}

Identify:
1. Voice characteristics
2. Common phrases and expressions
3. Sentence structure patterns
4. Formatting preferences
5. Communication style""",
                }
            ],
            model="mixtral-8x7b",
            metadata={"context": context.dict()},
        )

        return StyleGuide(**result)

    async def generate_draft(
        self, brief: ContentBrief, style: Optional[StyleGuide] = None
    ) -> ContentDraft:
        """Generate content draft based on brief.

        Args:
            brief: Content requirements
            style: Optional style guide (will analyze if not provided)

        Returns:
            Generated content draft
        """
        if not style:
            style = await self.analyze_writing_style()

        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Generate content matching this brief and style:

Brief:
{brief.dict()}

Style Guide:
{style.dict()}

Requirements:
1. Match voice and tone
2. Address key points
3. Follow formatting preferences
4. Consider audience
5. Maintain authenticity""",
                }
            ],
            model="mixtral-8x7b",
            metadata={"content_type": brief.type, "audience": brief.target_audience},
        )

        return ContentDraft(**result)

    async def refine_content(
        self, draft: ContentDraft, style: StyleGuide, feedback: Optional[str] = None
    ) -> ContentDraft:
        """Refine content based on style and feedback.

        Args:
            draft: Content draft to refine
            style: Style guide to follow
            feedback: Optional feedback to incorporate

        Returns:
            Refined content draft
        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Refine this content:

Current Draft:
{draft.dict()}

Style Guide:
{style.dict()}

Feedback:
{feedback or "None"}

Focus on:
1. Voice consistency
2. Clarity and flow
3. Impact and engagement
4. Technical accuracy
5. Authenticity preservation""",
                }
            ],
            model="mixtral-8x7b",
            metadata={"has_feedback": bool(feedback)},
        )

        return ContentDraft(**result)

    async def generate_variations(
        self, content: str, style: StyleGuide, count: int = 3
    ) -> List[str]:
        """Generate variations of content in the same voice.

        Args:
            content: Original content
            style: Style guide to follow
            count: Number of variations to generate

        Returns:
            List of content variations
        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Generate {count} variations of this content:

Original:
{content}

Style Guide:
{style.dict()}

Requirements:
1. Maintain core message
2. Vary structure/approach
3. Match voice consistently
4. Preserve key points
5. Optimize for impact""",
                }
            ],
            model="mixtral-8x7b",
            metadata={"variation_count": count},
        )

        return result["variations"]

    async def adapt_for_medium(
        self, content: str, target_medium: str, style: StyleGuide
    ) -> str:
        """Adapt content for specific medium while maintaining voice.

        Args:
            content: Content to adapt
            target_medium: Target platform/format
            style: Style guide to follow

        Returns:
            Adapted content
        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Adapt this content for {target_medium}:

Content:
{content}

Style Guide:
{style.dict()}

Consider:
1. Medium constraints
2. Format requirements
3. Audience expectations
4. Voice consistency
5. Platform optimization""",
                }
            ],
            model="mixtral-8x7b",
            metadata={"medium": target_medium},
        )

        return result["adapted_content"]
