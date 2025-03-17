"""Mock LLM client for testing."""


class LLMClient:
    """A mock LLM client that returns predefined responses."""

    def __init__(self):
        self.default_response = {
            "content": "Mock LLM response",
            "metadata": {"model": "mock-model", "tokens": 10, "confidence": 0.95},
        }

    def generate(self, prompt: str) -> dict:
        """Generate a mock response."""
        return self.default_response

    def analyze(self, text: str) -> dict:
        """Analyze text and return mock analysis."""
        return {
            "sentiment": "neutral",
            "topics": ["mock_topic_1", "mock_topic_2"],
            "summary": "Mock summary of the text.",
            "confidence": 0.9,
        }
