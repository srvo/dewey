"""Configuration management for AI models and agents."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class ModelTier(Enum):
    """Classification of models by capability and cost."""

    BASIC = "basic"  # Fast, cheap models for simple tasks
    STANDARD = "standard"  # Good balance of performance and cost
    PREMIUM = "premium"  # High-capability models for complex tasks
    TECHNICAL = "technical"  # Specialized models for technical tasks
    CODE = "code"  # Models optimized for code-related tasks


class ModelProvider(Enum):
    """Supported model providers."""

    DEEPINFRA = "deepinfra"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""

    name: str
    provider: ModelProvider
    tier: ModelTier
    description: str
    endpoint: str  # DeepInfra API endpoint

    # Cost in millicents per 1K tokens
    input_cost: int
    output_cost: int

    # Performance characteristics
    typical_latency_ms: int
    max_input_tokens: int
    max_output_tokens: int

    # Whether prompts can be used for training
    allows_training: bool = False

    # Optional provider-specific settings
    provider_settings: dict = None


class AIConfig:
    """Central configuration for AI models and agents."""

    # Basic tier models
    BASIC_MODELS = {
        "mistral-7b-instruct": ModelConfig(
            name="mistral-7b-instruct",
            provider=ModelProvider.DEEPINFRA,
            tier=ModelTier.BASIC,
            description="Basic triage and classification tasks",
            endpoint="mistralai/Mistral-7B-Instruct-v0.1",
            input_cost=50,  # Example cost
            output_cost=100,
            typical_latency_ms=200,
            max_input_tokens=4096,
            max_output_tokens=4096,
            allows_training=False,
        ),
        "phi-4": ModelConfig(
            name="phi-4",
            provider=ModelProvider.DEEPINFRA,
            tier=ModelTier.BASIC,
            description="Simple text completion tasks",
            endpoint="microsoft/phi-2",
            input_cost=30,
            output_cost=60,
            typical_latency_ms=150,
            max_input_tokens=2048,
            max_output_tokens=2048,
            allows_training=False,
        ),
    }

    # Standard tier models
    STANDARD_MODELS = {
        "mixtral-8x7b": ModelConfig(
            name="mixtral-8x7b",
            provider=ModelProvider.DEEPINFRA,
            tier=ModelTier.STANDARD,
            description="Enhanced capabilities for medium complexity tasks",
            endpoint="mistralai/Mixtral-8x7B-Instruct-v0.1",
            input_cost=200,
            output_cost=400,
            typical_latency_ms=500,
            max_input_tokens=8192,
            max_output_tokens=4096,
            allows_training=False,
        ),
        "wizardlm-2": ModelConfig(
            name="wizardlm-2",
            provider=ModelProvider.DEEPINFRA,
            tier=ModelTier.STANDARD,
            description="Complex text-only tasks",
            endpoint="WizardLM/WizardLM-70B-V1.0",
            input_cost=300,
            output_cost=600,
            typical_latency_ms=600,
            max_input_tokens=8192,
            max_output_tokens=4096,
            allows_training=False,
        ),
    }

    # Premium tier models
    PREMIUM_MODELS = {
        "llama-3-nemotron": ModelConfig(
            name="llama-3-nemotron",
            provider=ModelProvider.DEEPINFRA,
            tier=ModelTier.PREMIUM,
            description="High complexity tasks requiring deep understanding",
            endpoint="NousResearch/Nous-Hermes-2-Yi-34B",
            input_cost=800,
            output_cost=1600,
            typical_latency_ms=1000,
            max_input_tokens=8192,
            max_output_tokens=4096,
            allows_training=False,
        ),
        "llama-3-meta": ModelConfig(
            name="llama-3-meta",
            provider=ModelProvider.DEEPINFRA,
            tier=ModelTier.PREMIUM,
            description="Most complex tasks requiring extensive reasoning",
            endpoint="meta-llama/Llama-2-70b-chat-hf",
            input_cost=1500,
            output_cost=3000,
            typical_latency_ms=1500,
            max_input_tokens=16384,
            max_output_tokens=8192,
            allows_training=False,
        ),
    }

    # Technical/Code models
    TECHNICAL_MODELS = {
        "qwen-coder": ModelConfig(
            name="qwen-coder",
            provider=ModelProvider.DEEPINFRA,
            tier=ModelTier.CODE,
            description="Specialized for code and technical tasks",
            endpoint="Qwen/Qwen-14B",
            input_cost=400,
            output_cost=800,
            typical_latency_ms=800,
            max_input_tokens=8192,
            max_output_tokens=4096,
            allows_training=False,
        ),
    }

    # Task-specific model assignments with escalation paths
    TASK_MODELS = {
        # Contact operations with escalation
        "contact_merge": ["mistral-7b-instruct", "mixtral-8x7b", "llama-3-nemotron"],
        "contact_category": ["mistral-7b-instruct", "mixtral-8x7b"],
        "contact_enrich": ["mixtral-8x7b", "llama-3-nemotron"],
        # Email operations with escalation
        "email_priority": ["mistral-7b-instruct", "mixtral-8x7b"],
        "email_analyze": ["mixtral-8x7b", "llama-3-meta"],
        "email_sensitive": [
            "llama-3-meta",
        ],  # Always use highest tier for sensitive content
        # Technical operations
        "code_analysis": ["qwen-coder"],
        "technical_doc": ["qwen-coder", "llama-3-meta"],
        # Basic operations
        "text_completion": ["phi-4", "mistral-7b-instruct"],
    }

    @classmethod
    def get_model_for_task(
        cls,
        task: str,
        complexity: int = 0,  # 0: basic, 1: medium, 2: high
        fallback: str = "mistral-7b-instruct",
    ) -> ModelConfig:
        """Get the appropriate model configuration for a task based on complexity.

        Args:
        ----
            task: The task identifier
            complexity: Task complexity level (0-2)
            fallback: Fallback model if task not found

        Returns:
        -------
            ModelConfig for the task

        """
        models = cls.TASK_MODELS.get(task, [fallback])

        # Select model based on complexity
        model_index = min(complexity, len(models) - 1)
        model_name = models[model_index]

        # Find model in tiers
        for tier in [
            cls.BASIC_MODELS,
            cls.STANDARD_MODELS,
            cls.PREMIUM_MODELS,
            cls.TECHNICAL_MODELS,
        ]:
            if model_name in tier:
                return tier[model_name]

        # If not found, return fallback model
        logger.warning(
            "model_not_found_using_fallback",
            task=task,
            complexity=complexity,
            requested_model=model_name,
            fallback=fallback,
        )
        return cls.BASIC_MODELS[fallback]

    @classmethod
    def estimate_cost(
        cls,
        model: ModelConfig,
        input_tokens: int,
        output_tokens: int | None = None,
    ) -> int:
        """Estimate cost in millicents for a model operation.

        Args:
        ----
            model: Model configuration
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens (if known)

        Returns:
        -------
            Estimated cost in millicents

        """
        cost = (input_tokens * model.input_cost) // 1000  # Cost per 1K tokens

        if output_tokens:
            cost += (output_tokens * model.output_cost) // 1000

        return cost
