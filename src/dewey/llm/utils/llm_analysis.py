"""Utility module for performing analysis using large language models."""

from typing import Any

from dewey.core.base_script import BaseScript


class LLMAnalysis(BaseScript):
    """
    A script for performing LLM analysis.

    Inherits from BaseScript for standardized configuration and logging.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the LLMAnalysis script.

        Args:
        ----
            **kwargs: Keyword arguments to pass to the BaseScript constructor.

        """
        super().__init__(config_section="llm_analysis", **kwargs)

    def execute(self) -> dict[str, Any]:
        """Execute the LLM analysis.

        Returns
        -------
            A dictionary containing the analysis results.

        Raises
        ------
            Exception: If an error occurs during the analysis.

        """
        try:
            # Access configuration values using self.get_config_value()
            model_name = self.get_config_value("llm_model_name")
            self.logger.info(f"Using LLM model: {model_name}")

            # Perform LLM analysis here
            analysis_results = {"status": "success", "model": model_name}

            self.logger.info("LLM analysis completed successfully.")
            return analysis_results

        except Exception as e:
            self.logger.exception(f"An error occurred during LLM analysis: {e}")
            raise
