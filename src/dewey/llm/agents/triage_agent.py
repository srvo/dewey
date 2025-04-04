"""Triage agent for initial analysis and delegation of incoming items using smolagents."""

from typing import Any

from smolagents import Tool

from dewey.core.base_script import BaseScript


class TriageAgent(BaseScript):
    """
    Agent for triaging incoming items and determining appropriate actions.

    Features:
        - Priority assessment
        - Content classification
        - Action recommendation
        - Delegation suggestions
        - Response time estimation
    """

    def __init__(self) -> None:
        """Initializes the TriageAgent."""
        super().__init__(config_section="triage_agent")
        self.add_tools(
            [
                Tool.from_function(
                    self.triage_item,
                    description="Analyzes an item and determines appropriate actions.",
                ),
            ],
        )

    def run(self, prompt: str) -> dict[str, Any]:
        """
        Runs the triage agent with the given prompt.

        Args:
        ----
            prompt: The prompt to use for triaging.

        Returns:
        -------
            The result of the agent's run.

        """
        return self.agent.run(prompt)

    def triage_item(
        self, content: str, context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Analyzes an item and determines appropriate actions.

        Args:
        ----
            content: The content to analyze.
            context: Optional context for the analysis. Defaults to None.

        Returns:
        -------
            Triage results containing priority, classification, and recommended actions.

        """
        self.logger.info("Triage item started", content=content, context=context)
        context_str = str(context) if context else "No additional context"
        prompt = f"""
        Analyze the following item:

        CONTENT:
        {content}

        CONTEXT:
        {context_str}

        Provide:
        1. Priority assessment (High/Medium/Low)
        2. Content classification
        3. Recommended actions
        4. Delegation suggestions
        5. Estimated response time
        """
        result = self.run(prompt)
        self.logger.info("Triage item completed", result=result)
        return result

    def execute(self, prompt: str) -> dict[str, Any]:
        """
        Executes the triage agent with the given prompt.

        Args:
        ----
            prompt: The prompt to use for triaging.

        Returns:
        -------
            The result of the agent's run.

        """
        self.logger.info(f"Executing triage agent with prompt: {prompt}")
        result = self.run(prompt)
        self.logger.info(f"Triage agent completed. Result: {result}")
        return result
