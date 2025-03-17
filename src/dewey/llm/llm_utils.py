from __future__ import annotations

import logging
from typing import Any
import json
import os

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
        """Initialize the appropriate LLM client based on config."""
        # First check for default provider in config
        client_type = (
            self.config.get("default_provider") or  # Check default_provider first
            self.config.get("client", "gemini")     # Fallback to client or gemini
        )
        
        try:
            # Load environment variables from project root .env
            from dotenv import load_dotenv
            env_path = os.path.join(os.getenv("DEWEY_PROJECT_ROOT", "/Users/srvo/dewey"), ".env")
            load_dotenv(env_path)
            
            if client_type == "gemini":
                self.client = GeminiClient(config=self.config)
            elif client_type == "deepinfra":
                # Get API key from providers section or environment
                api_key = (
                    self.config.get("providers", {}).get("deepinfra", {}).get("api_key") or
                    os.getenv("DEEPINFRA_API_KEY")
                )
                if not api_key:
                    msg = f"DeepInfra API key not found in config or environment file at {env_path}"
                    raise LLMError(msg)
                    
                # Handle ${VAR} format in the API key
                if isinstance(api_key, str) and api_key.startswith("${") and api_key.endswith("}"):
                    var_name = api_key[2:-1]  # Strip ${ and }
                    api_key = os.getenv(var_name)
                    if not api_key:
                        msg = f"Environment variable {var_name} not found"
                        raise LLMError(msg)
                        
                self.client = DeepInfraClient(api_key=api_key)
            else:
                msg = f"Unsupported LLM client: {client_type}"
                raise LLMError(msg)
                
            logger.info(f"Initialized {client_type} client")
            
        except Exception as e:
            msg = f"Failed to initialize {client_type} client: {e!s}"
            raise LLMError(msg)

    def _switch_to_deepinfra(self) -> None:
        """Switch to DeepInfra client and update config."""
        logger.info("Switching to DeepInfra permanently...")
        
        # Update the config to use DeepInfra
        self.config["client"] = "deepinfra"
        
        # Get DeepInfra API key from providers section if available
        api_key = (self.config.get("providers", {}).get("deepinfra", {}).get("api_key") or 
                  os.getenv("DEEPINFRA_API_KEY"))
        if not api_key:
            msg = "DeepInfra API key not found in config or environment"
            raise LLMError(msg)
            
        # Initialize new DeepInfra client with appropriate Gemini model
        self.client = DeepInfraClient(api_key=api_key)
        
        # Update the config file to persist the change
        try:
            config_path = os.path.join(os.getenv("DEWEY_PROJECT_ROOT", os.getcwd()), "config", "dewey.yaml")
            if os.path.exists(config_path):
                import yaml
                with open(config_path, 'r') as f:
                    full_config = yaml.safe_load(f)
                
                # Update the LLM config section
                if 'llm' not in full_config:
                    full_config['llm'] = {}
                full_config['llm']['default_provider'] = 'deepinfra'
                full_config['llm']['client'] = 'deepinfra'
                
                # Set appropriate Gemini model in DeepInfra config
                if 'providers' not in full_config['llm']:
                    full_config['llm']['providers'] = {}
                if 'deepinfra' not in full_config['llm']['providers']:
                    full_config['llm']['providers']['deepinfra'] = {}
                    
                full_config['llm']['providers']['deepinfra'].update({
                    'default_model': 'google/gemini-2.0-flash-001',
                    'fallback_models': [
                        'google/gemini-2.0-pro',
                        'google/gemini-2.0-pro-vision'
                    ]
                })
                
                # Write back to config file
                with open(config_path, 'w') as f:
                    yaml.safe_dump(full_config, f, default_flow_style=False)
                logger.info("Updated config file to use DeepInfra permanently")
        except Exception as e:
            logger.warning(f"Failed to persist DeepInfra switch to config file: {e}")
        
        logger.info("Successfully switched to DeepInfra client")

    def _clean_json_response(self, response: str) -> str:
        """Clean up JSON response from LLM output.
        
        Args:
            response: Raw response from LLM
            
        Returns:
            Cleaned response with only the JSON content
        """
        response = response.strip()
        
        # Remove markdown code blocks if present
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
            
        return response.strip()

    def _extract_json(self, response: str) -> str:
        """Extract JSON content from a string that might contain other text.
        
        Args:
            response: String that might contain JSON
            
        Returns:
            Extracted JSON string or original string if no JSON found
        """
        # First try to find content between curly braces
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            return response[start:end]
        
        # If no curly braces, try square brackets
        start = response.find('[')
        end = response.rfind(']') + 1
        if start >= 0 and end > start:
            return response[start:end]
            
        return response

    def parse_json_response(self, response: str, strict: bool = True) -> Any:
        """Parse JSON response from LLM output.
        
        Args:
            response: Raw response from LLM
            strict: If True, raise error for invalid JSON. If False, try to extract JSON content.
            
        Returns:
            Parsed JSON object
            
        Raises:
            LLMError: If JSON parsing fails and strict=True
        """
        try:
            # Clean up the response
            cleaned = self._clean_json_response(response)
            
            # Try to parse the cleaned response
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                if strict:
                    raise
                
                # If not strict, try to extract JSON content
                extracted = self._extract_json(cleaned)
                return json.loads(extracted)
                
        except json.JSONDecodeError as e:
            if strict:
                msg = f"Failed to parse JSON response: {e}"
                raise LLMError(msg) from e
            
            # If not strict, return the cleaned string
            logger.warning(f"Failed to parse JSON response, returning raw string: {e}")
            return cleaned

    def generate_response(
        self, prompt: str, fallback_model: str | None = None, **kwargs
    ) -> str | Any:
        """Unified interface for generating responses with fallback support.
        
        Args:
            prompt: Input prompt
            fallback_model: Optional fallback model to use if primary fails
            **kwargs: Additional parameters for the LLM
                - temperature: float = 0.7
                - max_tokens: int = 1000
                - response_format: dict = None (e.g. {"type": "json_object"})
                - strict_json: bool = True (only used if response_format is specified)
                
        Returns:
            Generated response as string, or parsed JSON if response_format specified
        """
        if not self.client:
            msg = "LLM client not initialized"
            raise LLMError(msg)

        # Handle JSON formatting in the prompt if needed
        if "response_format" in kwargs:
            json_format = str(kwargs["response_format"]).replace("'", '"')
            prompt = f"""IMPORTANT: Your response must be a valid JSON object.
Format: {json_format}

DO NOT include any markdown formatting, code blocks, or other text - ONLY the raw JSON object.

{prompt}"""

        try:
            self.usage_stats["requests"] += 1
            
            # Client-specific parameter handling
            if isinstance(self.client, GeminiClient):
                try:
                    params = {
                        "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
                        "model": kwargs.get("model", self.config.get("default_model", "gemini-2.0-flash-001")),
                    }
                    
                    # Only add max_output_tokens if specified
                    if "max_tokens" in kwargs:
                        params["max_output_tokens"] = kwargs["max_tokens"]
                        
                    response = self.client.generate_content(prompt, **params)
                except LLMError as e:
                    error_msg = str(e).lower()
                    if "rate limit" in error_msg or "circuit breaker" in error_msg or "resource has been exhausted" in error_msg:
                        # Switch to DeepInfra permanently
                        from rich.prompt import Confirm
                        if Confirm.ask("[yellow]Gemini API is rate limited. Would you like to switch to DeepInfra?[/yellow]"):
                            self._switch_to_deepinfra()
                            # Retry with DeepInfra
                            return self.generate_response(prompt, **kwargs)
                    raise
                    
            elif isinstance(self.client, DeepInfraClient):
                # Get model configuration
                deepinfra_config = self.config.get("providers", {}).get("deepinfra", {})
                default_model = deepinfra_config.get("default_model", "google/gemini-2.0-flash-001")
                
                params = {
                    "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
                    "max_tokens": kwargs.get("max_tokens", 1000),
                    "model": kwargs.get("model", default_model),
                }
                
                # Add system message for JSON format if needed
                if "response_format" in kwargs:
                    params["system_message"] = "You must respond with a valid JSON object. No other text or formatting."
                
                try:
                    response = self.client.chat_completion(prompt, **params)
                except LLMError as e:
                    # If primary model fails, try fallback models
                    fallback_models = deepinfra_config.get("fallback_models", [
                        "google/gemini-2.0-pro",
                        "google/gemini-2.0-pro-vision"
                    ])
                    
                    for fallback in fallback_models:
                        try:
                            logger.warning(f"Primary model failed, trying fallback: {fallback}")
                            params["model"] = fallback
                            response = self.client.chat_completion(prompt, **params)
                            break
                        except Exception:
                            continue
                    else:
                        # If all fallbacks fail, raise the original error
                        raise

            # Track token usage if available
            if hasattr(response, "usage"):
                self.usage_stats["tokens"] += response.usage.total_tokens
            
            # Get response text - handle both string and object responses
            # Both clients now guarantee string responses
            response_text = str(response).strip()
            
            # Parse JSON if requested
            if "response_format" in kwargs:
                return self.parse_json_response(
                    response_text,
                    strict=kwargs.get("strict_json", True)
                )
            
            return response_text
                
        except Exception as primary_error:
            if fallback_model:
                logger.warning(
                    f"Primary model failed, trying fallback: {fallback_model}"
                )
                try:
                    # Switch to DeepInfra client for fallback
                    self._switch_to_deepinfra()
                    return self.generate_response(prompt, **kwargs)
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
