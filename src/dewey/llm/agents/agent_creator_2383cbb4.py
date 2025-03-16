# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Agent creator for dynamically generating and configuring AI agents."""
from .agent_creator import AgentCreatorAgent  # Import the new agent

async def create_agent(purpose: str, requirements: list[str], context: dict | None = None) -> str:
    """Creates a new agent configuration based on requirements using the new AgentCreatorAgent."""
    agent = AgentCreatorAgent()
    return await agent.create_agent(purpose, requirements, context)
