"""Wellness monitoring and self-care intervention agent using smolagents."""

from typing import Any, Dict, List, Optional

from smolagents import Tool

from dewey.core.base_script import BaseScript
from dewey.llm.agents.base_agent import BaseAgent


class SelfCareAgent(BaseAgent):
    """Agent for monitoring user wellness and suggesting self-care interventions.

    Features:
        - Work pattern monitoring
        - Break timing recommendations
        - Wellness activity suggestions
        - Stress indicator detection
        - Productivity optimization
    """

    def __init__(self) -> None:
        """Initializes the SelfCareAgent."""
        super().__init__(task_type="wellness_monitoring")
        self.add_tools(
            [
                Tool.from_function(
                    self.monitor_and_intervene,
                    description="Monitors work patterns and intervenes if needed.",
                ),
                Tool.from_function(
                    self.suggest_break,
                    description="Suggests a break based on current work patterns.",
                ),
            ]
        )

    def execute(self, prompt: str) -> dict[str, Any]:
        """Executes the agent with the given prompt.

        Args:
            prompt: The prompt to run the agent with.

        Returns:
            The result of running the agent.

        """
        self.logger.info(f"Executing SelfCareAgent with prompt: {prompt}")
        result = self.run(prompt)
        self.logger.info(f"SelfCareAgent completed with result: {result}")
        return result

    def run(self, prompt: str) -> dict[str, Any]:
        """Runs the agent with the given prompt.

        Args:
            prompt: The prompt to run the agent with.

        Returns:
            The result of running the agent.

        """
        return super().run(prompt)

    def monitor_and_intervene(
        self, work_patterns: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Monitors work patterns and intervenes if needed.

        Args:
            work_patterns: Information about recent work patterns.
                Defaults to None.

        Returns:
            Assessment and recommendations for self-care.

        """
        self.logger.info("Monitoring work patterns and intervening if needed.")
        patterns_str = (
            str(work_patterns) if work_patterns else "No specific patterns provided"
        )
        prompt = f"""
        Monitor these work patterns and suggest self-care interventions:
        {patterns_str}

        Provide:
        1. Pattern assessment
        2. Potential wellness concerns
        3. Self-care recommendations
        4. Break timing suggestions
        5. Productivity optimization tips
        """
        result = self.run(prompt)
        return result

    def suggest_break(
        self,
        work_duration: int = 0,
        break_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Suggests a break based on current work patterns.

        Args:
            work_duration: Minutes of continuous work. Defaults to 0.
            break_history: Recent break history.
                Defaults to None.

        Returns:
            Break recommendation with activity suggestion and duration.

        """
        self.logger.info("Suggesting a break based on current work patterns.")
        history_str = str(break_history) if break_history else "No recent breaks"
        prompt = f"""
        Suggest an optimal break based on:
        - Work duration: {work_duration} minutes
        - Break history: {history_str}

        Provide:
        1. Recommended break duration
        2. Suggested break activities
        3. Optimal timing
        4. Expected benefits
        """
        result = self.run(prompt)
        return result
