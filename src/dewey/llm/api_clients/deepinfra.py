import os

from dewey.llm.exceptions import LLMError
from openai import OpenAI


class DeepInfraClient:
    """Client for interacting with DeepInfra's OpenAI-compatible API."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize DeepInfra client.

        Args:
        ----
            api_key: Optional DeepInfra API key. If not provided, will attempt
                to read from DEEPINFRA_API_KEY environment variable.

        """
        self.api_key = api_key or os.getenv("DEEPINFRA_API_KEY")
        if not self.api_key:
            msg = "DeepInfra API key not found. Set DEEPINFRA_API_KEY environment variable."
            raise LLMError(
                msg,
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepinfra.com/v1/openai",
        )

    def chat_completion(
        self,
        prompt: str,
        model: str = "meta-llama/Meta-Llama-3-8B-Instruct",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        system_message: str | None = None,
        **kwargs,
    ) -> str:
        """Generate a chat completion response from DeepInfra.

        Args:
        ----
            prompt: User input prompt
            model: Model identifier string
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            system_message: Optional system message to guide model behavior
            **kwargs: Additional parameters for completion

        Returns:
        -------
            Generated text content

        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content
        except Exception as e:
            msg = f"DeepInfra API error: {e!s}"
            raise LLMError(msg) from e

    def stream_completion(self, **kwargs) -> str:
        """Streaming version of chat completion (not yet implemented)."""
        msg = "Streaming completion not implemented yet"
        raise NotImplementedError(msg)
