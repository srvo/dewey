"""Critical analysis and risk identification agent using smolagents."""

from typing import Any

from smolagents import Tool

from dewey.core.base_script import BaseScript


class AdversarialAgent(BaseScript):
    """
    Agent for critical analysis and devil's advocacy.

    Features:
        - Risk identification
        - Critical evaluation
        - Assumption testing
        - Counterargument generation
    """

    def __init__(self) -> None:
        """Initializes the AdversarialAgent with risk analysis tools."""
        super().__init__(config_section="adversarial_agent")
        self.add_tools(
            [
                Tool.from_function(
                    self.analyze_risks,
                    description="Analyzes potential risks and issues in proposals",
                ),
            ],
        )

    def analyze_risks(self, proposal: str) -> str:
        """
        Analyzes potential risks and issues in a proposal.

        Args:
        ----
            proposal: The text of the proposal to analyze.

        Returns:
        -------
            Detailed risk analysis containing potential issues and recommendations.

        """
        prompt = f"Critically analyze this proposal: {proposal}"
        result = self.run_llm(prompt)
        return result

    def run(self, input_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Executes the agent's primary task.

        Args:
        ----
            input_data: Input data for the agent. Defaults to None.

        Returns:
        -------
            The result of the agent execution with risk analysis.

        """
        self.logger.info("Starting Adversarial Agent analysis...")

        # Perform analysis if input data is provided
        if input_data and "proposal" in input_data:
            proposal = input_data["proposal"]
            result = self.analyze_risks(proposal)
        else:
            result = "No proposal provided for analysis."
            self.logger.warning(result)

        self.logger.info("Adversarial Agent analysis completed.")
        return {"analysis_result": result}

    def run_llm(self, prompt: str) -> str:
        """
        Runs the LLM with the given prompt.

        Args:
        ----
            prompt: The prompt to send to the LLM.

        Returns:
        -------
            The LLM's response.

        """
        try:
            response = self.llm(prompt)
            return response
        except Exception as e:
            self.logger.exception(f"Error running LLM: {e}")
            return f"LLM Error: {e}"

    def execute(self) -> None:
        """
        Executes the adversarial analysis based on configuration.

        This method retrieves a proposal from the configuration, if available,
        and performs a risk analysis. The result is logged.
        """
        proposal = self.get_config_value("proposal")
        if proposal:
            self.logger.info("Executing Adversarial Agent analysis from config...")
            analysis_result = self.analyze_risks(proposal)
            self.logger.info(f"Analysis Result: {analysis_result}")
        else:
            self.logger.warning("No proposal found in configuration.")
