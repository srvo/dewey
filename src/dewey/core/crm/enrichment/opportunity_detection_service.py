from dewey.core.base_script import BaseScript


class OpportunityDetectionService(BaseScript):
    """Detects opportunities from a given text."""

    def __init__(self):
        """Initializes the OpportunityDetectionService."""
        super().__init__(config_section="opportunity_detection")

    def run(self) -> None:
        """Runs the opportunity detection service."""
        text = "This is a sample text with a demo opportunity."
        opportunities = self.detect_opportunities(text)
        self.logger.info(f"Detected opportunities: {opportunities}")

    def detect_opportunities(self, text: str) -> list[str]:
        """Detects opportunities in the given text based on regex patterns
        defined in the configuration.

        Args:
            text (str): The text to analyze.

        Returns:
            list[str]: A list of detected opportunity types.

        """
        opportunity_types = self.get_config_value("regex_patterns.opportunity")
        detected_opportunities = []

        if opportunity_types:
            for opportunity_type, pattern in opportunity_types.items():
                if self._check_opportunity(text, pattern):
                    detected_opportunities.append(opportunity_type)

        return detected_opportunities

    def _check_opportunity(self, text: str, pattern: str) -> bool:
        """Checks if a specific opportunity exists in the text based on the given regex pattern.

        Args:
            text (str): The text to analyze.
            pattern (str): The regex pattern to search for.

        Returns:
            bool: True if the opportunity is found, False otherwise.

        """
        import re

        return bool(re.search(pattern, text, re.IGNORECASE))
