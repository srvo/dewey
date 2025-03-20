"""Utilities for working with LLMs across the Dewey system."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, List, Union

from smolagents import CodeAgent, HfApiModel, LiteLLMModel

from dewey.core.base_script import BaseScript
from dewey.llm.api_clients.deepinfra import DeepInfraClient
from dewey.llm.api_clients.gemini import GeminiClient
from dewey.llm.exceptions import LLMError


class LLMHandler(BaseScript):
    """Centralized handler for LLM client configuration and execution."""

    def __init__(self, config_section: str = "llm") -> None:
        """
        Initialize the LLM Handler with configuration.

        Args:
            config_section: Configuration section name. Defaults to "llm".
        """
        super().__init__(config_section=config_section)
        self.client = None
        self.usage_stats: Dict[str, int] = {"requests": 0, "tokens": 0}
        self._init_client()

    def _init_client(self) -> None:
        """Initialize the appropriate LLM client based on configuration."""
        client_type = self.get_config_value("client", "gemini")
        try:
            if client_type == "gemini":
                self.client = GeminiClient(config=self.config)
            elif client_type == "deepinfra":
                api_key = self.get_config_value("api_key")
                self.client = DeepInfraClient(api_key=api_key)
            elif client_type == "smolagents":
                # Initialize smolagents client option
                api_key = self.get_config_value("api_key") or os.environ.get("DEEPINFRA_API_KEY")
                model_name = self.get_config_value("model_name", "Qwen/Qwen2.5-Coder-32B-Instruct")
                temperature = self.get_config_value("temperature", 0.3)
                max_tokens = self.get_config_value("max_tokens", 4096)
                if model_name.startswith("HF:"):
                    self.client = HfApiModel(
                        model_id=model_name[3:],
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                else:
                    self.client = LiteLLMModel(
                        model_id=model_name,
                        api_key=api_key,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
            else:
                msg = f"Unsupported LLM client: {client_type}"
                raise LLMError(msg)
        except Exception as e:
            msg = f"Failed to initialize {client_type} client: {e!s}"
            raise LLMError(msg)

    def generate_response(
        self, prompt: str, fallback_model: str | None = None, **kwargs: Any
    ) -> str:
        """
        Unified interface for generating responses with fallback support.

        Args:
            prompt: The prompt to send to the LLM.
            fallback_model: Fallback model to use if primary fails. Defaults to None.
            **kwargs: Additional parameters for the LLM client.

        Returns:
            The generated response text.

        Raises:
            LLMError: If generation fails.
        """
        if not self.client:
            msg = "LLM client not initialized"
            raise LLMError(msg)

        # Client-specific parameter handling
        params: Dict[str, Any] = {
            "temperature": self.get_config_value("temperature", 0.7),
            "fallback_model": fallback_model,
        }

        if isinstance(self.client, GeminiClient):
            params.update(
                {
                    "model": self.get_config_value("default_model", "gemini-2.0-flash"),
                    "max_output_tokens": kwargs.get("max_tokens", 1000),
                },
            )
        elif isinstance(self.client, DeepInfraClient):
            params.update(
                {
                    "model": self.get_config_value(
                        "default_model",
                        "meta-llama/Meta-Llama-3-8B-Instruct",
                    ),
                    "max_tokens": kwargs.get("max_tokens", 1000),
                },
            )
        elif isinstance(self.client, (HfApiModel, LiteLLMModel)):
            # We handle smolagents models differently - they're initialized with params already
            pass

        params.update(kwargs)

        try:
            self.usage_stats["requests"] += 1
            if isinstance(self.client, GeminiClient):
                response = self.client.generate_content(prompt, **params)
            elif isinstance(self.client, DeepInfraClient):
                response = self.client.chat_completion(prompt, **params)
            elif isinstance(self.client, (HfApiModel, LiteLLMModel)):
                # Use smolagents model directly
                response = self.client(prompt)

            # Track token usage if available
            if hasattr(response, "usage"):
                self.usage_stats["tokens"] += response.usage.total_tokens
            return response
        except Exception as primary_error:
            if params.get("fallback_model"):
                self.logger.warning(
                    f"Primary model failed, trying fallback: {params['fallback_model']}"
                )
                try:
                    # Switch to DeepInfra client for fallback
                    from dewey.llm.api_clients.deepinfra import DeepInfraClient

                    fallback_client = DeepInfraClient(
                        api_key=self.get_config_value("deepinfra_api_key")
                    )
                    return fallback_client.chat_completion(
                        prompt,
                        model=params["fallback_model"],
                        temperature=kwargs.get("temperature", 0.7),
                        max_tokens=kwargs.get("max_tokens", 1000),
                    )
                except Exception as fallback_error:
                    self.logger.exception(f"Fallback LLM failed: {fallback_error}")
                    msg = f"Both primary and fallback LLMs failed: {primary_error}, {fallback_error}"
                    raise LLMError(msg)
            msg = f"Generation failed: {primary_error}"
            raise LLMError(msg) from primary_error

    def run(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a sample LLM call.

        Args:
            input_data: Input data. Defaults to None.

        Returns:
            Results.
        """
        prompt = "Hello world"
        if input_data and "prompt" in input_data:
            prompt = input_data["prompt"]

        response = self.generate_response(prompt)
        return {"response": response}


def validate_model_params(params: Dict[str, Any]) -> None:
    """
    Validate parameters for LLM model calls.

    Args:
        params: Dictionary of parameters to validate.

    Raises:
        ValueError: If any parameters are invalid.
    """
    if "temperature" in params and not 0 <= params["temperature"] <= 2:
        msg = "Temperature must be between 0 and 2"
        raise ValueError(msg)
    if "max_tokens" in params and params["max_tokens"] <= 0:
        msg = "max_tokens must be positive integer"
        raise ValueError(msg)


def create_smolagents_model(config: Dict[str, Any]) -> Union[HfApiModel, LiteLLMModel]:
    """
    Create a smolagents model based on configuration.

    Args:
        config: Configuration parameters.

    Returns:
        Configured model.
    """
    api_key = config.get("api_key") or os.environ.get("DEEPINFRA_API_KEY")
    model_name = config.get("model_name", "Qwen/Qwen2.5-Coder-32B-Instruct")
    temperature = config.get("temperature", 0.3)
    max_tokens = config.get("max_tokens", 4096)

    if model_name.startswith("HF:"):
        return HfApiModel(
            model_id=model_name[3:],
            temperature=temperature,
            max_tokens=max_tokens
        )
    else:
        return LiteLLMModel(
            model_id=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens
        )


class LLMUtilsManager(BaseScript):
    """BaseScript-compatible manager for LLM utilities."""

    def __init__(self, config_section: str = "llm") -> None:
        """
        Initialize the LLM utilities manager.

        Args:
            config_section: Configuration section. Defaults to "llm".
        """
        super().__init__(config_section=config_section)
        self.llm_handler = LLMHandler(config_section=config_section)

    def run(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a sample LLM call.

        Args:
            input_data: Input data. Defaults to None.

        Returns:
            Results.
        """
        prompt = "Hello world"
        if input_data and "prompt" in input_data:
            prompt = input_data["prompt"]

        response = self.llm_handler.generate_response(prompt)
        return {"response": response}
