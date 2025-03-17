"""Wellness monitoring and self-care intervention agent.

This module implements an AI agent that monitors user work patterns and suggests
appropriate self-care interventions. It uses chat history and work patterns to:

- Track work hours and break frequency
- Detect stress indicators
- Suggest context-appropriate interventions
- Generate wellness reports
- Prevent burnout through proactive suggestions

Key Features:
- Real-time work pattern analysis
- Context-aware break suggestions
- Stress level detection
- Daily wellness reporting
- Adaptive intervention strategies
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import structlog

from ..base import SyzygyAgent
from .chat_history import ChatHistoryAgent

# Configure structured logging for better observability
logger = structlog.get_logger(__name__)


class WellnessMetrics(BaseModel):
    """Quantitative metrics tracking user wellness and work patterns.

    Attributes:
        work_hours_today (float): Total hours worked today
        consecutive_work_time (timedelta): Duration of current work session
        last_break (datetime): Timestamp of last break
        break_frequency (float): Average breaks per hour
        stress_indicators (List[str]): Detected stress signals from chat/behavior
        wellness_score (float): Overall wellness score (0-100)
    """

    work_hours_today: float
    consecutive_work_time: timedelta
    last_break: datetime
    break_frequency: float  # breaks per hour
    stress_indicators: List[str]
    wellness_score: float = Field(ge=0, le=100)


class SelfCareIntervention(BaseModel):
    """A suggested wellness intervention with context and rationale.

    Attributes:
        type (str): Type of intervention (break, exercise, meditation, etc.)
        urgency (int): Urgency level from 1 (low) to 5 (critical)
        reason (str): Explanation for why intervention is needed
        suggested_duration (timedelta): Recommended duration
        benefits (List[str]): Expected benefits of the intervention
        context_appropriate (bool): Whether suggestion fits current context
    """

    type: str  # break, exercise, meditation, etc.
    urgency: int = Field(ge=1, le=5)
    reason: str
    suggested_duration: timedelta
    benefits: List[str]
    context_appropriate: bool


class SelfCareAgent(SyzygyAgent):
    """AI agent for monitoring user wellness and suggesting self-care interventions.

    This agent analyzes work patterns, chat history, and behavioral signals to:
    - Detect signs of fatigue and stress
    - Suggest timely, context-aware interventions
    - Track wellness metrics over time
    - Prevent burnout through proactive suggestions

    Key Features:
    - Real-time work pattern analysis
    - Context-aware break suggestions
    - Stress level detection
    - Daily wellness reporting
    - Adaptive intervention strategies

    Args:
        chat_agent (ChatHistoryAgent): Agent providing chat context and history

    Attributes:
        chat_agent (ChatHistoryAgent): Reference to chat history agent
    """

    def __init__(self, chat_agent: ChatHistoryAgent):
        """Initialize the self-care agent with chat context provider.

        Args:
            chat_agent (ChatHistoryAgent): Chat history agent providing context
        """
        super().__init__(
            task_type="wellness_monitoring",
            model="mixtral-8x7b",  # Use sophisticated model for nuanced analysis
        )
        self.chat_agent = chat_agent

    async def analyze_work_patterns(self) -> WellnessMetrics:
        """Analyze recent work patterns and wellness indicators."""
        context = await self.chat_agent.get_context()

        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Analyze work patterns and wellness indicators from recent history:

Context Summary: {context.summary}
Key Points: {", ".join(context.key_points)}
Last Action: {context.last_action or "None"}

Consider:
1. Work duration and intensity
2. Break patterns
3. Stress indicators in communication
4. Time of day effects
5. Energy level indicators""",
                }
            ],
            model="mixtral-8x7b",
            metadata={"context": context.dict()},
        )

        return WellnessMetrics(**result)

    async def check_intervention_needed(self) -> Optional[SelfCareIntervention]:
        """Check if a wellness intervention is needed."""
        metrics = await self.analyze_work_patterns()

        if (
            metrics.consecutive_work_time > timedelta(hours=2)
            or metrics.work_hours_today > 8
            or metrics.break_frequency < 1
            or metrics.wellness_score < 70
            or len(metrics.stress_indicators) > 2
        ):
            result = await self.run(
                messages=[
                    {
                        "role": "system",
                        "content": f"""Suggest an appropriate wellness intervention:

Current Metrics:
- Work time: {metrics.consecutive_work_time}
- Hours today: {metrics.work_hours_today}
- Break frequency: {metrics.break_frequency}/hour
- Wellness score: {metrics.wellness_score}
- Stress indicators: {", ".join(metrics.stress_indicators)}

Consider:
1. Current work context
2. Time of day
3. Previous interventions
4. Physical vs. mental needs
5. Environmental factors""",
                    }
                ],
                model="mixtral-8x7b",
                metadata={"metrics": metrics.dict()},
            )

            return SelfCareIntervention(**result)

        return None

    async def suggest_break_activity(self) -> str:
        """Suggest a specific break activity based on context."""
        context = await self.chat_agent.get_context()
        metrics = await self.analyze_work_patterns()

        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Suggest a specific break activity:

Current State:
- Wellness score: {metrics.wellness_score}
- Stress indicators: {", ".join(metrics.stress_indicators)}
- Work context: {context.summary}

Consider:
1. Time available
2. Energy level
3. Physical vs. mental needs
4. Environmental constraints
5. Previous activities""",
                }
            ],
            model="mixtral-8x7b",
        )

        return result["activity_suggestion"]

    async def monitor_and_intervene(self) -> Optional[str]:
        """Monitor work patterns and intervene if needed."""
        if intervention := await self.check_intervention_needed():
            if intervention.urgency >= 4:
                return (
                    f"⚠️ URGENT: {intervention.reason}\n\nPlease take a {intervention.suggested_duration} {intervention.type} break.\n\nBenefits:\n"
                    + "\n".join(f"- {b}" for b in intervention.benefits)
                )
            elif intervention.urgency >= 2:
                activity = await self.suggest_break_activity()
                return f"💡 Wellness Suggestion: {intervention.reason}\n\nConsider: {activity}"

        return None

    async def get_daily_wellness_report(self) -> Dict[str, Any]:
        """Generate a daily wellness report."""
        metrics = await self.analyze_work_patterns()

        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Generate a daily wellness report:

Metrics:
{metrics.dict()}

Include:
1. Overall wellness assessment
2. Key concerns
3. Positive patterns
4. Recommendations
5. Tomorrow's focus areas""",
                }
            ],
            model="mixtral-8x7b",
            metadata={"metrics": metrics.dict()},
        )

        return result
