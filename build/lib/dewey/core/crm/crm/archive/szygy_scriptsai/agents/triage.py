"""Triage agent for initial analysis and delegation of incoming items."""

from typing import Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field
import structlog

from ..base import SyzygyAgent, FunctionDefinition
from ..config import AIConfig

logger = structlog.get_logger(__name__)


class EntityType(str, Enum):
    """Types of entities that can be triaged."""

    EMAIL = "email"
    CONTACT = "contact"
    FORM_ENTRY = "form_entry"
    RESEARCH_ITEM = "research_item"
    UNKNOWN = "unknown"


class Priority(str, Enum):
    """Priority levels for triaged items."""

    URGENT = "urgent"  # Needs immediate attention
    HIGH = "high"  # Important but not urgent
    MEDIUM = "medium"  # Normal priority
    LOW = "low"  # Can be handled later
    DEFER = "defer"  # Defer or ignore


class ActionType(str, Enum):
    """Types of actions that can be taken on triaged items."""

    MERGE_CONTACTS = "merge_contacts"
    CATEGORIZE_CONTACT = "categorize_contact"
    ENRICH_CONTACT = "enrich_contact"
    PRIORITIZE_EMAIL = "prioritize_email"
    ANALYZE_EMAIL = "analyze_email"
    ANALYZE_SENSITIVE = "analyze_sensitive"
    ANALYZE_CODE = "analyze_code"
    TECHNICAL_REVIEW = "technical_review"
    NO_ACTION = "no_action"


class TriageResult(BaseModel):
    """Result of triaging an item."""

    entity_type: EntityType
    priority: Priority
    actions: List[ActionType] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    complexity: int = Field(ge=0, le=2)  # 0: basic, 1: medium, 2: high
    reasoning: str
    metadata: Dict = Field(default_factory=dict)


