"""
LiteLLM implementation of the LLMProvider interface.

This module provides a concrete implementation of the LLMProvider interface
using the LiteLLM library, which supports multiple model providers.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from dewey.core.interfaces.llm_provider import LLMProvider
from dewey.llm.litellm_client import LiteLLMClient, LiteLLMConfig, Message

logger = logging.getLogger(__name__)


class LiteLLMProvider(LLMProvider):
    """
    LiteLLM implementation of the LLMProvider interface.
    
    This class wraps the existing LiteLLMClient with the standardized
    LLMProvider interface for use throughout the Dewey project.
    """
    
    def __init__(self, client: Optional[LiteLLMClient] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the LiteLLM provider.
        
        Args:
            client: Optional existing LiteLLMClient instance
            config: Optional configuration dictionary for creating a new client
        """
        if client:
            self._client = client
        else:
            if config:
                llm_config = LiteLLMConfig(**config)
                self._client = LiteLLMClient(config=llm_config)
            else:
                # Use default configuration
                self._client = LiteLLMClient()
                
        logger.debug(f"Initialized LiteLLMProvider with model: {self._client.config.model}")
    
    def generate_text(
        self, 
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate text from a prompt using LiteLLM.
        
        Args:
            prompt: The text prompt to generate from
            max_tokens: Optional maximum number of tokens to generate
            temperature: Optional temperature parameter for controlling randomness
            **kwargs: Additional model-specific parameters
            
        Returns:
            Generated text as a string
        """
        # Create message for completion
        messages = [Message(role="user", content=prompt)]
        
        # Set parameters
        params = {}
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        if temperature is not None:
            params["temperature"] = temperature
        params.update(kwargs)
        
        # Generate completion
        response = self._client.completion(messages, **params)
        return response.content
    
    def generate_embeddings(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings from text using LiteLLM.
        
        Args:
            text: The text to generate embeddings for (string or list of strings)
            
        Returns:
            Embeddings as a list of floats or list of lists of floats (for multiple inputs)
        """
        return self._client.embedding(text)
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate a chat completion from a list of messages using LiteLLM.
        
        Args:
            messages: List of message dictionaries (each with 'role' and 'content' keys)
            max_tokens: Optional maximum number of tokens to generate
            temperature: Optional temperature parameter for controlling randomness
            **kwargs: Additional model-specific parameters
            
        Returns:
            Generated response as a string
        """
        # Convert dict messages to Message objects
        formatted_messages = [
            Message(role=msg.get("role", "user"), content=msg.get("content", ""))
            for msg in messages
        ]
        
        # Set parameters
        params = {}
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        if temperature is not None:
            params["temperature"] = temperature
        params.update(kwargs)
        
        # Generate completion
        response = self._client.completion(formatted_messages, **params)
        return response.content
    
    @property
    def model_name(self) -> str:
        """
        Get the name of the current model.
        
        Returns:
            Model name as a string
        """
        return self._client.config.model
    
    def get_client(self) -> LiteLLMClient:
        """
        Get the underlying LiteLLMClient instance.
        
        This method is provided for cases where direct access to the
        client is needed for advanced functionality.
        
        Returns:
            The LiteLLMClient instance
        """
        return self._client 