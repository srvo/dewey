"""Meeting transcript analysis and insight extraction agent."""
from typing import Dict, Any
from smolagents import Tool
from .base_agent import DeweyBaseAgent

class TranscriptAnalysisAgent(DeweyBaseAgent):
    """Extracts actionable insights and content opportunities from meeting transcripts."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config=config, task_type="transcript_analysis")
        self.add_tools([
            Tool.from_function(
                self.analyze_meeting,
                description="Analyzes meeting transcripts for action items and content opportunities",
                args_schema={
                    "transcript": {
                        "type": "string",
                        "description": "Full text of the meeting transcript"
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional meeting context and metadata"
                    }
                }
            )
        ])

    def analyze_meeting(self, transcript: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze meeting transcript for insights and opportunities.
        
        Args:
            transcript: Text content of the meeting transcript
            context: Additional meeting context and metadata
            
        Returns:
            Dictionary containing analysis results and recommendations
        """
        prompt = f"""Analyze this meeting transcript:
        {transcript}
        
        Context: {context or 'None'}
        
        Return JSON with:
        - action_items (list)
        - content_opportunities (list)
        - key_decisions (list)
        - follow_up_actions (list)
        - sentiment_analysis (dict)
        - meeting_summary (str)
        """
        
        return self.generate_response(
            prompt=prompt,
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1200
        )
