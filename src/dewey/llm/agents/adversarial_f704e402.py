# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Critical analysis and risk identification agent."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel

from ..base import SyzygyAgent

if TYPE_CHECKING:
    from .chat_history import ChatHistoryAgent

logger = structlog.get_logger(__name__)


class RiskAnalysis(BaseModel):
    """Analysis of potential risks and issues."""

    critical_issues: list[dict[str, Any]]
    assumptions: list[str]
    edge_cases: list[str]
    dependencies: list[str]
    failure_modes: list[dict[str, Any]]
    mitigation_suggestions: list[str]


class Counterargument(BaseModel):
    """Structured counterargument to a proposal."""

    key_concerns: list[str]
    logical_flaws: list[str]
    evidence_gaps: list[str]
    alternative_perspectives: list[dict[str, Any]]
    impact_analysis: dict[str, Any]


class AdversarialAgent(SyzygyAgent):
    """Agent for critical analysis and devil's advocacy.

    Features:
    - Risk identification
    - Assumption challenging
    - Edge case analysis
    - Failure mode exploration
    - Alternative perspective generation
    """

    def __init__(self, chat_agent: ChatHistoryAgent) -> None:
        """Initialize the adversarial agent.

        Args:
        ----
            chat_agent: Chat history agent for context

        """
        super().__init__(
            task_type="critical_analysis",
            model="mixtral-8x7b",  # Use sophisticated model for nuanced analysis
        )
        self.chat_agent = chat_agent

    async def analyze_risks(
        self,
        proposal: str,
        context: str | None = None,
    ) -> RiskAnalysis:
        """Analyze potential risks and issues.

        Args:
        ----
            proposal: Proposal to analyze
            context: Optional context

        Returns:
        -------
            Risk analysis

        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Critically analyze this proposal:

Proposal:
{proposal}

Context:
{context or "None"}

Identify:
1. Critical failure points
2. Hidden assumptions
3. Edge cases
4. Dependencies
5. Potential problems
6. Mitigation strategies""",
                },
            ],
            model="mixtral-8x7b",
            metadata={"proposal_length": len(proposal)},
        )

        return RiskAnalysis(**result)

    async def challenge_assumptions(
        self,
        assumptions: list[str],
        context: str | None = None,
    ) -> list[dict[str, Any]]:
        """Challenge stated assumptions.

        Args:
        ----
            assumptions: List of assumptions to challenge
            context: Optional context

        Returns:
        -------
            List of challenges to assumptions

        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Challenge these assumptions:

Assumptions:
{assumptions}

Context:
{context or "None"}

For each assumption:
1. Question validity
2. Find counterexamples
3. Identify dependencies
4. Test edge cases
5. Consider alternatives""",
                },
            ],
            model="mixtral-8x7b",
            metadata={"assumption_count": len(assumptions)},
        )

        return result["challenges"]

    async def generate_counterarguments(
        self,
        argument: str,
        context: str | None = None,
    ) -> Counterargument:
        """Generate structured counterarguments.

        Args:
        ----
            argument: Argument to counter
            context: Optional context

        Returns:
        -------
            Structured counterargument

        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Generate counterarguments:

Argument:
{argument}

Context:
{context or "None"}

Consider:
1. Logical flaws
2. Missing evidence
3. Alternative views
4. Implementation challenges
5. Unintended consequences""",
                },
            ],
            model="mixtral-8x7b",
        )

        return Counterargument(**result)

    async def explore_failure_modes(
        self,
        system: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Explore potential failure modes.

        Args:
        ----
            system: System description

        Returns:
        -------
            List of potential failure modes

        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Explore failure modes:

System:
{system}

Analyze:
1. Component failures
2. Integration points
3. External dependencies
4. Resource constraints
5. Edge conditions""",
                },
            ],
            model="mixtral-8x7b",
            metadata={"system_complexity": len(str(system))},
        )

        return result["failure_modes"]

    async def suggest_stress_tests(
        self,
        system: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Suggest stress tests and edge cases.

        Args:
        ----
            system: System description

        Returns:
        -------
            List of suggested tests

        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Suggest stress tests:

System:
{system}

Design tests for:
1. Load handling
2. Error conditions
3. Resource limits
4. Timing issues
5. Integration points""",
                },
            ],
            model="mixtral-8x7b",
        )

        return result["stress_tests"]

    async def evaluate_complexity(self, proposal: str) -> dict[str, Any]:
        """Evaluate complexity and maintenance burden.

        Args:
        ----
            proposal: Proposal to evaluate

        Returns:
        -------
            Complexity analysis

        """
        return await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Evaluate complexity:

Proposal:
{proposal}

Analyze:
1. Implementation complexity
2. Maintenance burden
3. Learning curve
4. Integration challenges
5. Long-term implications""",
                },
            ],
            model="mixtral-8x7b",
        )
