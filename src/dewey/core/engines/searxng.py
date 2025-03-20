from dewey.core.base_script import BaseScript


class SearxNG(BaseScript):
    """
    A class for interacting with a SearxNG instance.
    """

    def __init__(self) -> None:
        """
        Initializes the SearxNG instance.
        """
        super().__init__(config_section="searxng")

    def run(self) -> None:
        """
        Executes the main logic of the SearxNG script.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If there is an error during the SearxNG script execution.
        """
        self.logger.info("Starting SearxNG script")
        try:
            # Example of accessing configuration values
            api_url = self.get_config_value("api_url", "http://localhost:8080")
            self.logger.info(f"SearxNG API URL: {api_url}")

            # Add your SearxNG interaction logic here
            self.logger.info("SearxNG script completed")
        except Exception as e:
            self.logger.error(f"Error during SearxNG script execution: {e}")
            raise
