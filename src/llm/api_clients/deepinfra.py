from typing import Optional, Dict, Any
import os
from openai import OpenAI
from llm.llm_utils import LLMError

class DeepInfraClient:
    """Client for interacting with DeepInfra's OpenAI-compatible API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DeepInfra client.
        
        Args:
            api_key: Optional DeepInfra API key. If not provided, will attempt
                to read from DEEPINFRA_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv("DEEPINFRA_API_KEY")
        if not self.api_key:
            raise LLMError("DeepInfra API key not found. Set DEEPINFRA_API_KEY environment variable.")
            
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepinfra.com/v1/openai",
        )

    def chat_completion(
        self,
        prompt: str,
        model: str = "meta-llama/Meta-Llama-3-8B-Instruct",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate a chat completion response from DeepInfra.
        
        Args:
            prompt: User input prompt
            model: Model identifier string
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            system_message: Optional system message to guide model behavior
            **kwargs: Additional parameters for completion
            
        Returns:
            Generated text content
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise LLMError(f"DeepInfra API error: {str(e)}") from e

    def stream_completion(self, **kwargs) -> str:
        """Streaming version of chat completion (not yet implemented)."""
        raise NotImplementedError("Streaming completion not implemented yet")
