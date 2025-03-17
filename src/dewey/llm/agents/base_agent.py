"""Base agent configuration using smolagents framework."""
from typing import Dict, Any, List, Optional
import os
from smolagents import CodeAgent, Tool, LiteLLMModel
from smolagents.tools import PythonREPLTool
from dewey.llm.llm_utils import LLMHandler

class DeweyBaseAgent(CodeAgent):
    """
    Base agent for all Dewey agents using the smolagents framework.

    Attributes:
        config (Dict[str, Any]): Configuration dictionary
        task_type (str): The type of task the agent is designed to perform
        llm_handler (LLMHandler): Centralized LLM handler instance
    """

    def __init__(self, config: Dict[str, Any], task_type: str):
        """
        Initializes the DeweyBaseAgent with configuration and task type.

        Args:
            config: Configuration dictionary from dewey.yaml
            task_type: The type of task the agent will perform

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        self.config = config
        self.task_type = task_type
        self._validate_config()
        self.llm_handler = LLMHandler(config.get("llm", {}))

        # Initialize model with config values
        model = LiteLLMModel(
            model_id=config.get("model", "Qwen/Qwen2.5-Coder-32B-Instruct"),
            api_key=os.environ.get("DEEPINFRA_API_KEY"),
            temperature=config.get("temperature", 0.3),
            max_tokens=config.get("max_tokens", 4096),
        )

        super().__init__(
            model=model,
            tools=self._get_tools(),
            system_prompt=self._get_system_prompt(task_type),
            safe_mode="e2b",
        )

    def _get_tools(self) -> List[Tool]:
        """
        Returns a list of tools available to the agent.

        Returns:
            List of Tool instances
        """
        return [PythonREPLTool()]

    def _get_system_prompt(self, task_type: str) -> str:
        """
        Returns the system prompt for the agent based on the task type.

        Args:
            task_type: The type of task the agent will perform

        Returns:
            System prompt string
        """
        prompts = {
            "docstring": "You are an expert at analyzing and generating Python docstrings. Your goal is to improve code documentation.",
            "contact": "You are an expert at analyzing contact information and determining if records should be merged.",
            "data_ingestion": "You specialize in data structure analysis. Your goal is to recommend optimal database schema changes.",
            "logical_fallacy_detection": "You are an expert in logical fallacy detection. Your goal is to identify logical fallacies in text.",
            "content_generation": "You are an expert content creator. Your goal is to generate high-quality content in a specific style.",
            "strategic_optimization": "You are an expert in strategic optimization. Your goal is to help users optimize their personal productivity.",
            "critical_analysis": "You are an expert in critical analysis. Your goal is to identify risks and challenge assumptions.",
            "transcript_analysis": "You are an expert in transcript analysis. Your goal is to extract actionable insights from meeting transcripts.",
            "rag_search": "You are an expert in semantic search. Your goal is to find relevant information in a knowledge base.",
            "client_advocacy": "You are an expert in client relationship management. Your goal is to manage client relationships and prioritize client work.",
            "wellness_monitoring": "You are an expert in wellness monitoring. Your goal is to monitor user work patterns and suggest self-care interventions."
        }
        return prompts.get(task_type, "You are a helpful AI assistant.")

    def generate_response(self, prompt: str, **kwargs) -> Any:
        """
        Generate response using centralized LLM handler.

        Args:
            prompt: Input prompt
            **kwargs: Additional parameters for the LLM

        Returns:
            Generated response
        """
        return self.llm_handler.generate_response(
            prompt,
            temperature=self.config.get("temperature", 0.3),
            max_tokens=self.config.get("max_tokens", 1000),
            **kwargs
        )

    @property
    def agent_config(self) -> Dict[str, Any]:
        """Get agent-specific configuration."""
        return self.config.get("agents", {}).get(self.task_type, {})

    def _validate_config(self) -> None:
        """Validate the agent configuration.
        
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        required_keys = {
            "llm": ["client", "default_provider"],
            f"agents.{self.task_type}": ["enabled", "version"]
        }
        
        errors = []
        for section, keys in required_keys.items():
            current = self.config
            for part in section.split('.'):
                current = current.get(part, {})
            
            for key in keys:
                if key not in current:
                    errors.append(f"Missing required config key: {section}.{key}")
        
        if errors:
            raise ValueError(f"Invalid configuration:\n" + "\n".join(errors))

    def get_config_value(self, path: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation path.
        
        Args:
            path: Dot notation path to config value (e.g. "llm.providers.deepinfra.api_key")
            default: Default value if path not found
            
        Returns:
            The config value or default if not found
        """
        current = self.config
        for part in path.split('.'):
            if not isinstance(current, dict):
                return default
            current = current.get(part, default)
        return current

    def ensure_config_section(self, path: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """Ensure a configuration section exists, creating it if needed.
        
        Args:
            path: Dot notation path to config section
            default: Default value to create if section doesn't exist
            
        Returns:
            The existing or created config section
        """
        if default is None:
            default = {}
            
        current = self.config
        parts = path.split('.')
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
            
        if parts[-1] not in current:
            current[parts[-1]] = default
            
        return current[parts[-1]]
