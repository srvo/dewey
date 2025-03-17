
# Refactored from: llm_client
# Date: 2025-03-16T16:19:08.885550
# Refactor Version: 1.0
```python
"""Mock LLM client for testing."""


class LLMClient:
    """A mock LLM client that returns predefined responses."""

    def __init__(self) -> None:
        """Initializes the LLMClient with a default response."""
        self.default_response: dict[str, any] = {
            "content": "Mock LLM response",
            "metadata": {"model": "mock-model", "tokens": 10, "confidence": 0.95},
        }

    def generate(self, prompt: str) -> dict[str, any]:
        """Generate a mock response.

        Args:
            prompt: The input prompt (not used in this mock implementation).

        Returns:
            A dictionary containing the mock LLM response.
        """
        return self.default_response

    def analyze(self, text: str) -> dict[str, any]:
        """Analyze text and return mock analysis.

        Args:
            text: The text to analyze (not used in this mock implementation).

        Returns:
            A dictionary containing the mock analysis results.
        """
        analysis_result: dict[str, any] = {
            "sentiment": "neutral",
            "topics": ["mock_topic_1", "mock_topic_2"],
            "summary": "Mock summary of the text.",
            "confidence": 0.9,
        }
        return analysis_result
```
