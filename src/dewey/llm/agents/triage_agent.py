"""Initial analysis and routing agent for incoming items."""
from typing import Dict, Any, Optional
from smolagents import Tool
from .base_agent import DeweyBaseAgent

class TriageAgent(DeweyBaseAgent):
    """Analyzes and routes incoming items to appropriate handlers."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the TriageAgent with configuration.

        Args:
            config: Configuration dictionary from dewey.yaml
        """
        super().__init__(config=config, task_type="triage")
        self.add_tools([
            Tool.from_function(
                self.analyze_item,
                description="Analyzes incoming items and determines appropriate actions",
                args_schema={
                    "content": {
                        "type": "string",
                        "description": "Content of the item to analyze"
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context for analysis"
                    }
                }
            )
        ])

    def analyze_item(self, content: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze incoming item and determine appropriate routing.
        
        Args:
            content: Text content of the item
            context: Additional analysis context
            
        Returns:
            Dictionary containing analysis results and routing instructions
        """
        prompt = f"""Analyze this incoming item and determine appropriate actions:
        {content}
        
        Context: {context or 'None'}
        
        Return JSON with:
        - category (str)
        - urgency (1-5)
        - recommended_actions (list)
        - suggested_handlers (list)
        - follow_up_required (bool)
        - analysis_summary (str)
        """
        
        return self.generate_response(
            prompt=prompt,
            response_format={"type": "json_object"},
            temperature=self.config.get("temperature", 0.2),
            max_tokens=600
        )
