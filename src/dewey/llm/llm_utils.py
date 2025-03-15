"""Core LLM utilities for interacting with AI providers."""
from typing import Optional, Dict, Any
import os
import logging
from openai import OpenAI
from openai.types.chat import ChatCompletion

from src.llm.api_clients.openrouter import OpenRouterClient

class LLMError(Exception):
    """Base exception for LLM operations."""

def get_deepinfra_client() -> OpenAI:
    """Initialize DeepInfra client with environment config."""
    return OpenAI(
        api_key=os.getenv("DEEPINFRA_API_KEY"),
        base_url="https://api.deepinfra.com/v1/openai",
    )

def get_openrouter_client() -> OpenRouterClient:
    """Initialize OpenRouter client with environment config."""
    return OpenRouterClient(api_key=os.getenv("OPENROUTER_API_KEY"))

def generate_response(
    prompt: str,
    model: str = "meta-llama/Meta-Llama-3-8B-Instruct",
    temperature: float = 0.7,
    max_tokens: int = 1000,
    system_message: Optional[str] = None,
    api_key: Optional[str] = None,
    fallback_client: Optional[str] = None
) -> str:
    """
    Generate text response using DeepInfra's OpenAI-compatible API.
    
    Args:
        prompt: User input prompt
        model: DeepInfra model name
        temperature: Creativity parameter (0-2)
        max_tokens: Maximum response length
        system_message: Optional system role message
    
    Returns:
        Generated text response
        
    Raises:
        LLMError: For API failures or invalid responses
    """
    if fallback_client == "openrouter":
        client = get_openrouter_client()
    else:
        client = get_deepinfra_client()
    
    try:
        if isinstance(client, OpenAI):
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            response: ChatCompletion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        elif isinstance(client, OpenRouterClient):
            return client.generate_content(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            raise ValueError(f"Unsupported client type: {type(client)}")
    except Exception as e:
        logging.error(f"LLM API Error: {str(e)}")
        raise LLMError("Failed to generate LLM response") from e
