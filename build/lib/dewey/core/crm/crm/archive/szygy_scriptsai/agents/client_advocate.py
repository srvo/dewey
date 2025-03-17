"""Client relationship and task prioritization agent."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import structlog

from ..base import SyzygyAgent
from .chat_history import ChatHistoryAgent

logger = structlog.get_logger(__name__)


class ClientProfile(BaseModel):
    """Profile of a client with relationship history."""

    id: str
    name: str
    engagement_level: int = Field(ge=1, le=5)
    last_contact: datetime
    contact_frequency: float  # contacts per month
    key_topics: List[str]
    preferences: Dict[str, Any]
    success_metrics: Dict[str, float]
    risk_factors: List[str]


class ClientTask(BaseModel):
    """A task related to client management."""

    id: str
    client_id: str
    type: str  # followup, review, outreach, etc.
    description: str
    due_date: Optional[datetime]
    priority: int = Field(ge=1, le=5)
    estimated_impact: float
    dependencies: List[str] = Field(default_factory=list)


class RelationshipInsight(BaseModel):
    """Analysis of client relationship."""

    strengths: List[str]
    areas_for_improvement: List[str]
    engagement_trends: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    opportunity_areas: List[str]
    next_steps: List[str]


class ClientAdvocate(SyzygyAgent):
    """Agent for managing client relationships and prioritizing client work.

    Features:
    - Client relationship analysis
    - Task prioritization
    - Engagement monitoring
    - Risk assessment
    - Opportunity identification
    """

    def __init__(self, chat_agent: ChatHistoryAgent):
        """Initialize the client advocate agent.

        Args:
            chat_agent: Chat history agent for context
        """
        super().__init__(
            task_type="client_advocacy",
            model="mixtral-8x7b",  # Use sophisticated model for relationship analysis
        )
        self.chat_agent = chat_agent

    async def analyze_client(self, profile: ClientProfile) -> RelationshipInsight:
        """Analyze client relationship and generate insights.

        Args:
            profile: Client profile to analyze

        Returns:
            Relationship insights and recommendations
        """
        # Get context about client interactions
        context = await self.chat_agent.get_context(query=f"client:{profile.name}")

        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Analyze this client relationship:

Client Profile:
{profile.dict()}

Recent Context:
{context.summary}
Key Points: {", ".join(context.key_points)}

Consider:
1. Engagement patterns
2. Success metrics
3. Risk factors
4. Communication preferences
5. Growth opportunities""",
                }
            ],
            model="mixtral-8x7b",
            metadata={"client_id": profile.id},
        )

        return RelationshipInsight(**result)

    async def prioritize_tasks(
        self, tasks: List[ClientTask], profiles: Dict[str, ClientProfile]
    ) -> List[ClientTask]:
        """Prioritize client-related tasks.

        Args:
            tasks: List of tasks to prioritize
            profiles: Dictionary mapping client IDs to profiles

        Returns:
            Prioritized task list
        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Prioritize these client tasks:

Tasks:
{[t.dict() for t in tasks]}

Client Profiles:
{[p.dict() for p in profiles.values()]}

Consider:
1. Client engagement levels
2. Task impact and urgency
3. Risk factors
4. Dependencies
5. Resource constraints""",
                }
            ],
            model="mixtral-8x7b",
            metadata={"task_count": len(tasks), "client_count": len(profiles)},
        )

        return [ClientTask(**t) for t in result["prioritized_tasks"]]

    async def identify_risks(self, profile: ClientProfile) -> List[Dict[str, Any]]:
        """Identify potential risks in client relationship.

        Args:
            profile: Client profile to analyze

        Returns:
            List of identified risks with mitigation strategies
        """
        context = await self.chat_agent.get_context(
            query=f"client:{profile.name} risks concerns issues"
        )

        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Identify risks for this client:

Profile:
{profile.dict()}

Context:
{context.summary}

Consider:
1. Engagement patterns
2. Success metrics
3. Industry factors
4. Communication gaps
5. Resource alignment""",
                }
            ],
            model="mixtral-8x7b",
            metadata={"client_id": profile.id},
        )

        return result["risks"]

    async def suggest_engagement(self, profile: ClientProfile) -> Dict[str, Any]:
        """Suggest engagement strategies for a client.

        Args:
            profile: Client profile

        Returns:
            Engagement recommendations
        """
        insights = await self.analyze_client(profile)

        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Suggest engagement strategies:

Profile:
{profile.dict()}

Insights:
{insights.dict()}

Recommend:
1. Communication approach
2. Meeting frequency
3. Content/topics
4. Success metrics
5. Growth opportunities""",
                }
            ],
            model="mixtral-8x7b",
            metadata={
                "client_id": profile.id,
                "engagement_level": profile.engagement_level,
            },
        )

        return result

    async def generate_client_brief(self, profile: ClientProfile) -> str:
        """Generate a comprehensive client brief.

        Args:
            profile: Client profile

        Returns:
            Formatted client brief
        """
        insights = await self.analyze_client(profile)
        risks = await self.identify_risks(profile)

        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Generate a client brief:

Profile:
{profile.dict()}

Insights:
{insights.dict()}

Risks:
{risks}

Include:
1. Relationship summary
2. Key metrics and trends
3. Current initiatives
4. Risk factors
5. Strategic recommendations""",
                }
            ],
            model="mixtral-8x7b",
        )

        return result["brief"]
