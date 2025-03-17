"""Software development and code review agent."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import structlog

from ..base import SyzygyAgent
from .chat_history import ChatHistoryAgent

logger = structlog.get_logger(__name__)


class CodeReview(BaseModel):
    """Code review analysis and suggestions."""

    issues: List[Dict[str, Any]]
    improvements: List[Dict[str, Any]]
    security_concerns: List[str]
    performance_notes: List[str]
    maintainability_score: float = Field(ge=0, le=100)
    test_coverage_analysis: Dict[str, Any]


class ArchitectureDecision(BaseModel):
    """Technical architecture decision with rationale."""

    decision: str
    context: str
    alternatives: List[Dict[str, Any]]
    rationale: str
    consequences: Dict[str, List[str]]
    implementation_plan: List[str]


class TechnicalSpec(BaseModel):
    """Technical specification for implementation."""

    components: List[Dict[str, Any]]
    interfaces: List[Dict[str, Any]]
    data_models: List[Dict[str, Any]]
    dependencies: List[str]
    deployment_notes: List[str]


class SoftwareDeveloperAgent(SyzygyAgent):
    """Agent for software development assistance and code review.

    Features:
    - Code review and analysis
    - Architecture decisions
    - Technical specifications
    - Implementation guidance
    - Best practices enforcement
    """

    def __init__(self, chat_agent: ChatHistoryAgent):
        """Initialize the developer agent.

        Args:
            chat_agent: Chat history agent for context
        """
        super().__init__(
            task_type="software_development",
            model="qwen-coder-32b",  # Use code-specialized model
        )
        self.chat_agent = chat_agent

    async def review_code(self, code: str, context: Optional[str] = None) -> CodeReview:
        """Review code for issues and improvements.

        Args:
            code: Code to review
            context: Optional context about the code

        Returns:
            Code review analysis
        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Review this code:

Code:
{code}

Context:
{context or "None"}

Analyze:
1. Code quality and style
2. Potential bugs
3. Security concerns
4. Performance issues
5. Test coverage
6. Documentation needs""",
                }
            ],
            model="qwen-coder-32b",
            metadata={"code_length": len(code)},
        )

        return CodeReview(**result)

    async def make_architecture_decision(
        self, problem: str, constraints: List[str]
    ) -> ArchitectureDecision:
        """Make and document architecture decision.

        Args:
            problem: Problem to solve
            constraints: List of constraints

        Returns:
            Architecture decision with rationale
        """
        context = await self.chat_agent.get_context(
            query=f"architecture decisions {problem}"
        )

        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Make architecture decision:

Problem:
{problem}

Constraints:
{constraints}

Context:
{context.summary}

Consider:
1. Technical requirements
2. Scalability needs
3. Maintenance burden
4. Team capabilities
5. Future flexibility""",
                }
            ],
            model="qwen-coder-32b",
        )

        return ArchitectureDecision(**result)

    async def create_technical_spec(
        self, requirements: List[str], context: Optional[str] = None
    ) -> TechnicalSpec:
        """Create technical specification.

        Args:
            requirements: List of requirements
            context: Optional context

        Returns:
            Technical specification
        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Create technical specification:

Requirements:
{requirements}

Context:
{context or "None"}

Include:
1. Component design
2. Interface definitions
3. Data models
4. Dependencies
5. Deployment notes""",
                }
            ],
            model="qwen-coder-32b",
            metadata={"req_count": len(requirements)},
        )

        return TechnicalSpec(**result)

    async def suggest_implementation(
        self, spec: TechnicalSpec, language: str
    ) -> Dict[str, Any]:
        """Suggest implementation approach.

        Args:
            spec: Technical specification
            language: Target programming language

        Returns:
            Implementation suggestions
        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Suggest implementation in {language}:

Specification:
{spec.dict()}

Consider:
1. Language idioms
2. Framework choices
3. Library selection
4. Testing approach
5. Performance optimization""",
                }
            ],
            model="qwen-coder-32b",
            metadata={"language": language},
        )

        return result

    async def evaluate_technical_debt(self, codebase_summary: str) -> Dict[str, Any]:
        """Evaluate technical debt in codebase.

        Args:
            codebase_summary: Summary of codebase state

        Returns:
            Technical debt analysis
        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Evaluate technical debt:

Codebase Summary:
{codebase_summary}

Analyze:
1. Code complexity
2. Outdated patterns
3. Missing tests
4. Documentation gaps
5. Upgrade needs""",
                }
            ],
            model="qwen-coder-32b",
        )

        return result
