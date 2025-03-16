"""Test agent for AI interaction."""

from .base import SyzygyAgent


class PhilosophicalAgent(SyzygyAgent):
    """Test agent for philosophical discussions using advanced AI models."""

    def __init__(self) -> None:
        """Initialize the philosophical agent with standard model configuration."""
        super().__init__(
            task_type="philosophical_discussion",
            model="mixtral-8x7b",
            complexity=2,
        )

    def get_system_prompt(self) -> str:
        """Return the system prompt for philosophical discussions."""
        return """You are a philosophical AI assistant engaging in deep discussions about consciousness,
        existence, and the nature of reality. Consider multiple perspectives, historical context,
        and practical implications in your responses."""


async def test_philosophical_discussion():
    """Test the philosophical agent with a question about consciousness."""
    try:
        agent = PhilosophicalAgent()
        prompt = """What is the nature of consciousness and how does it relate to the physical brain?
        Consider both scientific and philosophical perspectives."""
        return await agent.run(prompt)
    except Exception:
        return None
