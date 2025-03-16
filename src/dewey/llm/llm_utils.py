import logging
from typing import Any

from dewey.llm.api_clients.deepinfra import DeepInfraClient
from dewey.llm.exceptions import LLMError


def generate_response(
    prompt: str,
    model: str = "gemini-2.0-flash",
    temperature: float = 0.7,
    system_message: str | None = None,
    api_key: str | None = None,
    fallback_client: Any | None = None,
) -> str:
    """Generate a response from the specified LLM model.

    Args:
    ----
        prompt: Input text prompt
        model: Model identifier (default: Meta-Llama-3-8B-Instruct)
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum number of tokens to generate
        system_message: Optional system message for chat models
        api_key: Optional API key override

    Returns:
    -------
        Generated text response

    Raises:
    ------
        LLMError: If there's an error during generation

    """
    try:
        client = DeepInfraClient(api_key=api_key)
        # Prepend system message to prompt if provided
        full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt

        return client.generate_content(
            prompt=full_prompt,
            model=model,
            temperature=temperature,
        )
    except Exception as e:
        if fallback_client and "exhausted" in str(e).lower():
            try:
                logging.warning("Gemini API exhausted, falling back to DeepInfra")
                return fallback_client.chat_completion(
                    prompt=prompt,
                    system_message=system_message,
                    temperature=temperature,
                )
            except Exception as fallback_error:
                msg = f"Both Gemini and fallback failed: {fallback_error!s}"
                raise LLMError(
                    msg,
                ) from e
        msg = f"LLM generation failed: {e!s}"
        raise LLMError(msg) from e


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
