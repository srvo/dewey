from dewey.core.base_script import BaseScript
from typing import Any

class TestEnrichment(BaseScript):
    """
    A module for testing enrichment processes within Dewey's CRM.

    This module inherits from BaseScript and provides a standardized
    structure for testing enrichment scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initializes the TestEnrichment module.
        """
        super().__init__(*args, **kwargs)
        self.name = "TestEnrichment"
        self.description = "Tests the CRM enrichment process."

    def run(self) -> None:
        """
        Executes the test enrichment process.
        """
        self.logger.info("Starting test enrichment process.")

        # Example of accessing configuration values
        example_config_value = self.get_config_value("example_config", "default_value")
        self.logger.info(f"Example config value: {example_config_value}")

        self.logger.info("Test enrichment process completed.")
