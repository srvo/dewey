"""Critical analysis and risk identification agent using smolagents."""
from typing import Dict, Any, Optional
import structlog
from smolagents import Tool
from .base_agent import DeweyBaseAgent

logger = structlog.get_logger(__name__)

class AdversarialAgent(DeweyBaseAgent):
    """Agent for critical analysis and devil's advocacy."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AdversarialAgent with configuration.

        Args:
            config: Configuration dictionary from dewey.yaml
        """
        super().__init__(config=config, task_type="critical_analysis")
        self.add_tools([
            Tool.from_function(
                self.analyze_risks,
                description="Analyzes potential risks and issues in proposals",
                args_schema={
                    "proposal": {
                        "type": "string",
                        "description": "The proposal text to analyze"
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context for analysis"
                    }
                }
            )
        ])

    def analyze_risks(self, proposal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze potential risks and issues in a proposal.

        Args:
            proposal: The text of the proposal to analyze
            context: Additional context for analysis

        Returns:
            Dictionary containing risk analysis with:
            - identified_risks (list)
            - severity_levels (dict)
            - mitigation_strategies (list)
            - overall_risk_score (float)
        """
        prompt = f"""Critically analyze this proposal and identify risks:
        {proposal}
        
        Context: {context or 'None'}
        
        Return JSON with:
        - identified_risks (list)
        - severity_levels (dict)
        - mitigation_strategies (list)
        - overall_risk_score (float)
        """
        
        return self.generate_response(
            prompt=prompt,
            response_format={"type": "json_object"},
            temperature=self.config.get("temperature", 0.3),
            max_tokens=800
        )
