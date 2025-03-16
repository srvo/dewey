# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Wellness monitoring and self-care intervention agent."""
from .self_care_agent import SelfCareAgent  # Import the new agent

async def monitor_and_intervene() -> str | None:
    """Monitors work patterns and intervenes if needed using the new SelfCareAgent."""
    agent = SelfCareAgent()
    return await agent.monitor_and_intervene()
"""Wellness monitoring and self-care intervention agent."""
from .self_care_agent import SelfCareAgent  # Import the new agent

async def monitor_and_intervene() -> str | None:
    """Monitors work patterns and intervenes if needed using the new SelfCareAgent."""
    agent = SelfCareAgent()
    return await agent.monitor_and_intervene()
