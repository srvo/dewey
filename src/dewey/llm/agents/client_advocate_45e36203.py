# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Client relationship and task prioritization agent."""
from typing import List, Dict, Any, Optional
from .client_advocate_agent import ClientAdvocateAgent  # Import the new agent

async def analyze_client(profile: Dict[str, Any]) -> str:
    """Analyzes client relationship and generates insights using the new ClientAdvocateAgent."""
    agent = ClientAdvocateAgent()
    return await agent.analyze_client(profile)
