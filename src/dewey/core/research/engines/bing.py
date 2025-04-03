from dewey.core.base_script import BaseScript


class Bing(BaseScript):
    """A class for interacting with the Bing search engine."""

    def __init__(self, config_section: str = "bing") -> None:
        """Initializes the Bing search engine class.

        Args:
            config_section (str): The section in the config file to use for this engine.

        """
        super().__init__(config_section=config_section)

    def run(self) -> None:
        """Executes the main logic of the Bing script."""
        self.logger.info("Bing script started.")

        api_key = self.get_config_value("api_key")
        if not api_key:
            self.logger.error("Bing API key is not configured.")
            return

        # Add your Bing search logic here, using self.logger for logging
        # and self.get_config_value() for configuration.
        self.logger.info("Bing script finished.")
