from typing import Optional, Dict, Any
import os
import logging
from openai import OpenAI
from llm.api_clients.gemini import GeminiClient
from llm.exceptions import LLMError

def generate_response(
    prompt: str,
    model: str = "gemini-2.0-flash", 
    temperature: float = 0.7,
    system_message: Optional[str] = None,
    api_key: Optional[str] = None,
    fallback_client: Optional[Any] = None
) -> str:
    """
    Generate a response from the specified LLM model.
    
    Args:
        prompt: Input text prompt
        model: Model identifier (default: Meta-Llama-3-8B-Instruct)
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum number of tokens to generate
        system_message: Optional system message for chat models
        api_key: Optional API key override
        
    Returns:
        Generated text response
        
    Raises:
        LLMError: If there's an error during generation
    """
    try:
        client = GeminiClient(api_key=api_key)
        # Prepend system message to prompt if provided
        full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt
        
        return client.generate_content(
            prompt=full_prompt,
            model=model,
            temperature=temperature
        )
    except Exception as e:
        if fallback_client and "exhausted" in str(e).lower():
            try:
                logging.warning("Gemini API exhausted, falling back to DeepInfra")
                return fallback_client.chat_completion(
                    prompt=prompt,
                    system_message=system_message,
                    temperature=temperature
                )
            except Exception as fallback_error:
                raise LLMError(f"Both Gemini and fallback failed: {str(fallback_error)}") from e
        raise LLMError(f"LLM generation failed: {str(e)}") from e

def validate_model_params(params: Dict[str, Any]) -> None:
    """
    Validate parameters for LLM model calls.
    
    Args:
        params: Dictionary of parameters to validate
        
    Raises:
        ValueError: If any parameters are invalid
    """
    if "temperature" in params and not 0 <= params["temperature"] <= 2:
        raise ValueError("Temperature must be between 0 and 2")
    if "max_tokens" in params and params["max_tokens"] <= 0:
        raise ValueError("max_tokens must be positive integer")
