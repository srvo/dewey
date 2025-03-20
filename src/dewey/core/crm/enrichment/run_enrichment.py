from typing import Any

from dewey.core.base_script import BaseScript


class RunEnrichment(BaseScript):
    """
    A module for running enrichment tasks within Dewey's CRM.

    This module inherits from BaseScript and provides a standardized
    structure for enrichment scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(
        self,
        name: str = "RunEnrichment",
        description: str = "Runs enrichment tasks.",
    ) -> None:
        """
        Initializes the RunEnrichment module.

        Args:
            name: The name of the module.
            description: A description of the module.
        """
        super().__init__(name=name, description=description, config_section="enrichment")

    def run(self) -> None:
        """
        Executes the primary logic of the enrichment script.
        """
        self.logger.info("Starting enrichment process...")

        # Access configuration values using self.get_config_value()
        api_key = self.get_config_value("api_key")

        if api_key:
            self.logger.info("API key found in configuration.")
            # Perform enrichment tasks here
        else:
            self.logger.warning(
                "API key not found in configuration. Enrichment tasks will not be executed."
            )

        self.logger.info("Enrichment process completed.")
