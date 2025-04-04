from typing import Any

from dewey.core.base_script import BaseScript


class ResearchUtils(BaseScript):
    """
    A collection of utility functions for research workflows within Dewey.

    This class inherits from BaseScript and provides methods for various
    research-related tasks, such as data processing, analysis, and reporting.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the ResearchUtils module."""
        super().__init__(
            *args,
            config_section="research_utils",
            requires_db=False,
            enable_llm=False,
            **kwargs,
        )
        self.name = "ResearchUtils"
        self.description = "Provides utility functions for research workflows."

    def run(self) -> None:
        """Executes the main logic of the research utility."""
        self.logger.info("Starting ResearchUtils...")

        # Example usage of config and logging
        example_config_value = self.get_config_value("example_config", "default_value")
        self.logger.info(f"Example config value: {example_config_value}")

        self._example_utility_function()

        self.logger.info("ResearchUtils completed.")

    def _example_utility_function(self) -> None:
        """
        An example utility function.

        This function demonstrates how to use the logger and other Dewey
        components within a utility function.
        """
        self.logger.info("Executing example utility function...")
        # Add your utility logic here
        self.logger.info("Example utility function completed.")

    def get_data(self, data_source: str) -> Any | None:
        """
        Retrieves data from the specified data source.

        Args:
        ----
            data_source: The name of the data source to retrieve data from.

        Returns:
        -------
            The data retrieved from the data source, or None if the data source
            is not found or an error occurs.

        """
        try:
            # Simulate data retrieval based on config
            data = self.get_config_value(data_source)
            if data:
                self.logger.info(f"Successfully retrieved data from {data_source}.")
                return data
            self.logger.warning(f"No data found for data source: {data_source}.")
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving data from {data_source}: {e}")
            return None
