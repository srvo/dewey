"""Critical analysis and risk identification agent using smolagents."""
from typing import List, Dict, Any, Optional
import structlog
from smolagents import Tool

from .base_agent import DeweyBaseAgent
from dewey.core.base_script import BaseScript

logger = structlog.get_logger(__name__)

class AdversarialAgent(BaseScript, DeweyBaseAgent):
    """Agent for critical analysis and devil's advocacy.
    
    Features:
    - Risk identification
    - Critical evaluation
    - Assumption testing
    - Counterargument generation
    """

    def __init__(self) -> None:
        """Initializes the AdversarialAgent with risk analysis tools."""
        super().__init__(task_type="critical_analysis")
        self.add_tools([
            Tool.from_function(
                self.analyze_risks, 
                description="Analyzes potential risks and issues in proposals"
            )
        ])

    def analyze_risks(self, proposal: str) -> str:
        """
        Analyzes potential risks and issues in a proposal.

        Args:
            proposal (str): The text of the proposal to analyze

        Returns:
            str: Detailed risk analysis containing potential issues and recommendations
        """
        prompt = f"Critically analyze this proposal: {proposal}"
        result = self.run(prompt)
        return result

    def run(self, input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes the agent's primary task.
        
        Args:
            input_data (Dict[str, Any], optional): Input data for the agent. Defaults to None.

        Returns:
            Dict[str, Any]: The result of the agent execution with risk analysis.
        """
        self.logger.info("Starting Adversarial Agent analysis...")
        
        # Call the parent's run method
        result = super().run(input_data)
        
        self.logger.info("Adversarial Agent analysis completed.")
        return result
