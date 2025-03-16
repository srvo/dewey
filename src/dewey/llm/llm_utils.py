from typing import Any

from dewey.llm.api_clients.deepinfra import DeepInfraClient
from dewey.llm.api_clients.gemini import GeminiClient
from dewey.llm.exceptions import LLMError


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

    def generate_response(self, prompt: str, **kwargs) -> str:
        """Unified interface for generating responses."""
        if not self.client:
            msg = "LLM client not initialized"
            raise LLMError(msg)

        # Client-specific parameter handling
        params = {"temperature": self.config.get("temperature", 0.7)}

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

        params.update(kwargs)

        try:
            self.usage_stats["requests"] += 1
            if isinstance(self.client, GeminiClient):
                response = self.client.generate_content(prompt, **params)
            elif isinstance(self.client, DeepInfraClient):
                response = self.client.chat_completion(prompt, **params)

            # Track token usage if available
            if hasattr(response, "usage"):
                self.usage_stats["tokens"] += response.usage.total_tokens
            return response
        except Exception as e:
            msg = f"Generation failed: {e!s}"
            raise LLMError(msg)


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
