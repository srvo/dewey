from __future__ import annotations

import logging
from typing import Any
import json

from dewey.llm.api_clients.deepinfra import DeepInfraClient
from dewey.llm.api_clients.gemini import GeminiClient
from dewey.llm.exceptions import LLMError

logger = logging.getLogger(__name__)


class LLMHandler:
    """Centralized handler for LLM client configuration and execution."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.client = None
        self.usage_stats = {"requests": 0, "tokens": 0}
        self._init_client()

    def _init_client(self) -> None:
        client_type = self.config.get("client", "gemini")
        try:
            if client_type == "gemini":
                self.client = GeminiClient(config=self.config)
            elif client_type == "deepinfra":
                self.client = DeepInfraClient(api_key=self.config.get("api_key"))
            else:
                msg = f"Unsupported LLM client: {client_type}"
                raise LLMError(msg)
        except Exception as e:
            msg = f"Failed to initialize {client_type} client: {e!s}"
            raise LLMError(msg)

    def generate_response(
        self, prompt: str, fallback_model: str | None = None, **kwargs
    ) -> str:
        """Unified interface for generating responses with fallback support."""
        if not self.client:
            msg = "LLM client not initialized"
            raise LLMError(msg)

        try:
            self.usage_stats["requests"] += 1
            
            # Handle client-specific parameters
            if isinstance(self.client, GeminiClient):
                # Gemini uses max_output_tokens instead of max_tokens
                params = {
                    "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
                    "model": kwargs.get("model", self.config.get("default_model", "gemini-2.0-flash-lite")),
                }
                
                # Only add max_output_tokens if specified
                if "max_tokens" in kwargs:
                    params["max_output_tokens"] = kwargs["max_tokens"]
                
                # For Gemini, we'll handle JSON formatting in the prompt
                if kwargs.get("response_format"):
                    # Create a more explicit JSON instruction
                    json_format = str(kwargs["response_format"]).replace("'", '"')
                    prompt = f"""IMPORTANT: Your response must be a valid JSON object.
Format: {json_format}

DO NOT include any markdown formatting, code blocks, or other text - ONLY the raw JSON object.

{prompt}"""
                
                response = self.client.generate_content(prompt, **params)
                
                # For Gemini, we need to extract the text
                if hasattr(response, "text"):
                    response = response.text.strip()
                    
                    # Try to clean up any markdown formatting that might have been added
                    if response.startswith("```json\n"):
                        response = response[8:]  # Remove ```json\n
                    elif response.startswith("```\n"):
                        response = response[4:]  # Remove ```\n
                    elif response.startswith("```"):
                        response = response[3:]  # Remove ```
                        
                    if response.endswith("\n```"):
                        response = response[:-4]  # Remove \n```
                    elif response.endswith("```"):
                        response = response[:-3]  # Remove ```
                    
                    # Clean up any remaining markdown or whitespace
                    response = response.strip()
                    
                    # If we're expecting JSON, try to validate it
                    if kwargs.get("response_format"):
                        try:
                            # Test if it's valid JSON
                            json.loads(response)
                        except json.JSONDecodeError:
                            # If not, try to find JSON-like content
                            start = response.find('{')
                            end = response.rfind('}') + 1
                            if start >= 0 and end > start:
                                response = response[start:end]
                                # Try to validate the extracted JSON
                                try:
                                    json.loads(response)
                                except json.JSONDecodeError:
                                    logger.warning("Failed to extract valid JSON from response")
                
            elif isinstance(self.client, DeepInfraClient):
                params = {
                    "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
                    "max_tokens": kwargs.get("max_tokens", 1000),
                }
                # Add system message for JSON format if needed
                if kwargs.get("response_format"):
                    params["system_message"] = "You must respond with a valid JSON object. No other text or formatting."
                response = self.client.chat_completion(prompt, **params)

            # Track token usage if available
            if hasattr(response, "usage"):
                self.usage_stats["tokens"] += response.usage.total_tokens
            
            # Ensure we return a string
            if isinstance(response, str):
                return response.strip()
            elif hasattr(response, "text"):
                return response.text.strip()
            else:
                return str(response).strip()
                
        except Exception as primary_error:
            if fallback_model:
                logger.warning(
                    f"Primary model failed, trying fallback: {fallback_model}"
                )
                try:
                    # Switch to DeepInfra client for fallback
                    fallback_client = DeepInfraClient(
                        api_key=self.config.get("deepinfra_api_key")
                    )
                    return fallback_client.chat_completion(
                        prompt,
                        model=fallback_model,
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
    """Validate parameters for LLM model calls.

    Args:
    ----
        params: Dictionary of parameters to validate

    Raises:
    ------
        ValueError: If any parameters are invalid

    """
    if "temperature" in params and not 0 <= params["temperature"] <= 2:
        msg = "Temperature must be between 0 and 2"
        raise ValueError(msg)
    if "max_tokens" in params and params["max_tokens"] <= 0:
        msg = "max_tokens must be positive integer"
        raise ValueError(msg)
