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
        """Executes the main logic of the Apitube script."""
        self.logger.info("Starting Apitube script...")

        api_key = self.get_config_value("api_key")
        if not api_key:
            self.logger.error("API key not found in configuration.")
            return

        self.logger.info(f"API Key: {api_key}")
        self.logger.info("Apitube script completed.")

    def execute(self) -> None:
        """
        Executes the Apitube API interaction.

        This method retrieves the API key from the configuration and logs it.
        In a real implementation, this method would use the API key to
        interact with the Apitube API and perform some action.
        """
        self.logger.info("Executing Apitube script...")

        api_key = self.get_config_value("api_key")
        if not api_key:
            self.logger.error("API key not found in configuration.")
            return

        self.logger.debug(f"Apitube API Key: {api_key}")
        self.logger.info("Apitube script execution completed.")
