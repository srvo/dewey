"""Agent creator for dynamically generating and configuring AI agents."""

from typing import Any, Dict, List, Optional

from .agent_creator_agent import AgentCreatorAgent  # Import the new agent


async def create_agent(
    purpose: str,
    requirements: List[str],
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Creates a new agent configuration based on requirements using the new AgentCreatorAgent."""
    agent = AgentCreatorAgent()
    return await agent.create_agent(purpose, requirements, context)
