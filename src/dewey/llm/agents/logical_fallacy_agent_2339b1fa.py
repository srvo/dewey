# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Logical fallacy detection agent for analyzing reasoning and arguments."""
from .logical_fallacy_agent import LogicalFallacyAgent  # Import the new agent

async def analyze_text(text: str, context: str | None = None) -> str:
    """Analyzes text for logical fallacies using the new LogicalFallacyAgent."""
    agent = LogicalFallacyAgent()
    return await agent.analyze_text(text, context)
