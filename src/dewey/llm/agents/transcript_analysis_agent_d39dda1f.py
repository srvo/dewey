"""Agent for analyzing meeting transcripts to extract action items and content."""
from .transcript_analysis_agent import TranscriptAnalysisAgent

def analyze_transcript(transcript: str) -> str:
    """Analyzes a meeting transcript to extract actionable insights using the new TranscriptAnalysisAgent."""
    agent = TranscriptAnalysisAgent()
    return agent.analyze_transcript(transcript)
