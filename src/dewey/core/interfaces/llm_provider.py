"""
Interface definition for LLM providers.

This module defines the abstract interface for language model providers,
allowing different implementations to be used interchangeably.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


class LLMProvider(ABC):
    """
    Abstract interface for language model providers.
    
    This interface defines the contract that all LLM providers must implement,
    allowing them to be used interchangeably throughout the Dewey project.
    """
    
    @abstractmethod
    def generate_text(
        self, 
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The text prompt to generate from
            max_tokens: Optional maximum number of tokens to generate
            temperature: Optional temperature parameter for controlling randomness
            **kwargs: Additional model-specific parameters
            
        Returns:
            Generated text as a string
        """
        pass
    
    @abstractmethod
    def generate_embeddings(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings from text.
        
        Args:
            text: The text to generate embeddings for (string or list of strings)
            
        Returns:
            Embeddings as a list of floats or list of lists of floats (for multiple inputs)
        """
        pass
    
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate a chat completion from a list of messages.
        
        Args:
            messages: List of message dictionaries (each with 'role' and 'content' keys)
            max_tokens: Optional maximum number of tokens to generate
            temperature: Optional temperature parameter for controlling randomness
            **kwargs: Additional model-specific parameters
            
        Returns:
            Generated response as a string
        """
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Get the name of the current model.
        
        Returns:
            Model name as a string
        """
        pass 