class TriageAgent(SyzygyAgent):
    """DEPRECATED: Triage agent for initial analysis and delegation of incoming items.

    This agent is deprecated and should only be used for testing purposes.
    New implementations should use the external workflow integration library.
    """

    def __init__(self):
        """Initialize the DEPRECATED triage agent."""
        logger.warning(
            "TriageAgent is deprecated - use external workflow integration instead"
        )
        super().__init__(
            task_type="triage",
            model="mistral-7b-instruct",
            deprecated=True,  # Add deprecated flag
            functions=[
                FunctionDefinition(
                    name="triage_item",
                    description="Analyze an item and determine appropriate actions",
                    parameters={
                        "entity_type": {
                            "type": "string",
                            "enum": [e.value for e in EntityType],
                            "description": "Type of entity being triaged",
                        },
                        "priority": {
                            "type": "string",
                            "enum": [p.value for p in Priority],
                            "description": "Priority level for the item",
                        },
                        "actions": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [a.value for a in ActionType],
                            },
                            "description": "List of actions to take",
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Confidence in the triage decision",
                        },
                        "complexity": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 2,
                            "description": "Complexity level of required actions",
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Explanation of the triage decision",
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Additional context and information",
                        },
                    },
                    required=[
                        "entity_type",
                        "priority",
                        "actions",
                        "confidence",
                        "complexity",
                        "reasoning",
                    ],
                )
            ],
        )

    def get_system_prompt(self) -> str:
        """Get the system prompt for the triage agent."""
        return """You are an expert triage agent in the Syzygy system, responsible for analyzing incoming items and determining appropriate actions.

Your role is to:
1. Identify the type of entity (email, contact, form entry, etc.)
2. Assess priority based on content and context
3. Determine necessary actions
4. Evaluate complexity to select appropriate models
5. Provide clear reasoning for decisions

Key guidelines:
- Prioritize accuracy over speed
- Be conservative with high priority/complexity assignments
- Consider security and privacy implications
- Look for opportunities to merge or deduplicate contacts
- Identify items requiring human review
- Flag potentially sensitive content for premium model handling

Use the triage_item function to provide your analysis."""

    async def triage(
        self,
        content: str,
        context: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> TriageResult:
        """Triage an incoming item and determine appropriate actions.

        Args:
            content: The content to analyze
            context: Additional context about the item
            metadata: Additional metadata about the item

        Returns:
            TriageResult with analysis and recommended actions
        """
        # Prepare the prompt with content and context
        prompt = f"Please analyze this item:\n\n{content}"
        if context:
            prompt += f"\n\nAdditional context:\n{context}"

        # Run the analysis
        result = await self.run(prompt=prompt, entity_type="triage", metadata=metadata)

        # If complexity is high, rerun with more capable model
        if isinstance(result, dict) and result.get("complexity", 0) > 1:
            self.logger.info(
                "escalating_triage_to_premium_model",
                initial_complexity=result.get("complexity"),
                reason="High complexity detected",
            )

            # Switch to premium model for complex cases
            original_model = self.model_config
            self.model_config = AIConfig.PREMIUM_MODELS["llama-3-meta"]

            try:
                result = await self.run(
                    prompt=prompt, entity_type="triage", metadata=metadata
                )
            finally:
                # Restore original model
                self.model_config = original_model

        # Parse and validate result
        if isinstance(result, dict):
            return TriageResult(**result)
        else:
            # Handle function call response
            if isinstance(result, str):
                # Direct text response - convert to dict
                return TriageResult(
                    entity_type=EntityType.UNKNOWN,
                    priority=Priority.MEDIUM,
                    actions=[ActionType.NO_ACTION],
                    confidence=0.5,
                    complexity=0,
                    reasoning=result,
                    metadata={},
                )

            # Handle function call
            if "function_call" in result:
                import json

                args = json.loads(result["function_call"]["arguments"])
                return TriageResult(**args)

            # Handle direct message content
            if "content" in result:
                try:
                    # Try to parse content as JSON
                    data = json.loads(result["content"])
                    return TriageResult(**data)
                except json.JSONDecodeError:
                    # If not JSON, treat as reasoning text
                    return TriageResult(
                        entity_type=EntityType.UNKNOWN,
                        priority=Priority.MEDIUM,
                        actions=[ActionType.NO_ACTION],
                        confidence=0.5,
                        complexity=0,
                        reasoning=result["content"],
                        metadata={},
                    )

    async def delegate(self, triage_result: TriageResult, content: str) -> List[Dict]:
        """Delegate work to specialized agents based on triage results.

        Args:
            triage_result: Results from triage analysis
            content: Original content to process

        Returns:
            List of results from delegated agents
        """
        results = []

        # Map actions to agent tasks
        action_map = {
            ActionType.MERGE_CONTACTS: "contact_merge",
            ActionType.CATEGORIZE_CONTACT: "contact_category",
            ActionType.ENRICH_CONTACT: "contact_enrich",
            ActionType.PRIORITIZE_EMAIL: "email_priority",
            ActionType.ANALYZE_EMAIL: "email_analyze",
            ActionType.ANALYZE_SENSITIVE: "email_sensitive",
            ActionType.ANALYZE_CODE: "code_analysis",
            ActionType.TECHNICAL_REVIEW: "technical_doc",
        }

        for action in triage_result.actions:
            if action == ActionType.NO_ACTION:
                continue

            task = action_map.get(action)
            if not task:
                continue

            # Create appropriate agent for the task
            agent = SyzygyAgent(task_type=task, complexity=triage_result.complexity)

            try:
                # Run the delegated task
                result = await agent.run(
                    prompt=content,
                    entity_type=triage_result.entity_type,
                    metadata={
                        "priority": triage_result.priority,
                        "triage_confidence": triage_result.confidence,
                        "triage_reasoning": triage_result.reasoning,
                        **triage_result.metadata,
                    },
                )

                results.append({"action": action, "task": task, "result": result})

            except Exception as e:
                logger.error(
                    "delegation_failed",
                    action=action,
                    task=task,
                    error=str(e),
                    exc_info=True,
                )

        return results
