"""Test agent for AI interaction."""

from .philosophical_agent import PhilosophicalAgent  # Import the new agent

async def test_philosophical_discussion() -> str | None:
    """Test the philosophical agent with a question about consciousness."""
    try:
        agent = PhilosophicalAgent()
        prompt = """What is the nature of consciousness and how does it relate to the physical brain?
        Consider both scientific and philosophical perspectives."""
        result = await agent.discuss_philosophy(prompt)
        return result
    except Exception:
        return None
