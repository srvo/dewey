from dewey.core.base_script import BaseScript


class Apitube(BaseScript):
    """
    A class for interacting with the Apitube API.

    Inherits from BaseScript to provide standardized access to configuration,
    logging, and other utilities.
    """

    def __init__(self):
        """
        Initializes the Apitube class.

        Calls the superclass constructor to initialize the base script.
        """
        super().__init__(config_section="apitube")

    def run(self) -> None:
        """
        Executes the main logic of the Apitube script.
        """
        self.logger.info("Starting Apitube script...")

        api_key = self.get_config_value("api_key")
        if not api_key:
            self.logger.error("API key not found in configuration.")
            return

        self.logger.info(f"API Key: {api_key}")
        self.logger.info("Apitube script completed.")
