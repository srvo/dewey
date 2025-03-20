from dewey.core.base_script import BaseScript
import logging
from typing import Any

class Bing(BaseScript):
    """
    A class for interacting with the Bing search engine.
    """

    def __init__(self) -> None:
        """
        Initializes the Bing search engine class.
        """
        super().__init__(config_section='bing')

    def run(self) -> None:
        """
        Executes the main logic of the Bing script.
        """
        api_key = self.get_config_value("api_key")
        if not api_key:
            self.logger.error("Bing API key is not configured.")
            return

        self.logger.info("Bing script started.")
        # Add your Bing search logic here, using self.logger for logging
        # and self.get_config_value() for configuration.
        self.logger.info("Bing script finished.")
