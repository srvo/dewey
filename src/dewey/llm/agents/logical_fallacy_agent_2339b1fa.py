# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Logical fallacy detection agent for analyzing reasoning and arguments."""
from .logical_fallacy_agent import LogicalFallacyAgent  # Import the new agent

async def analyze_text(text: str, context: str | None = None) -> str:
    """Analyzes text for logical fallacies using the new LogicalFallacyAgent."""
    agent = LogicalFallacyAgent()
    return await agent.analyze_text(text, context)
from __future__ import annotations

import json
from typing import Any

import structlog
from pydantic import BaseModel, Field

from ..base import FunctionDefinition, SyzygyAgent

logger = structlog.get_logger(__name__)


class FallacyType(BaseModel):
    """Model representing a type of logical fallacy."""

    name: str
    description: str
    example: str
    category: str = Field(
        description="Category of fallacy (e.g., 'relevance', 'ambiguity', 'presumption')",
    )


class FallacyInstance(BaseModel):
    """Model representing a detected fallacy instance in text."""

    fallacy_type: str
    confidence: float = Field(ge=0, le=1)
    text_segment: str
    explanation: str
    suggestion: str | None = None


class FallacyAnalysis(BaseModel):
    """Complete analysis of logical fallacies in a text."""

    detected_fallacies: list[FallacyInstance]
    overall_reasoning_score: float = Field(ge=0, le=1)
    major_concerns: list[str]
    improvement_suggestions: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)


