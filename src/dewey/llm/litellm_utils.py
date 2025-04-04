"""
Utility functions for working with LiteLLM.

This module provides helper functions for common operations with LiteLLM
such as loading and setting API keys, extracting text from responses,
and managing fallbacks and providers.
"""

import logging
import os
import re
from typing import Any

import litellm
import yaml
from litellm import completion

from dewey.llm.exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMResponseError,
)
from dewey.llm.litellm_client import LiteLLMClient, Message

logger = logging.getLogger(__name__)

# Path to Aider configuration files
AIDER_CONF_PATH = os.path.expanduser("~/.aider.conf.yml")
AIDER_MODEL_METADATA_PATH = os.path.expanduser("~/.aider.model.metadata.json")


def load_api_keys_from_env() -> dict[str, str]:
    """
    Load API keys from environment variables.

    Returns
    -------
        Dictionary mapping provider names to API keys

    """
    # Define the environment variable names for different providers
    key_mappings = {
        "openai": "OPENAI_API_KEY",
        "azure": "AZURE_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "cohere": "COHERE_API_KEY",
        "huggingface": "HUGGINGFACE_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "google": "GOOGLE_API_KEY",
        "deepinfra": "DEEPINFRA_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }

    # Load keys from environment
    api_keys = {}
    for provider, env_var in key_mappings.items():
        key = os.environ.get(env_var)
        if key:
            api_keys[provider] = key
            logger.debug(f"Loaded API key for {provider}")

    # Special case: If GOOGLE_API_KEY is present but GEMINI_API_KEY is not,
    # use GOOGLE_API_KEY for gemini provider
    if "google" in api_keys and "gemini" not in api_keys:
        api_keys["gemini"] = api_keys["google"]
        logger.debug("Using GOOGLE_API_KEY for gemini provider")

    # Try to load additional keys from Aider config
    aider_keys = load_api_keys_from_aider()
    if aider_keys:
        # Merge with environment keys (environment takes precedence)
        for provider, key in aider_keys.items():
            if provider not in api_keys or not api_keys[provider]:
                api_keys[provider] = key
                logger.debug(f"Loaded API key for {provider} from Aider config")

    # Try to load from .env file if available
    try:
        from dotenv import load_dotenv
        loaded = load_dotenv()
        if loaded:
            logger.debug("Loaded environment variables from .env file")
            # Check for new keys after loading .env
            for provider, env_var in key_mappings.items():
                if provider not in api_keys or not api_keys[provider]:
                    key = os.environ.get(env_var)
                    if key:
                        api_keys[provider] = key
                        logger.debug(f"Loaded API key for {provider} from .env file")
    except ImportError:
        logger.debug("dotenv not installed, skipping .env file loading")

    return api_keys


def load_api_keys_from_aider() -> dict[str, str]:
    """
    Load API keys from Aider configuration files.

    Returns
    -------
        Dictionary mapping provider names to API keys

    """
    api_keys = {}

    # Try to load from .aider.conf.yml
    try:
        if os.path.exists(AIDER_CONF_PATH):
            with open(AIDER_CONF_PATH) as f:
                aider_conf = yaml.safe_load(f)

                # Extract API keys from api-key field
                api_key_str = aider_conf.get("api-key", "")
                if api_key_str:
                    # Parse entries like "deepinfra=KEY,openai=KEY"
                    key_pairs = api_key_str.split(",")
                    for pair in key_pairs:
                        if "=" in pair:
                            provider, key = pair.split("=", 1)
                            api_keys[provider.strip()] = key.strip()

                # Extract API keys from set-env field
                env_vars = aider_conf.get("set-env", [])
                for env_var in env_vars:
                    if "=" in env_var:
                        name, value = env_var.split("=", 1)
                        # Look for API keys like DEEPINFRA_API_KEY
                        if name.endswith("_API_KEY"):
                            provider = name.replace("_API_KEY", "").lower()
                            api_keys[provider] = value
    except Exception as e:
        logger.warning(f"Error loading API keys from Aider config: {e}")

    return api_keys


def set_api_keys(api_keys: dict[str, str]) -> None:
    """
    Set API keys for various providers.

    Args:
    ----
        api_keys: Dictionary mapping provider names to API keys

    """
    for provider, key in api_keys.items():
        try:
            # For OpenAI, set the API key directly
            if provider.lower() == "openai":
                litellm.api_key = key
                os.environ["OPENAI_API_KEY"] = key
                logger.debug("Set OpenAI API key")

            # For DeepInfra, set both environment variables
            elif provider.lower() == "deepinfra":
                os.environ["DEEPINFRA_API_KEY"] = key
                # Ensure we set the base URL to the OpenAI-compatible endpoint
                os.environ["DEEPINFRA_API_BASE"] = "https://api.deepinfra.com/v1/openai"
                # Also set using litellm's provider-specific method if available
                try:
                    litellm.deepinfra_api_key = key
                    # Set up litellm better for DeepInfra
                    if not hasattr(litellm, "model_list"):
                        litellm.model_list = []
                        
                    # Add a DeepInfra model configuration if it doesn't exist yet
                    deepinfra_model_found = False
                    for model in litellm.model_list:
                        if 'deepinfra' in model.get('model_name', ''):
                            deepinfra_model_found = True
                            break
                            
                    if not deepinfra_model_found:
                        litellm.model_list.append({
                            "model_name": "deepinfra/google/gemini-2.0-flash-001",
                            "litellm_provider": "deepinfra",
                            "api_base": "https://api.deepinfra.com/v1/openai",
                            "api_key": key
                        })
                except AttributeError:
                    # Older versions of litellm don't have these attributes
                    logger.debug("Using older version of litellm without provider-specific attributes")
                logger.debug("Set DeepInfra API key and configured models")

            # For Gemini/Google, set both environment variables
            elif provider.lower() in ["gemini", "google"]:
                os.environ["GEMINI_API_KEY"] = key
                os.environ["GOOGLE_API_KEY"] = key
                # Also set using litellm's provider-specific method if available
                try:
                    litellm.gemini_api_key = key
                except AttributeError:
                    # Older versions of litellm don't have this attribute
                    pass
                logger.debug(f"Set {provider.capitalize()} API key")

            # For other providers, set environment variables in the format PROVIDER_API_KEY
            else:
                # Set as environment variable in the format PROVIDER_API_KEY
                os.environ[f"{provider.upper()}_API_KEY"] = key
                logger.debug(f"Set environment variable for {provider}")

            # Try to set directly on litellm for common providers that might be supported
            try:
                # Dynamically set provider key if available as attribute in litellm
                attr_name = f"{provider.lower()}_api_key"
                if hasattr(litellm, attr_name):
                    setattr(litellm, attr_name, key)
                    logger.debug(f"Set litellm.{attr_name}")
            except Exception as attr_error:
                logger.debug(f"Could not set litellm attribute for {provider}: {attr_error}")

        except Exception as e:
            logger.error(f"Failed to set API key for {provider}: {e}")


def load_model_metadata_from_aider() -> dict[str, dict[str, Any]]:
    """
    Load LLM model metadata from Aider's model metadata file.

    Returns
    -------
        Dictionary mapping model names to their metadata

    """
    try:
        if os.path.exists(AIDER_MODEL_METADATA_PATH):
            with open(AIDER_MODEL_METADATA_PATH) as f:
                # The file might have trailing commas which JSON doesn't allow
                content = f.read()
                # Remove trailing commas
                content = re.sub(r",\s*}", "}", content)
                content = re.sub(r",\s*]", "]", content)

                # Parse as YAML which is more forgiving than JSON
                return yaml.safe_load(content)
    except Exception as e:
        logger.warning(f"Error loading model metadata from Aider: {e}")

    return {}


def get_available_models() -> list[dict[str, Any]]:
    """
    Get a list of available models across all configured providers.

    Returns
    -------
        List of dictionaries containing model information

    """
    try:
        # In older versions of litellm, list_available_models is not available
        # Instead, we'll return a manual list of commonly used models
        models = [
            {"id": "gpt-3.5-turbo", "provider": "openai"},
            {"id": "gpt-4", "provider": "openai"},
            {"id": "gpt-4-turbo", "provider": "openai"},
            {"id": "text-embedding-ada-002", "provider": "openai"},
            {"id": "claude-2", "provider": "anthropic"},
            {"id": "claude-instant-1", "provider": "anthropic"},
            {"id": "gemini-pro", "provider": "google"},
            {"id": "gemini-1.5-pro", "provider": "google"},
            {"id": "mistral-small", "provider": "mistral"},
            {"id": "mistral-medium", "provider": "mistral"},
        ]
        logger.debug(f"Using preset list of {len(models)} models")
        return models
    except Exception as e:
        logger.error(f"Failed to list available models: {e}")
        raise LLMConnectionError(f"Failed to list available models: {e}")


def configure_azure_openai(
    api_key: str, api_base: str, api_version: str, deployment_name: str | None = None,
) -> None:
    """
    Configure Azure OpenAI settings for LiteLLM.

    Args:
    ----
        api_key: Azure OpenAI API key
        api_base: Azure OpenAI API base URL
        api_version: Azure OpenAI API version
        deployment_name: Optional deployment name

    """
    try:
        # Set environment variables for Azure OpenAI
        os.environ["AZURE_API_KEY"] = api_key
        os.environ["AZURE_API_BASE"] = api_base
        os.environ["AZURE_API_VERSION"] = api_version

        if deployment_name:
            os.environ["AZURE_DEPLOYMENT_NAME"] = deployment_name

        logger.info("Azure OpenAI configuration set successfully")
    except Exception as e:
        logger.error(f"Failed to configure Azure OpenAI: {e}")
        raise LLMAuthenticationError(f"Failed to configure Azure OpenAI: {e}")


def setup_fallback_models(primary_model: str, fallback_models: list[str]) -> None:
    """
    Configure model fallbacks for reliability.

    Args:
    ----
        primary_model: The primary model to use
        fallback_models: List of fallback models to try if the primary model fails

    """
    try:
        litellm.set_fallbacks(fallbacks=[primary_model] + fallback_models)
        logger.info(
            f"Set up fallback chain: {primary_model} → {' → '.join(fallback_models)}",
        )
    except Exception as e:
        logger.error(f"Failed to set up fallback models: {e}")


def get_text_from_response(response: dict[str, Any]) -> str:
    """
    Extract text content from an LLM response.

    Args:
    ----
        response: LLM response dictionary

    Returns:
    -------
        Extracted text content

    Raises:
    ------
        LLMResponseError: If text content cannot be extracted

    """
    try:
        # Handle different response formats
        if "choices" in response and len(response["choices"]) > 0:
            choice = response["choices"][0]

            # OpenAI format
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]

            # Classic completion format
            if "text" in choice:
                return choice["text"]

        # Anthropic format
        elif "content" in response and len(response["content"]) > 0:
            contents = response["content"]
            text_parts = [
                part["text"] for part in contents if part.get("type") == "text"
            ]
            return "".join(text_parts)

        # If we can't extract text using known patterns
        raise LLMResponseError("Could not extract text from response")
    except Exception as e:
        logger.error(f"Failed to extract text from response: {e}")
        raise LLMResponseError(f"Failed to extract text from response: {e}")


