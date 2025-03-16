# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Triage agent for initial analysis and delegation of incoming items."""
from typing import Dict, Any, Optional
from .triage_agent import TriageAgent  # Import the new agent

async def triage(content: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Triage an incoming item using the new TriageAgent."""
    agent = TriageAgent()
    return await agent.triage_item(content, context)
