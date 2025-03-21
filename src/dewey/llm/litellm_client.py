"""
LiteLLM client for handling LLM calls across different providers.

This module provides a unified interface for interacting with different
LLM providers using the LiteLLM library.
"""

import logging
import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import litellm
from litellm import (
    completion,
    embedding,
    get_model_info,
    ModelResponse,
    completion_cost,
)

from dewey.llm.exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)

# Path to config files
CONFIG_PATH = Path("/Users/srvo/dewey/src/dewey/llm/config.yaml")
AIDER_MODEL_METADATA_PATH = Path(os.path.expanduser("~/.aider.model.metadata.json"))


@dataclass
class Message:
    """Message format for LLM conversations."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None  # For "tool" roles


@dataclass
class LiteLLMConfig:
    """Configuration for LiteLLM client."""

    model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    organization_id: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60
    max_retries: int = 3
    fallback_models: List[str] = field(default_factory=list)
    proxy: Optional[str] = None
    cache: bool = False
    cache_folder: str = ".litellm_cache"
    verbose: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    litellm_provider: Optional[str] = None


class LiteLLMClient:
    """Client for interacting with various LLM providers using LiteLLM."""

    def __init__(
        self, config: Optional[LiteLLMConfig] = None, verbose: bool = False
    ):
        """
        Initialize the LiteLLM client.

        Args:
            config: Configuration for the client, defaults to environment-based config
            verbose: Whether to enable verbose logging
        """
        # Set verbose mode
        self.verbose = verbose

        # Try to load configuration from various sources
        if config is None:
            # First try to load from Dewey config
            dewey_config = self._load_dewey_config()
            if dewey_config:
                self.config = self._create_config_from_dewey(dewey_config)
            # Next try to load from Aider model metadata
            elif AIDER_MODEL_METADATA_PATH.exists():
                self.config = self._create_config_from_aider()
            # Fall back to environment variables
            else:
                self.config = self._create_config_from_env()
        else:
            self.config = config

        logger.info(f"Initialized LiteLLM client with model: {self.config.model}")

        # Set OpenAI API key if available
        if self.config.api_key:
            litellm.api_key = self.config.api_key

        # Set up litellm parameters
        if self.config.cache:
            os.environ["LITELLM_CACHE_FOLDER"] = self.config.cache_folder
            logger.debug(f"Enabled caching in {self.config.cache_folder}")

        # Set up proxy if specified
        if self.config.proxy:
            os.environ["LITELLM_PROXY"] = self.config.proxy
            logger.debug(f"Using proxy: {self.config.proxy}")

    def _load_dewey_config(self) -> Optional[Dict[str, Any]]:
        """
        Load configuration from the Dewey config file.
        
        Returns:
            Dictionary of configuration values, or None if loading fails
        """
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r") as f:
                    config = yaml.safe_load(f)
                    logger.debug("Loaded configuration from Dewey config")
                    return config
            else:
                logger.debug(f"Dewey config file not found at {CONFIG_PATH}")
                return None
        except Exception as e:
            logger.warning(f"Failed to load Dewey config: {e}")
            return None
    
    def _create_config_from_dewey(self, dewey_config: Dict[str, Any]) -> LiteLLMConfig:
        """
        Create LiteLLMConfig from Dewey config.
        
        Args:
            dewey_config: The loaded Dewey configuration
            
        Returns:
            LiteLLMConfig populated with values from the Dewey config
        """
        # Extract LLM configuration from Dewey config
        llm_config = dewey_config.get("llm", {})
        
        # Create LiteLLMConfig with values from Dewey config
        config = LiteLLMConfig(
            model=llm_config.get("model", "gpt-3.5-turbo"),
            api_key=llm_config.get("api_key"),
            base_url=llm_config.get("base_url"),
            timeout=llm_config.get("timeout", 60),
            max_retries=llm_config.get("max_retries", 3),
            fallback_models=llm_config.get("fallback_models", []),
            proxy=llm_config.get("proxy"),
            cache=llm_config.get("cache", False),
            cache_folder=llm_config.get("cache_folder", ".litellm_cache"),
            verbose=llm_config.get("verbose", False),
            litellm_provider=llm_config.get("provider")
        )
        
        logger.debug(f"Created config from Dewey config with model: {config.model}")
        return config

    def _create_config_from_aider(self) -> LiteLLMConfig:
        """
        Create LiteLLMConfig from Aider model metadata.
        
        Returns:
            LiteLLMConfig populated with values from Aider metadata
        """
        try:
            # Load Aider model metadata
            from dewey.llm.litellm_utils import load_model_metadata_from_aider
            model_metadata = load_model_metadata_from_aider()
            
            # Default to a reliable model if we can't determine one from Aider
            default_model = "gpt-3.5-turbo"
            litellm_provider = None
            
            # Try to find a good model from the metadata
            if model_metadata:
                # Find models with LiteLLM provider specified
                provider_models = {name: data for name, data in model_metadata.items() 
                                if 'litellm_provider' in data}
                
                # Prioritize OpenAI, Anthropic, then any provider
                for provider in ['openai', 'anthropic']:
                    for name, data in provider_models.items():
                        if data.get('litellm_provider', '').lower() == provider:
                            default_model = name
                            litellm_provider = provider
                            break
                    if litellm_provider:
                        break
                
                # If no preferred provider found, use the first available
                if not litellm_provider and provider_models:
                    name, data = next(iter(provider_models.items()))
                    default_model = name
                    litellm_provider = data.get('litellm_provider')
            
            # Create config with values from Aider or defaults
            config = LiteLLMConfig(
                model=default_model,
                verbose=os.environ.get("LITELLM_VERBOSE", "").lower() == "true",
                litellm_provider=litellm_provider
            )
            
            logger.debug(f"Created config from Aider metadata with model: {config.model}")
            return config
        
        except Exception as e:
            logger.warning(f"Failed to create config from Aider metadata: {e}")
            return self._create_config_from_env()

    def _create_config_from_env(self) -> LiteLLMConfig:
        """
        Create LiteLLMConfig from environment variables.
        
        Returns:
            LiteLLMConfig populated with values from environment variables
        """
        # Get environment variables with defaults
        config = LiteLLMConfig(
            model=os.environ.get("LITELLM_MODEL", "gpt-3.5-turbo"),
            api_key=os.environ.get("OPENAI_API_KEY"),
            organization_id=os.environ.get("OPENAI_ORGANIZATION"),
            base_url=os.environ.get("OPENAI_BASE_URL"),
            timeout=int(os.environ.get("LITELLM_TIMEOUT", "60")),
            max_retries=int(os.environ.get("LITELLM_MAX_RETRIES", "3")),
            proxy=os.environ.get("LITELLM_PROXY"),
            cache=os.environ.get("LITELLM_CACHE", "").lower() == "true",
            cache_folder=os.environ.get("LITELLM_CACHE_FOLDER", ".litellm_cache"),
            verbose=os.environ.get("LITELLM_VERBOSE", "").lower() == "true",
        )
        
        # Parse fallback models if specified
        fallback_env = os.environ.get("LITELLM_FALLBACKS", "")
        if fallback_env:
            config.fallback_models = [model.strip() for model in fallback_env.split(",")]
        
        logger.debug(f"Created config from environment with model: {config.model}")
        return config

    def generate_completion(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[Union[str, List[str]]] = None,
        user: Optional[str] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> ModelResponse:
        """
        Generate a completion from messages.

        Args:
            messages: List of Message objects
            model: Model to use, defaults to config model
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Penalize repeat tokens
            presence_penalty: Penalize repeat topics
            stop: Stop sequences
            user: User identifier
            functions: Function schemas for function calling
            function_call: Function call configuration

        Returns:
            LiteLLM ModelResponse

        Raises:
            LLMResponseError: For general response errors
            LLMConnectionError: For connection issues
            LLMAuthenticationError: For authentication issues
            LLMRateLimitError: For rate limiting issues
            LLMTimeoutError: For timeout issues
        """
        try:
            # Convert Message objects to dictionaries
            messages_dict = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    **({"name": msg.name} if msg.name else {}),
                }
                for msg in messages
            ]

            # Use model from parameters or config
            model_name = model or self.config.model

            # Log the request if verbose
            if self.verbose:
                logger.debug(
                    f"Generating completion with model {model_name}, "
                    f"{len(messages)} messages, temperature={temperature}"
                )

            # Call litellm completion
            response = completion(
                model=model_name,
                messages=messages_dict,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stop=stop,
                user=user,
                functions=functions,
                function_call=function_call,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )

            # Calculate cost for logging
            cost = completion_cost(
                completion_response=response,
            )
            logger.debug(f"Completion cost: ${cost:.6f}")

            return response

        except litellm.exceptions.RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            raise LLMRateLimitError(f"Rate limit exceeded: {e}")
        except litellm.exceptions.AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            raise LLMAuthenticationError(f"Authentication error: {e}")
        except litellm.exceptions.APIConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise LLMConnectionError(f"Connection error: {e}")
        except litellm.exceptions.APITimeoutError as e:
            logger.warning(f"Request timed out: {e}")
            raise LLMTimeoutError(f"Request timed out: {e}")
        except litellm.exceptions.BadRequestError as e:
            logger.error(f"Bad request: {e}")
            raise LLMResponseError(f"Bad request: {e}")
        except Exception as e:
            logger.error(f"Failed to generate completion: {e}")
            raise LLMResponseError(f"Failed to generate completion: {e}")

    def generate_embedding(
        self,
        input_text: Union[str, List[str]],
        model: Optional[str] = None,
        encoding_format: str = "float",
        dimensions: Optional[int] = None,
        user: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate embeddings for input text.

        Args:
            input_text: String or list of strings to embed
            model: Model to use, defaults to a suitable embedding model
            encoding_format: Encoding format for vectors
            dimensions: Dimensionality of output vectors
            user: User identifier

        Returns:
            Dictionary with embedding data

        Raises:
            LLMResponseError: For general response errors
            LLMConnectionError: For connection issues
            LLMAuthenticationError: For authentication issues
        """
        try:
            # Use model from parameters, or a default embedding model
            model_name = model or os.environ.get(
                "LITELLM_EMBEDDING_MODEL", "text-embedding-ada-002"
            )

            # Log the request if verbose
            if self.verbose:
                input_len = (
                    len(input_text)
                    if isinstance(input_text, str)
                    else len(input_text[0])
                    if input_text
                    else 0
                )
                logger.debug(
                    f"Generating embedding with model {model_name}, "
                    f"input length {input_len}"
                )

            # Call litellm embedding
            response = embedding(
                model=model_name,
                input=input_text,
                encoding_format=encoding_format,
                dimensions=dimensions,
                user=user,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )

            return response

        except litellm.exceptions.RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            raise LLMRateLimitError(f"Rate limit exceeded: {e}")
        except litellm.exceptions.AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            raise LLMAuthenticationError(f"Authentication error: {e}")
        except litellm.exceptions.APIConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise LLMConnectionError(f"Connection error: {e}")
        except litellm.exceptions.APITimeoutError as e:
            logger.warning(f"Request timed out: {e}")
            raise LLMTimeoutError(f"Request timed out: {e}")
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise LLMResponseError(f"Failed to generate embedding: {e}")

    def get_model_details(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get details about a specific model.

        Args:
            model: Model name to get details for, defaults to config model

        Returns:
            Dictionary with model details

        Raises:
            LLMResponseError: If model details cannot be retrieved
        """
        try:
            model_name = model or self.config.model
            model_info = get_model_info(model=model_name)
            return model_info
        except Exception as e:
            logger.error(f"Failed to get model details: {e}")
            raise LLMResponseError(f"Failed to get model details: {e}")
