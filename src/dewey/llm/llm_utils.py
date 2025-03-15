"""Core LLM utilities for interacting with AI providers."""
from typing import Optional, Dict, Any
import os
import logging
from openai import OpenAI
from openai.types.chat import ChatCompletion

class LLMError(Exception):
    """Base exception for LLM operations."""

def get_deepinfra_client() -> OpenAI:
    """Initialize DeepInfra client with environment config."""
    return OpenAI(
        api_key=os.getenv("DEEPINFRA_API_KEY"),
        base_url="https://api.deepinfra.com/v1/openai",
    )

def generate_response(
    prompt: str,
    model: str = "meta-llama/Meta-Llama-3-8B-Instruct",
    temperature: float = 0.7,
    max_tokens: int = 1000,
    system_message: Optional[str] = None
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
    client = get_deepinfra_client()
    messages = []
    
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    try:
        response: ChatCompletion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"LLM API Error: {str(e)}")
        raise LLMError("Failed to generate LLM response") from e
