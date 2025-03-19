"""Base agent configuration using smolagents framework integrated with BaseScript."""
import os
from typing import List, Dict, Any, Optional

from dewey.core.base_script import BaseScript
from smolagents import CodeAgent, HfApiModel, LiteLLMModel
from smolagents.tools import PythonREPLTool
import structlog


class DeweyBaseAgent(BaseScript, CodeAgent):
    """
    Base agent for all Dewey agents using the smolagents framework.
    Extends BaseScript for configuration management and CodeAgent for LLM capabilities.

    Attributes:
        task_type (str): The type of task the agent is designed to perform.
        model_name (str): The name of the language model to use.
    """

    def __init__(
        self, 
        task_type: str, 
        model_name: str = None, 
        config_section: str = "llm"
    ):
        """
        Initializes the DeweyBaseAgent with a task type and model.

        Args:
            task_type (str): The type of task the agent will perform.
            model_name (str, optional): The name of the language model to use.
                Defaults to None, which will use the model specified in the config.
            config_section (str, optional): The config section to use for BaseScript.
                Defaults to "llm".
        """
        # Initialize BaseScript first
        BaseScript.__init__(self, config_section=config_section)
        
        # Get model from config if not provided
        model_name = model_name or self.config.get("default_model", "Qwen/Qwen2.5-Coder-32B-Instruct")
        
        # Use API key from environment or config
        api_key = os.environ.get("DEEPINFRA_API_KEY") or self.config.get("api_key")
        
        # Configure model with appropriate settings
        model = self._configure_model(model_name, api_key)
        
        # Initialize CodeAgent
        CodeAgent.__init__(
            self,
            model=model,
            tools=self._get_tools(),
            system_prompt=self._get_system_prompt(task_type),
            safe_mode=self.config.get("safe_mode", "e2b"),
        )
        
        self.task_type = task_type
        self.logger.info(f"Initialized {self.__class__.__name__} with task type {task_type}")

    def _configure_model(self, model_name: str, api_key: str):
        """
        Configures the language model based on the model name.

        Args:
            model_name (str): The name of the language model to use.
            api_key (str): The API key to use for the model.

        Returns:
            Model: An instance of the appropriate model class.
        """
        # Get model configuration from config
        model_config = self.config.get("models", {}).get(model_name, {})
        temperature = model_config.get("temperature", 0.3)
        max_tokens = model_config.get("max_tokens", 4096)
        
        # Check if model is a local HuggingFace model or API-based
        if model_name.startswith("HF:"):
            model_id = model_name[3:]
            return HfApiModel(
                model_id=model_id, 
                temperature=temperature,
                max_tokens=max_tokens
            )
        else:
            return LiteLLMModel(
                model_id=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    def _get_tools(self) -> List[Any]:
        """
        Returns a list of tools available to the agent.

        This method can be overridden in subclasses to add or remove tools.

        Returns:
            list: A list of tools.
        """
        # Add PythonREPLTool for code execution
        tools = [PythonREPLTool()]
        
        # Get additional tools from config
        additional_tools = self.config.get("tools", {}).get(self.task_type, [])
        if additional_tools:
            self.logger.info(f"Adding {len(additional_tools)} additional tools from config")
            
        return tools

    def _get_system_prompt(self, task_type: str) -> str:
        """
        Returns the system prompt for the agent based on the task type.

        Args:
            task_type (str): The type of task the agent will perform.

        Returns:
            str: The system prompt.
        """
        # Get prompts from config if available
        config_prompts = self.config.get("prompts", {})
        if task_type in config_prompts:
            return config_prompts[task_type]
            
        # Default prompts
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
        
    def run(self, input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes the agent's primary task.
        
        This method implements the BaseScript interface and serves as the main entry point.

        Args:
            input_data (Dict[str, Any], optional): Input data for the agent. Defaults to None.

        Returns:
            Dict[str, Any]: The result of the agent execution.
        """
        self.logger.info(f"Running {self.__class__.__name__} with task type {self.task_type}")
        
        # Process input data
        prompt = None
        if isinstance(input_data, str):
            prompt = input_data
        elif isinstance(input_data, dict) and "prompt" in input_data:
            prompt = input_data["prompt"]
        else:
            prompt = self.config.get("default_prompt", "How can I assist you today?")
            
        # Execute the agent with the prepared prompt
        result = super().run(prompt)
        
        self.logger.info(f"Completed {self.__class__.__name__} execution")
        return {"result": result}