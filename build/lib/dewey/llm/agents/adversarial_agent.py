"""Critical analysis and risk identification agent using smolagents."""
from typing import List, Dict, Any, Optional
import structlog
from smolagents import Tool
from .base_agent import DeweyBaseAgent

logger = structlog.get_logger(__name__)

class AdversarialAgent(DeweyBaseAgent):
    """Agent for critical analysis and devil's advocacy.
    
    Attributes:
        task_type: The type of task the agent performs (critical_analysis)
    """

    def __init__(self) -> None:
        """Initializes the AdversarialAgent with risk analysis tool."""
        super().__init__(task_type="critical_analysis")
        self.add_tools([
            Tool.from_function(
                self.analyze_risks, 
                description="Analyzes potential risks and issues in proposals"
            )
        ])

    def analyze_risks(self, proposal: str) -> str:
        """Analyzes potential risks and issues in a proposal.

        Args:
            proposal: The text of the proposal to analyze

        Returns:
            Detailed risk analysis containing potential issues and recommendations
        """
        prompt = f"Critically analyze this proposal: {proposal}"
        result = self.run(prompt)
        return result
