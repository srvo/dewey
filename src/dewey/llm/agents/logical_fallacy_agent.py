"""Logical fallacy detection agent using smolagents."""
from typing import List, Dict, Any, Optional
from smolagents import Tool
from .base_agent import DeweyBaseAgent

class LogicalFallacyAgent(DeweyBaseAgent):
    """
    Agent for detecting and analyzing logical fallacies in text.
    """

    def __init__(self):
        """Initializes the LogicalFallacyAgent."""
        super().__init__(task_type="logical_fallacy_detection")
        self.add_tools([
            Tool.from_function(self.analyze_text, description="Analyzes text for logical fallacies.")
        ])

    def analyze_text(self, text: str, context: Optional[str] = None) -> str:
        """
        Analyzes text for logical fallacies.

        Args:
            text (str): The text to analyze.
            context (Optional[str], optional): Optional context for the analysis. Defaults to None.

        Returns:
            str: A string containing the analysis results.
        """
        prompt = f"""
        Analyze the following text for logical fallacies:
        {text}

        Context: {context or "None"}
        """
        result = self.run(prompt)
        return result
