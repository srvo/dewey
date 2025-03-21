"""
Dewey LLM module for interacting with LLMs through various providers.

This package provides utilities for calling LLMs with consistent interfaces.
"""

from dewey.llm.exceptions import (
    InvalidPromptError,
    LLMAuthenticationError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)
from dewey.llm.litellm_client import (
    LiteLLMClient, 
    LiteLLMConfig, 
    Message
)
from dewey.llm.litellm_utils import (
    create_message,
    get_available_models,
    get_text_from_response,
    initialize_client_from_env,
    load_api_keys_from_env,
    quick_completion,
    set_api_keys,
)

__all__ = [
    # Classes
    "LiteLLMClient",
    "LiteLLMConfig",
    "Message",
    
    # LiteLLM utilities
    "create_message",
    "get_available_models",
    "get_text_from_response",
    "initialize_client_from_env",
    "load_api_keys_from_env",
    "quick_completion",
    "set_api_keys",
    
    # Exceptions
    "InvalidPromptError",
    "LLMAuthenticationError",
    "LLMConnectionError",
    "LLMError",
    "LLMRateLimitError",
    "LLMResponseError",
    "LLMTimeoutError",
]
