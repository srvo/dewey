"""Triage agent for initial analysis and delegation of incoming items using smolagents."""
from typing import List, Dict, Any, Optional
from smolagents import Tool
from .base_agent import DeweyBaseAgent

class TriageAgent(DeweyBaseAgent):
    """
    Agent for triaging incoming items and determining appropriate actions.
    """

    def __init__(self):
        """Initializes the TriageAgent."""
        super().__init__(task_type="triage")
        self.add_tools([
            Tool.from_function(self.triage_item, description="Analyzes an item and determines appropriate actions.")
        ])

    def triage_item(self, content: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Analyzes an item and determines appropriate actions.

        Args:
            content (str): The content to analyze.
            context (Optional[Dict[str, Any]], optional): Optional context for the analysis. Defaults to None.

        Returns:
            str: A string containing the triage results.
        """
        prompt = f"""
        Analyze the following item:
        {content}

        Context: {context or "None"}
        """
        result = self.run(prompt)
        return result
