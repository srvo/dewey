"""Critical analysis and risk identification agent using smolagents."""
from typing import List, Dict, Any, Optional
from smolagents import Tool
from .base_agent import DeweyBaseAgent

class AdversarialAgent(DeweyBaseAgent):
    """
    Agent for critical analysis and devil's advocacy.
    """

    def __init__(self):
        """Initializes the AdversarialAgent."""
        super().__init__(task_type="critical_analysis")
        self.add_tools([
            Tool.from_function(self.analyze_risks, description="Analyzes potential risks and issues.")
        ])

    def analyze_risks(self, proposal: str) -> str:
        """
        Analyzes potential risks and issues.

        Args:
            proposal (str): The proposal to analyze.

        Returns:
            str: The risk analysis.
        """
        prompt = f"""
        Critically analyze this proposal:
        {proposal}
        """
        result = self.run(prompt)
        return result
"""Critical analysis and risk identification agent using smolagents."""
from typing import List, Dict, Any, Optional
from smolagents import Tool
from .base_agent import DeweyBaseAgent

class AdversarialAgent(DeweyBaseAgent):
    """
    Agent for critical analysis and devil's advocacy.
    """

    def __init__(self):
        """Initializes the AdversarialAgent."""
        super().__init__(task_type="critical_analysis")
        self.add_tools([
            Tool.from_function(self.analyze_risks, description="Analyzes potential risks and issues.")
        ])

    def analyze_risks(self, proposal: str) -> str:
        """
        Analyzes potential risks and issues.

        Args:
            proposal (str): The proposal to analyze.

        Returns:
            str: The risk analysis.
        """
        prompt = f"""
        Critically analyze this proposal:
        {proposal}
        """
        result = self.run(prompt)
        return result
