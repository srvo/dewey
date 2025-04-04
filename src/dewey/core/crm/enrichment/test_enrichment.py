from typing import Any

from dewey.core.base_script import BaseScript


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

        Args:
        ----
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        super().__init__(*args, config_section="test_enrichment", **kwargs)
        self.name = "TestEnrichment"
        self.description = "Tests the CRM enrichment process."

    def execute(self) -> None:
        """
        Executes the test enrichment process.

        This method retrieves an example configuration value and logs
        messages to indicate the start and completion of the test
        enrichment process.

        Args:
        ----
            None

        Returns:
        -------
            None

        Raises:
        ------
            Exception: If there is an error during the enrichment process.

        """
        self.logger.info("Starting test enrichment process.")

        # Example of accessing configuration values
        example_config_value = self.get_config_value("example_config", "default_value")
        self.logger.info(f"Example config value: {example_config_value}")

        self.logger.info("Test enrichment process completed.")

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()
