from typing import Optional, Dict, Any
import os
from openai import OpenAI
from llm.api_clients.deepinfra import DeepInfraClient, LLMError

def generate_response(
    prompt: str,
    model: str = "gemini-2.0-flash", 
    temperature: float = 0.7,
    max_tokens: int = 1000,
    system_message: Optional[str] = None,
    api_key: Optional[str] = None
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
        client = DeepInfraClient(api_key=api_key)
        return client.chat_completion(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_message=system_message
        )
    except Exception as e:
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
