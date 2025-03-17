"""Philosophical agent using smolagents."""
from smolagents import Tool
from .base_agent import DeweyBaseAgent

class PhilosophicalAgent(DeweyBaseAgent):
    """
    Test agent for philosophical discussions using advanced AI models.
    """

    def __init__(self):
        """Initializes the PhilosophicalAgent."""
        super().__init__(task_type="philosophical_discussion")
        self.add_tools([
            Tool.from_function(self.discuss_philosophy, description="Engages in philosophical discussions.")
        ])

    def discuss_philosophy(self, topic: str) -> str:
        """
        Engages in philosophical discussions.

        Args:
            topic (str): The topic to discuss.

        Returns:
            str: A string containing the philosophical discussion.
        """
        prompt = f"""
        Engage in a philosophical discussion about: {topic}
        """
        result = self.run(prompt)
        return result
