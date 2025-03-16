"""Strategic optimization and prioritization agent for personal productivity."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field

from ..base import SyzygyAgent

if TYPE_CHECKING:
    from datetime import datetime

    from .chat_history import ChatHistoryAgent

logger = structlog.get_logger(__name__)


class Task(BaseModel):
    """A task to be prioritized."""

    id: str
    title: str
    description: str | None
    priority: int = Field(ge=0, le=5)
    due_date: datetime | None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategicPriority(BaseModel):
    """A strategic priority with associated goals."""

    name: str
    description: str
    importance: int = Field(ge=0, le=10)
    timeline: str
    goals: list[str]
    metrics: list[str]


class OptimizationResult(BaseModel):
    """Result of optimization analysis."""

    recommendations: list[str]
    task_priorities: list[Task]
    strategic_alignment: dict[str, float]
    energy_management: dict[str, Any]
    next_steps: list[str]
    confidence: float


class SloanOptimizer(SyzygyAgent):
    """Agent for optimizing personal productivity and strategic alignment.

    Features:
    - Task prioritization based on strategic goals
    - Energy and attention management
    - Work-life balance optimization
    - Strategic goal alignment
    - Adaptive recommendations
    """

    def __init__(self, chat_agent: ChatHistoryAgent) -> None:
        """Initialize the Sloan Optimizer agent.

        Args:
        ----
            chat_agent: Chat history agent for context

        """
        super().__init__(
            task_type="strategic_optimization",
            model="mixtral-8x7b",  # Use sophisticated model for complex analysis
        )
        self.chat_agent = chat_agent

    async def analyze_current_state(self) -> OptimizationResult:
        """Analyze current state and provide optimization recommendations."""
        # Get recent context and strategic discussions
        context = await self.chat_agent.get_context()

        # Analyze with sophisticated model
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Based on the following context, analyze current state and provide optimization recommendations:

Context Summary: {context.summary}
Key Points: {", ".join(context.key_points)}
Last Action: {context.last_action or "None"}

Consider:
1. Strategic alignment
2. Energy management
3. Work-life balance
4. Task prioritization
5. Next steps""",
                },
            ],
            model="mixtral-8x7b",
            metadata={"context": context.dict()},
        )

        return OptimizationResult(**result)

    async def optimize_tasks(
        self,
        tasks: list[Task],
        priorities: list[StrategicPriority],
    ) -> list[Task]:
        """Optimize task ordering based on strategic priorities.

        Args:
        ----
            tasks: List of tasks to optimize
            priorities: Strategic priorities for alignment

        Returns:
        -------
            Optimized task list

        """
        # Get current context
        context = await self.chat_agent.get_context()

        # Analyze with model
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Optimize these tasks based on strategic priorities and current context:

Tasks:
{[t.dict() for t in tasks]}

Priorities:
{[p.dict() for p in priorities]}

Context:
{context.summary}

Consider:
1. Strategic alignment
2. Due dates and urgency
3. Dependencies
4. Energy levels
5. Work-life balance""",
                },
            ],
            model="mixtral-8x7b",
            metadata={"task_count": len(tasks), "priority_count": len(priorities)},
        )

        return [Task(**t) for t in result["optimized_tasks"]]

    async def suggest_breaks(self) -> list[str]:
        """Suggest optimal break times and activities."""
        context = await self.chat_agent.get_context()

        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Based on current context and energy levels, suggest optimal breaks:

Context:
{context.summary}
Last Action: {context.last_action}

Consider:
1. Current energy levels
2. Work intensity
3. Time of day
4. Recent breaks
5. Upcoming tasks""",
                },
            ],
            model="mixtral-8x7b",
        )

        return result["break_suggestions"]

    async def check_work_life_balance(self) -> dict[str, Any]:
        """Analyze work-life balance and provide recommendations."""
        # Get broader context
        context = await self.chat_agent.get_context()

        return await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Analyze work-life balance based on recent history:

Context:
{context.summary}
Key Points: {", ".join(context.key_points)}

Consider:
1. Working hours
2. Break frequency
3. Personal time
4. Stress indicators
5. Social interactions
6. Health indicators""",
                },
            ],
            model="mixtral-8x7b",
            metadata={"context": context.dict()},
        )