class LogicalFallacyAgent(SyzygyAgent):
    """Agent for detecting and analyzing logical fallacies in text.

    This agent is trained to identify common logical fallacies including:
    - Ad Hominem
    - Straw Man
    - False Dichotomy
    - Appeal to Authority
    - Slippery Slope
    - Hasty Generalization
    - Post Hoc Fallacy
    - Appeal to Emotion
    - Bandwagon Fallacy
    - Red Herring
    - And many others...

    The agent provides detailed analysis and suggestions for improving argumentation.
    """

    FALLACY_CATEGORIES = {
        "relevance": [
            "ad hominem",
            "appeal to authority",
            "appeal to emotion",
            "bandwagon fallacy",
            "genetic fallacy",
            "red herring",
            "straw man",
            "tu quoque",
        ],
        "presumption": [
            "false cause",
            "hasty generalization",
            "slippery slope",
            "circular argument",
            "false dichotomy",
            "middle ground fallacy",
            "no true scotsman",
        ],
        "ambiguity": [
            "equivocation",
            "loaded question",
            "ambiguity",
            "composition/division",
        ],
        "induction": [
            "sampling bias",
            "gambler's fallacy",
            "post hoc fallacy",
            "correlation implies causation",
        ],
    }

    def __init__(self) -> None:
        """Initialize the logical fallacy detection agent."""
        functions = [
            FunctionDefinition(
                name="analyze_fallacies",
                description="Analyze text for logical fallacies and provide detailed analysis",
                parameters={
                    "detected_fallacies": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "fallacy_type": {"type": "string"},
                                "confidence": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                },
                                "text_segment": {"type": "string"},
                                "explanation": {"type": "string"},
                            },
                            "required": [
                                "fallacy_type",
                                "confidence",
                                "text_segment",
                                "explanation",
                            ],
                        },
                    },
                    "overall_reasoning_score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "major_concerns": {"type": "array", "items": {"type": "string"}},
                    "improvement_suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                required=[
                    "detected_fallacies",
                    "overall_reasoning_score",
                    "major_concerns",
                    "improvement_suggestions",
                ],
            ),
            FunctionDefinition(
                name="suggest_improvements",
                description="Generate suggestions for improving text with logical fallacies",
                parameters={
                    "suggestions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "original_text": {"type": "string"},
                                "improved_version": {"type": "string"},
                                "explanation": {"type": "string"},
                            },
                            "required": [
                                "original_text",
                                "improved_version",
                                "explanation",
                            ],
                        },
                    },
                },
                required=["suggestions"],
            ),
        ]
        super().__init__(
            task_type="logical_fallacy_detection",
            model="mixtral-8x7b",
            complexity=2,
            functions=functions,
        )

        # Load fallacy definitions and examples
        self.fallacy_definitions = self._load_fallacy_definitions()

    def _load_fallacy_definitions(self) -> dict[str, FallacyType]:
        """Load detailed definitions and examples for each fallacy type."""
        definitions = {}

        # Ad Hominem
        definitions["ad_hominem"] = FallacyType(
            name="Ad Hominem",
            description="Attacking the person instead of addressing their argument",
            example="You can't trust his economic policy because he's never had a real job.",
            category="relevance",
        )

        # Straw Man
        definitions["straw_man"] = FallacyType(
            name="Straw Man",
            description="Misrepresenting someone's argument to make it easier to attack",
            example="You want better healthcare? So you want complete government control of our lives!",
            category="relevance",
        )

        # False Dichotomy
        definitions["false_dichotomy"] = FallacyType(
            name="False Dichotomy",
            description="Presenting only two options when there are more alternatives",
            example="Either you support unlimited development or you're against economic growth.",
            category="presumption",
        )

        # Add more fallacy definitions...

        return definitions

    async def analyze_text(
        self,
        text: str,
        context: dict | None = None,
        metadata: dict | None = None,
    ) -> FallacyAnalysis:
        """Analyze text for logical fallacies."""
        try:
            # Prepare the prompt with fallacy guidelines
            prompt = self._construct_analysis_prompt(text, context)

            # Get model's analysis with JSON mode
            result = await self.run(
                prompt=prompt,
                metadata=metadata,
                result_type="fallacy_analysis",
                entity_type="text",
                entity_id=str(hash(text))[:8],
                response_format={"type": "json_object"},
            )

            # Parse and validate the analysis
            try:
                # Handle function call response
                if isinstance(result, dict):
                    if "function_call" in result:
                        args = json.loads(result["function_call"]["arguments"])
                        return self._normalize_fallacy_analysis(args)
                    # Direct dictionary response
                    return self._normalize_fallacy_analysis(result)
                # Handle string response
                if isinstance(result, str):
                    # Try to parse as JSON
                    try:
                        # First try direct JSON parsing
                        try:
                            result_dict = json.loads(result)
                            return self._normalize_fallacy_analysis(result_dict)
                        except json.JSONDecodeError:
                            pass

                        # If that fails, try to extract the first JSON object
                        start = result.find("{")
                        if start == -1:
                            msg = "No JSON object found in response"
                            raise ValueError(msg)

                        # Find matching closing brace
                        count = 1
                        end = start + 1
                        while count > 0 and end < len(result):
                            if result[end] == "{":
                                count += 1
                            elif result[end] == "}":
                                count -= 1
                            end += 1

                        if count > 0:
                            # If we hit the end without finding the closing brace,
                            # try to reconstruct a minimal valid JSON object
                            partial = result[start:]
                            if '"detected_fallacies"' in partial:
                                # Extract the fallacy details we can see
                                fallacy_type = None

                                if '"fallacy_type":' in partial:
                                    type_start = partial.find('"fallacy_type":') + 15
                                    type_end = partial.find('"', type_start + 1)
                                    if type_end > type_start:
                                        fallacy_type = partial[type_start:type_end]

                                if fallacy_type:
                                    # We found at least a fallacy type, construct a minimal response
                                    return self._normalize_fallacy_analysis(
                                        {
                                            "detected_fallacies": [
                                                {
                                                    "fallacy_type": fallacy_type,
                                                    "confidence": 0.9,  # Default high confidence
                                                    "text_segment": text,  # Use the whole text
                                                    "explanation": f"Detected {fallacy_type.lower()} fallacy",
                                                },
                                            ],
                                            "overall_reasoning_score": 0.4,  # Lower score due to fallacy
                                            "major_concerns": [
                                                f"Contains {fallacy_type.lower()} fallacy",
                                            ],
                                            "improvement_suggestions": [
                                                "Address the logical fallacy",
                                            ],
                                        },
                                    )

                        # If we can't reconstruct, raise the original error
                        msg = "Unclosed JSON object"
                        raise ValueError(msg)

                        json_str = result[start:end]
                        result_dict = json.loads(json_str)
                        return self._normalize_fallacy_analysis(result_dict)
                    except Exception as e:
                        logger.warning(
                            "fallacy_analysis_json_error",
                            error=str(e),
                            text_length=len(text),
                            result=result[:100],  # Log first 100 chars for debugging
                        )
                        # Return default analysis
                        return FallacyAnalysis(
                            detected_fallacies=[],
                            overall_reasoning_score=0.5,
                            major_concerns=["Error analyzing fallacies"],
                            improvement_suggestions=["Please try rephrasing the text"],
                        )
                else:
                    logger.warning(
                        "unexpected_result_type",
                        type=type(result).__name__,
                        text_length=len(text),
                    )
                    return FallacyAnalysis(
                        detected_fallacies=[],
                        overall_reasoning_score=0.5,
                        major_concerns=["Error analyzing fallacies"],
                        improvement_suggestions=["Please try rephrasing the text"],
                    )

            except Exception as e:
                # If parsing fails, create a minimal valid response
                logger.warning(
                    "fallacy_analysis_parse_error",
                    error=str(e),
                    text_length=len(text),
                )
                return FallacyAnalysis(
                    detected_fallacies=[],
                    overall_reasoning_score=0.5,
                    major_concerns=["Error analyzing fallacies"],
                    improvement_suggestions=["Please try rephrasing the text"],
                )

        except Exception as e:
            logger.exception(
                "Error analyzing text for fallacies",
                error=str(e),
                text_length=len(text),
            )
            raise

    def _normalize_fallacy_analysis(self, data: dict) -> FallacyAnalysis:
        """Normalize the fallacy analysis data to ensure consistent casing and formatting."""
        if "detected_fallacies" in data:
            for fallacy in data["detected_fallacies"]:
                if "fallacy_type" in fallacy:
                    # Convert to lowercase and normalize common variations
                    fallacy_type = fallacy["fallacy_type"].lower()
                    if (
                        "ad hominem" in fallacy_type
                        or "personal attack" in fallacy_type
                    ):
                        fallacy["fallacy_type"] = "ad hominem"
                    elif (
                        "false dichotomy" in fallacy_type
                        or "black and white" in fallacy_type
                    ):
                        fallacy["fallacy_type"] = "false dichotomy"
                    elif "slippery slope" in fallacy_type:
                        fallacy["fallacy_type"] = "slippery slope"
                    elif "straw man" in fallacy_type:
                        fallacy["fallacy_type"] = "straw man"
                    elif "appeal to authority" in fallacy_type:
                        fallacy["fallacy_type"] = "appeal to authority"
                    elif "bandwagon" in fallacy_type:
                        fallacy["fallacy_type"] = "bandwagon"
                    elif "red herring" in fallacy_type:
                        fallacy["fallacy_type"] = "red herring"
                    elif "hasty generalization" in fallacy_type:
                        fallacy["fallacy_type"] = "hasty generalization"
                    elif "post hoc" in fallacy_type:
                        fallacy["fallacy_type"] = "post hoc"
                    elif "appeal to emotion" in fallacy_type:
                        fallacy["fallacy_type"] = "appeal to emotion"
        return FallacyAnalysis(**data)

    def _construct_analysis_prompt(self, text: str, context: dict | None) -> str:
        """Construct the prompt for fallacy analysis."""
        prompt_parts = [
            "You are a logical fallacy detection expert. Your task is to analyze the following text for logical fallacies.",
            "You MUST respond with a valid JSON object containing your analysis.",
            "IMPORTANT: All property names and string values MUST be enclosed in double quotes.",
            "The response MUST follow this exact structure and format:",
            """{
                "detected_fallacies": [
                    {
                        "fallacy_type": "type of fallacy",
                        "confidence": 0.9,
                        "text_segment": "the specific text containing the fallacy",
                        "explanation": "explanation of why this is a fallacy"
                    }
                ],
                "overall_reasoning_score": 0.8,
                "major_concerns": ["list", "of", "concerns"],
                "improvement_suggestions": ["list", "of", "suggestions"]
            }""",
            "\nEnsure your response:",
            "1. Uses double quotes for ALL property names",
            "2. Uses double quotes for ALL string values",
            "3. Uses numbers (without quotes) for numeric values",
            "4. Follows the exact structure shown above",
            "\nCommon fallacy types to look for:",
            "- False Dichotomy (presenting only two extreme options when more alternatives exist)",
            "- Ad Hominem (attacking the person instead of their argument)",
            "- Straw Man (misrepresenting an opponent's position)",
            "- Appeal to Authority (using authority rather than logic)",
            "- Slippery Slope (claiming one event will trigger a chain of negative events)",
            "\nText to analyze:\n",
            text,
        ]

        if context:
            prompt_parts.extend(["\nAdditional context:", str(context)])

        return "\n".join(prompt_parts)

    async def get_fallacy_explanation(self, fallacy_type: str) -> FallacyType | None:
        """Get detailed explanation and examples for a specific fallacy type."""
        return self.fallacy_definitions.get(fallacy_type.lower().replace(" ", "_"))

    async def suggest_improvements(
        self,
        text: str,
        fallacies: list[FallacyInstance],
    ) -> list[str]:
        """Generate specific suggestions for improving arguments with detected fallacies."""
        try:
            prompt = f"""You are an expert in logical argumentation and technical communication.
            Your task is to provide specific suggestions for improving arguments that contain logical fallacies.
            You MUST respond with a JSON object containing your suggestions. The response should have this exact structure:

            {{
                "suggestions": [
                    {{
                        "original_text": "text with fallacy",
                        "improved_version": "suggested improvement",
                        "explanation": "why this addresses the fallacy"
                    }}
                ]
            }}

            Original text with fallacies:
            {text}

            Detected fallacies:
            {json.dumps([f.model_dump() for f in fallacies], indent=2)}

            Focus on:
            1. Technical solutions and best practices
            2. Concrete implementation details
            3. Error handling and edge cases
            4. Validation and verification
            5. Clear, objective communication

            Your suggestions should:
            - Address the technical aspects first
            - Include specific implementation details
            - Focus on validation and error handling
            - Use objective, factual language
            - Avoid personal criticism"""

            result = await self.run(
                prompt=prompt,
                metadata={"fallacy_count": len(fallacies)},
                result_type="improvement_suggestions",
                entity_type="fallacy",
                entity_id=str(hash(text))[:8],
                response_format={"type": "json_object"},
            )

            # Parse and validate the suggestions
            try:
                # Handle function call response
                if isinstance(result, dict):
                    if "function_call" in result:
                        args = json.loads(result["function_call"]["arguments"])
                        return [s["improved_version"] for s in args["suggestions"]]
                    # Direct dictionary response
                    return [s["improved_version"] for s in result["suggestions"]]
                # Handle string response
                if isinstance(result, str):
                    # Try to parse as JSON
                    try:
                        result_dict = json.loads(result)
                        return [
                            s["improved_version"] for s in result_dict["suggestions"]
                        ]
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "suggestion_json_error",
                            error=str(e),
                            fallacy_count=len(fallacies),
                            result=result[:100],  # Log first 100 chars for debugging
                        )
                        return []
                else:
                    logger.warning(
                        "unexpected_suggestion_result_type",
                        type=type(result).__name__,
                        fallacy_count=len(fallacies),
                    )
                    return []

            except Exception as e:
                logger.warning(
                    "suggestion_parse_error",
                    error=str(e),
                    fallacy_count=len(fallacies),
                )
                return []

        except Exception as e:
            logger.exception(
                "Error generating improvement suggestions",
                error=str(e),
                fallacy_count=len(fallacies),
            )
            return []
