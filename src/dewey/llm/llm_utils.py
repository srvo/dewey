"""Utilities for working with LLMs across the Dewey system."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, List, Union

import structlog
from smolagents import CodeAgent, HfApiModel, LiteLLMModel

from dewey.core.base_script import BaseScript
from dewey.llm.api_clients.deepinfra import DeepInfraClient
from dewey.llm.api_clients.gemini import GeminiClient
from dewey.llm.exceptions import LLMError

logger = structlog.get_logger(__name__)


class LLMHandler:
    """Centralized handler for LLM client configuration and execution."""

    def __init__(self, config: dict) -> None:
        """
        Initialize the LLM Handler with configuration.
        
        Args:
            config (dict): Configuration dictionary for the LLM client
        """
        self.config = config
        self.client = None
        self.usage_stats = {"requests": 0, "tokens": 0}
        self._init_client()

    def _init_client(self) -> None:
        """Initialize the appropriate LLM client based on configuration."""
        client_type = self.config.get("client", "gemini")
        try:
            if client_type == "gemini":
                self.client = GeminiClient(config=self.config)
            elif client_type == "deepinfra":
                self.client = DeepInfraClient(api_key=self.config.get("api_key"))
            elif client_type == "smolagents":
                # Initialize smolagents client option
                api_key = self.config.get("api_key") or os.environ.get("DEEPINFRA_API_KEY")
                model_name = self.config.get("model_name", "Qwen/Qwen2.5-Coder-32B-Instruct")
                if model_name.startswith("HF:"):
                    self.client = HfApiModel(
                        model_id=model_name[3:],
                        temperature=self.config.get("temperature", 0.3),
                        max_tokens=self.config.get("max_tokens", 4096)
                    )
                else:
                    self.client = LiteLLMModel(
                        model_id=model_name,
                        api_key=api_key,
                        temperature=self.config.get("temperature", 0.3),
                        max_tokens=self.config.get("max_tokens", 4096)
                    )
            else:
                msg = f"Unsupported LLM client: {client_type}"
                raise LLMError(msg)
        except Exception as e:
            msg = f"Failed to initialize {client_type} client: {e!s}"
            raise LLMError(msg)

    def generate_response(
        self, prompt: str, fallback_model: str | None = None, **kwargs
    ) -> str:
        """
        Unified interface for generating responses with fallback support.
        
        Args:
            prompt (str): The prompt to send to the LLM
            fallback_model (str, optional): Fallback model to use if primary fails. Defaults to None.
            **kwargs: Additional parameters for the LLM client
            
        Returns:
            str: The generated response text
            
        Raises:
            LLMError: If generation fails
        """
        if not self.client:
            msg = "LLM client not initialized"
            raise LLMError(msg)

        # Client-specific parameter handling
        params = {
            "temperature": self.config.get("temperature", 0.7),
            "fallback_model": fallback_model,
        }

        if isinstance(self.client, GeminiClient):
            params.update(
                {
                    "model": self.config.get("default_model", "gemini-2.0-flash"),
                    "max_output_tokens": kwargs.get("max_tokens", 1000),
                },
            )
        elif isinstance(self.client, DeepInfraClient):
            params.update(
                {
                    "model": self.config.get(
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
                logger.warning(
                    f"Primary model failed, trying fallback: {params['fallback_model']}"
                )
                try:
                    # Switch to DeepInfra client for fallback
                    from dewey.llm.api_clients.deepinfra import DeepInfraClient

                    fallback_client = DeepInfraClient(
                        api_key=self.config.get("deepinfra_api_key")
                    )
                    return fallback_client.chat_completion(
                        prompt,
                        model=params["fallback_model"],
                        temperature=kwargs.get("temperature", 0.7),
                        max_tokens=kwargs.get("max_tokens", 1000),
                    )
                except Exception as fallback_error:
                    logger.exception(f"Fallback LLM failed: {fallback_error}")
                    msg = f"Both primary and fallback LLMs failed: {primary_error}, {fallback_error}"
                    raise LLMError(msg)
            msg = f"Generation failed: {primary_error}"
            raise LLMError(msg) from primary_error


def validate_model_params(params: dict[str, Any]) -> None:
    """
    Validate parameters for LLM model calls.

    Args:
        params: Dictionary of parameters to validate

    Raises:
        ValueError: If any parameters are invalid
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
        config (Dict[str, Any]): Configuration parameters
        
    Returns:
        Union[HfApiModel, LiteLLMModel]: Configured model
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
    
    def __init__(self, config_section: str = "llm"):
        """
        Initialize the LLM utilities manager.
        
        Args:
            config_section (str, optional): Configuration section. Defaults to "llm".
        """
        super().__init__(config_section=config_section)
        self.llm_handler = LLMHandler(self.config)
        
    def run(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a sample LLM call.
        
        Args:
            input_data (Optional[Dict[str, Any]], optional): Input data. Defaults to None.
            
        Returns:
            Dict[str, Any]: Results
        """
        prompt = "Hello world"
        if input_data and "prompt" in input_data:
            prompt = input_data["prompt"]
            
        response = self.llm_handler.generate_response(prompt)
        return {"response": response}