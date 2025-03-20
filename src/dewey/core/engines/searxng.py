from dewey.core.base_script import BaseScript
from typing import Any


class SearxNG(BaseScript):
    """
    A class for interacting with a SearxNG instance.
    """

    def __init__(self) -> None:
        """
        Initializes the SearxNG instance.
        """
        super().__init__(config_section='searxng')

    def run(self) -> None:
        """
        Executes the main logic of the SearxNG script.
        """
        self.logger.info("Starting SearxNG script")
        # Example of accessing configuration values
        api_url = self.get_config_value("api_url", "http://localhost:8080")
        self.logger.info(f"SearxNG API URL: {api_url}")

        # Add your SearxNG interaction logic here
        self.logger.info("SearxNG script completed")
