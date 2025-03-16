"""Content generation and refinement agent in Sloan's voice using smolagents."""
from typing import List, Dict, Any, Optional
from smolagents import Tool
from .base_agent import DeweyBaseAgent

class SloaneGhostwriterAgent(DeweyBaseAgent):
    """
    Agent for generating and refining content in Sloan's voice.
    """

    def __init__(self):
        """Initializes the SloaneGhostwriterAgent."""
        super().__init__(task_type="content_generation")
        self.add_tools([
            Tool.from_function(self.generate_content, description="Generates content based on a brief.")
        ])

    def generate_content(self, brief: str) -> str:
        """
        Generates content based on a brief.

        Args:
            brief (str): The content brief.

        Returns:
            str: The generated content.
        """
        prompt = f"""
        Generate content based on the following brief:
        {brief}
        """
        result = self.run(prompt)
        return result
