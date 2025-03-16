"""Base configuration for agents with DeepInfra integration."""
from __future__ import annotations

import time
from typing import Any, List, Dict, Optional

import httpx
import sentry_sdk
import structlog
from asgiref.sync import sync_to_async
from django.db import transaction
from pydantic import BaseModel, Field
from ulid import ULID
from smolagents import Agent, Tool

from ..models.metrics import AgentInteraction
from .config import AIConfig

logger = structlog.get_logger(__name__)


class FunctionDefinition(BaseModel):
    """Definition of a function that can be called by the model."""

    name: str
    description: str
    parameters: dict[str, Any]
    required: list[str] = Field(default_factory=list)


class DeweyBaseAgent(Agent):
    """Base class for AI agents using DeepInfra.

    Features include:
        - Automatic model selection based on task complexity
        - Function calling support
        - Comprehensive metrics tracking
        - Cost estimation and monitoring
        - Sentry error reporting
        - Configurable retries and timeouts
    """

    def __init__(
        self,
        task_type: str | None = None,
        model: str | None = None,
        complexity: int = 0,
        tools: List[Tool] | None = None,
    ) -> None:
        """Initialize the agent with configuration.

        Args:
            task_type (str, optional): Type of task for automatic model selection. Defaults to None.
            model (str, optional): Override model selection (optional). Defaults to None.
            complexity (int, optional): Task complexity level (0-2). Defaults to 0.
            tools (List[Tool], optional): List of available tools (optional). Defaults to None.
        """
        super().__init__(tools=tools)
        self.logger = logger.bind(component=self.__class__.__name__)
        self.task_type = task_type or self.__class__.__name__.lower()
        self.functions = []  # Keeping this for compatibility, but it's not used by smolagents

        # Get model configuration
        if model:
            # Check all model tiers
            for tier in [
                AIConfig.BASIC_MODELS,
                AIConfig.STANDARD_MODELS,
                AIConfig.PREMIUM_MODELS,
                AIConfig.TECHNICAL_MODELS,
            ]:
                if model in tier:
                    self.model_config = tier[model]
                    break
            else:
                # If model not found in any tier, use fallback
                self.logger.warning(
                    "model_not_found_using_fallback",
                    model=model,
                    fallback="mistral-7b-instruct",
                )
                self.model_config = AIConfig.BASIC_MODELS["mistral-7b-instruct"]
        else:
            self.model_config = AIConfig.get_model_for_task(self.task_type, complexity)

        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            base_url="https://api.deepinfra.com/v1/openai",
            timeout=60.0,
        )

        self.logger.info(
            "agent_initialized",
            task_type=self.task_type,
            model=self.model_config.name,
            endpoint=self.model_config.endpoint,
            tier=self.model_config.tier.value,
            functions_enabled=bool(self.functions),
        )

    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent.

        Override this in subclasses to provide specific prompts.

        Returns:
            str: The system prompt.
        """
        return "You are a helpful AI assistant in the Syzygy system."

    @sync_to_async
    def _create_interaction(self, **kwargs) -> AgentInteraction:
        """Create an interaction record in the database.

        Args:
            **kwargs: Keyword arguments to create the AgentInteraction object.

        Returns:
            AgentInteraction: The created AgentInteraction object.
        """
        with transaction.atomic():
            kwargs["id"] = str(ULID())
            return AgentInteraction.objects.create(**kwargs)

    @sync_to_async
    def _update_interaction(self, interaction: AgentInteraction, **kwargs) -> None:
        """Update an interaction record in the database.

        Args:
            interaction (AgentInteraction): The AgentInteraction object to update.
            **kwargs: Keyword arguments to update the AgentInteraction object.
        """
        with transaction.atomic():
            for key, value in kwargs.items():
                setattr(interaction, key, value)
            interaction.save()

    async def run(
        self,
        prompt: str,
        result_type: Any | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        metadata: dict | None = None,
        **kwargs,
    ):
        """Run the agent with comprehensive monitoring.

        Args:
            prompt (str): The prompt to send to the model.
            result_type (Any, optional): Expected result type (optional). Defaults to None.
            entity_type (str, optional): Type of entity being processed (optional). Defaults to None.
            entity_id (str, optional): ID of entity being processed (optional). Defaults to None.
            metadata (dict, optional): Additional context and metadata (optional). Defaults to None.
            **kwargs: Additional arguments for the agent.

        Returns:
            Any: Agent response.

        Raises:
            Exception: If the agent run fails.
        """
        start_time = time.time()
        interaction = None

        try:
            # Create interaction record
            interaction = await self._create_interaction(
                agent_type=self.task_type,
                model_name=self.model_config.name,
                provider=self.model_config.provider.value,
                operation=kwargs.get("operation", "run"),
                prompt_tokens=0,  # Will update after completion
                completion_tokens=0,
                latency_ms=0,
                success=False,
                cost_millicents=0,
                entity_type=entity_type or "unknown",
                entity_id=entity_id or "unknown",
                metadata=metadata or {},
            )

            # Prepare request payload
            payload = {
                "model": self.model_config.endpoint,
                "messages": [
                    {"role": "system", "content": self.get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            }

            # Add function calling if available
            # Smolagents handles tools differently, so this is not needed
            # if self.functions:
            #     payload["functions"] = [
            #         {
            #             "name": f.name,
            #             "description": f.description,
            #             "parameters": {
            #                 "type": "object",
            #                 "properties": f.parameters,
            #                 "required": f.required,
            #             },
            #         }
            #         for f in self.functions
            #     ]

            # Make API call
            response = await self.client.post(
                "/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self._get_api_key()}"},
            )
            response.raise_for_status()
            result = response.json()

            # Process response
            message = result["choices"][0]["message"]

            # Handle function calls
            if message.get("function_call"):
                function_call = message["function_call"]
                self.logger.info(
                    "function_call_requested",
                    function=function_call["name"],
                    arguments=function_call["arguments"],
                )
                # Note: Function execution would be implemented by subclasses

            # Update metrics
            elapsed_ms = int((time.time() - start_time) * 1000)
            usage = result.get("usage", {})

            await self._update_interaction(
                interaction,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                latency_ms=elapsed_ms,
                success=True,
                cost_millicents=AIConfig.estimate_cost(
                    self.model_config,
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                ),
            )

            # Log success
            self.logger.info(
                "agent_run_success",
                interaction_id=interaction.id,
                latency_ms=elapsed_ms,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                cost_millicents=interaction.cost_millicents,
                function_call=bool(message.get("function_call")),
            )

            return message["content"] if not message.get("function_call") else message

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)

            # Update interaction record
            if interaction:
                await self._update_interaction(
                    interaction,
                    latency_ms=elapsed_ms,
                    success=False,
                    error_type=e.__class__.__name__,
                    error_message=str(e),
                )

            # Log error
            self.logger.error(
                "agent_run_failed",
                error=str(e),
                latency_ms=elapsed_ms,
                exc_info=True,
            )

            # Report to Sentry
            sentry_sdk.capture_exception(e)

            raise

    def _get_api_key(self) -> str:
        """Get the DeepInfra API key from environment variables.

        Returns:
            str: The DeepInfra API key.

        Raises:
            ValueError: If the DEEPINFRA_API_KEY environment variable is not set.
        """
        import os

        api_key = os.getenv("DEEPINFRA_API_KEY")
        if not api_key:
            self.logger.error("DEEPINFRA_API_KEY not set")
            msg = "DEEPINFRA_API_KEY environment variable not set"
            raise ValueError(msg)
        return api_key
