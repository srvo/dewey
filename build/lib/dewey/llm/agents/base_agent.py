"""Base agent configuration using smolagents framework."""
import os
from smolagents import CodeAgent, HfApiModel, LiteLLMModel
from smolagents.tools import PythonREPLTool

class DeweyBaseAgent(CodeAgent):
    """
    Base agent for all Dewey agents using the smolagents framework.

    Attributes:
        task_type (str): The type of task the agent is designed to perform.
        model_name (str): The name of the language model to use.
    """

    def __init__(self, task_type: str, model_name: str = "Qwen/Qwen2.5-Coder-32B-Instruct"):
        """
        Initializes the DeweyBaseAgent with a task type and model.

        Args:
            task_type (str): The type of task the agent will perform.
            model_name (str, optional): The name of the language model to use.
                Defaults to "Qwen/Qwen2.5-Coder-32B-Instruct".
        """

        # Use LiteLLMModel for accessing models via API keys
        model = LiteLLMModel(
            model_id=model_name,
            api_key=os.environ.get("DEEPINFRA_API_KEY"),
            temperature=0.3,
            max_tokens=4096,
        )

        super().__init__(
            model=model,
            tools=self._get_tools(),
            system_prompt=self._get_system_prompt(task_type),
            safe_mode="e2b",  # Use a sandboxed environment for code execution
        )

    def _get_tools(self):
        """
        Returns a list of tools available to the agent.

        This method can be overridden in subclasses to add or remove tools.

        Returns:
            list: A list of tools.
        """
        # Add PythonREPLTool for code execution
        return [PythonREPLTool()]

    def _get_system_prompt(self, task_type: str) -> str:
        """
        Returns the system prompt for the agent based on the task type.

        Args:
            task_type (str): The type of task the agent will perform.

        Returns:
            str: The system prompt.
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