def create_message(role: str, content: str) -> Message:
    """
    Create a message object for LLM conversations.

    Args:
    ----
        role: The role of the message sender (system, user, assistant)
        content: The content of the message

    Returns:
    -------
        A Message object

    """
    return Message(role=role, content=content)


def quick_completion(prompt: str, model: str = "gpt-3.5-turbo", **kwargs) -> str:
    """
    Get a quick completion for a simple prompt.

    Args:
    ----
        prompt: The text prompt to send to the model
        model: The model to use for the completion
        **kwargs: Additional parameters for the completion

    Returns:
    -------
        The generated text response

    Raises:
    ------
        LLMResponseError: If the completion fails

    """
    try:
        # Create a messages array with a single user message
        messages = [{"role": "user", "content": prompt}]

        # Call the completion API
        response = completion(model=model, messages=messages, **kwargs)

        # Extract and return the text
        return get_text_from_response(response)
    except Exception as e:
        logger.error(f"Quick completion failed: {e}")
        raise LLMResponseError(f"Quick completion failed: {e}")


def initialize_client_from_env() -> LiteLLMClient:
    """
    Initialize a LiteLLM client using environment variables.

    Returns
    -------
        Configured LiteLLMClient instance

    """
    # Load API keys
    api_keys = load_api_keys_from_env()

    # Get verbose mode from environment
    verbose = os.environ.get("LITELLM_VERBOSE", "").lower() == "true"

    # Initialize the client with verbose flag
    client = LiteLLMClient(verbose=verbose)

    # Set API keys for the providers
    set_api_keys(api_keys)

    # Configure fallbacks if specified
    fallback_env = os.environ.get("LITELLM_FALLBACKS", "")
    if fallback_env:
        fallbacks = [model.strip() for model in fallback_env.split(",")]
        if fallbacks and len(fallbacks) > 0:
            setup_fallback_models(client.config.model, fallbacks)

    logger.info(f"Initialized LiteLLM client with model: {client.config.model}")
    return client
