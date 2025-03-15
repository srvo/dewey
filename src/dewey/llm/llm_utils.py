"""Core LLM utilities for interacting with AI providers."""
from typing import Optional, Dict, Any
import os
import re
import logging
import yaml
from openai import OpenAI
from openai.types.chat import ChatCompletion

from dewey.llm.api_clients.gemini import RateLimiter
from dewey.llm.api_clients.deepinfra import DeepInfraClient


def parse_llm_yaml_response(response: str, logger: logging.Logger = None) -> Dict:
    """Parse YAML response from LLM, handling common formatting issues."""
    try:
        # Extract first YAML block between --- markers
        parts = response.split('---')
        if len(parts) > 1:
            yaml_content = parts[1].strip()  # Get content between first --- pair
        else:
            yaml_content = response.strip()  # Fallback for responses without ---
        
        # Clean any remaining markdown syntax
        clean_response = re.sub(r'^```yaml\s*|```$', '', yaml_content, flags=re.MULTILINE).strip()
        
        if not clean_response:
            raise ValueError("Empty YAML response from LLM")
            
        try:
            parsed = yaml.safe_load(clean_response)
        except yaml.YAMLError as e:
            if logger:
                logger.error(f"YAML parsing failed. Content:\n{clean_response}")
            raise
            
        # Convert list of entries to dict
        if isinstance(parsed, list):
            result = {}
            for item in parsed:
                result.update(item)
            parsed = result
            
        if not isinstance(parsed, dict):
            raise ValueError("LLM returned invalid YAML structure")
            
        return parsed
    except Exception as e:
        if logger:
            logger.error(f"LLM Response that failed parsing:\n{response}")
        raise ValueError(f"Failed to parse LLM response: {str(e)}") from e

class LLMError(Exception):
    """Base exception for LLM operations."""

def get_deepinfra_client() -> OpenAI:
    """Initialize DeepInfra client with environment config."""
    return OpenAI(
        api_key=os.getenv("DEEPINFRA_API_KEY"),
        base_url="https://api.deepinfra.com/v1/openai",
    )


def generate_analysis_response(
    prompt: str,
    config: Dict,
    logger: logging.Logger,
    fallback_to_deepinfra: bool = False
) -> str:
    """Generate response with model rotation and fallback handling."""
    # Try all configured models with cooldown awareness
    models = config['llm_settings']['models']
    cooldown_minutes = config['llm_settings'].get('cooldownutesutes', 5)
    RateLimiter.cooldown_minutes = cooldown_minutes
    
    # Try primary models first
    for model in models:
        if not RateLimiter().is_in_cooldown(model):
            try:
                response = generate_response(
                    prompt,
                    model=model,
                    system_message="You are a Python code analysis assistant. Be concise and precise."
                )
                # Reset cooldown if successful
                if model in RateLimiter().cooldowns:
                    del RateLimiter().cooldowns[model]
                return response
            except LLMError as e:
                logger.warning(f"Model {model} failed: {str(e)}")
                RateLimiter().track_failure(model)
    
    # Fallback logic
    if fallback_to_deepinfra:
        logger.warning("All primary models exhausted, falling back to DeepInfra")
        return generate_response(
            prompt,
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            system_message="You are a Python code analysis assistant. Be concise and precise.",
            client=DeepInfraClient()
        )
    
    raise LLMError("All configured models exhausted with no successful responses")

def generate_response(
    prompt: str,
    model: str = "meta-llama/Meta-Llama-3-8B-Instruct",
    temperature: float = 0.7,
    max_tokens: int = 1000,
    system_message: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Optional[Any] = None
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
    if not client:
        client = get_openrouter_client() if "openrouter" in model.lower() else get_deepinfra_client()
    
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
        else:
            raise ValueError(f"Unsupported client type: {type(client)}")
    except Exception as e:
        logging.error(f"LLM API Error: {str(e)}")
        raise LLMError("Failed to generate LLM response") from e
