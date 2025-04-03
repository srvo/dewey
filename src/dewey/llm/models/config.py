"""
Module for LLM configuration management.

This module provides classes for managing configurations for language models.
"""

from typing import Any, Dict, Optional

from dewey.core.base_script import BaseScript


class LLMConfigManager:
    """Manager class for LLM configurations.
    
    This class provides methods for loading and accessing LLM configuration
    from the central dewey.yaml configuration file.
    """
    
    @classmethod
    def get_model_config(cls, config: Dict[str, Any], model_name: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for a specific model or the default model.
        
        Args:
            config: The full configuration dictionary
            model_name: Optional name of the model to get config for. If None, uses the default model.
            
        Returns:
            Configuration dictionary for the specified model
            
        Raises:
            ValueError: If the model configuration is not found
        """
        llm_config = config.get("llm", {})
        providers = llm_config.get("providers", {})
        
        # If no model specified, use the default model from the default provider
        if not model_name:
            default_provider = llm_config.get("default_provider")
            if not default_provider or default_provider not in providers:
                raise ValueError(f"Default provider '{default_provider}' not found in configuration")
                
            provider_config = providers.get(default_provider, {})
            model_name = provider_config.get("default_model")
            if not model_name:
                raise ValueError(f"Default model not specified for provider '{default_provider}'")
        
        # Find the provider that contains this model
        for provider_name, provider_config in providers.items():
            if provider_config.get("default_model") == model_name:
                return {
                    "provider": provider_name,
                    "model": model_name,
                    "api_key": provider_config.get("api_key"),
                    "api_base": provider_config.get("api_base"),
                    "timeout": provider_config.get("timeout", 30.0),
                    **provider_config
                }
            
            # Check if the model is in fallback models
            fallback_models = provider_config.get("fallback_models", [])
            if model_name in fallback_models:
                return {
                    "provider": provider_name,
                    "model": model_name,
                    "api_key": provider_config.get("api_key"),
                    "api_base": provider_config.get("api_base"),
                    "timeout": provider_config.get("timeout", 30.0),
                    **provider_config
                }
        
        raise ValueError(f"Model '{model_name}' not found in any provider configuration")
    
    @classmethod
    def get_agent_config(cls, config: Dict[str, Any], agent_name: str) -> Dict[str, Any]:
        """Get configuration for a specific agent.
        
        Args:
            config: The full configuration dictionary
            agent_name: Name of the agent to get config for
            
        Returns:
            Configuration dictionary for the specified agent
            
        Raises:
            ValueError: If the agent configuration is not found
        """
        agent_config = config.get("agents", {}).get(agent_name)
        if not agent_config:
            raise ValueError(f"Agent '{agent_name}' not found in configuration")
        
        # Merge with default agent config if it exists
        default_config = config.get("agents", {}).get("defaults", {})
        return {**default_config, **agent_config} 