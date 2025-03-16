"""Strategic optimization and prioritization agent for personal productivity."""
from __future__ import annotations

from .sloan_optimizer import SloanOptimizer  # Import the new agent

async def analyze_current_state() -> str:
    """Analyzes current state and provides optimization recommendations using the new SloanOptimizer."""
    agent = SloanOptimizer()
    return await agent.analyze_current_state()

async def optimize_tasks(tasks: list, priorities: list) -> list:
    """Optimizes task ordering based on strategic priorities using the new SloanOptimizer."""
    agent = SloanOptimizer()
    return await agent.optimize_tasks(tasks, priorities)

async def suggest_breaks() -> list:
    """Suggests optimal break times and activities using the new SloanOptimizer."""
    agent = SloanOptimizer()
    return await agent.suggest_breaks()

async def check_work_life_balance() -> dict:
    """Analyzes work-life balance and provide recommendations using the new SloanOptimizer."""
    agent = SloanOptimizer()
    return await agent.check_work_life_balance()
