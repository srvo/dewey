"""Content generation and refinement agent in Sloan's voice."""
from typing import List, Dict, Any, Optional
from .sloane_ghostwriter_agent import SloaneGhostwriterAgent  # Import the new agent

async def generate_content(brief: str) -> str:
    """Generates content based on a brief using the new SloaneGhostwriterAgent."""
    agent = SloaneGhostwriterAgent()
    return await agent.generate_content(brief)
