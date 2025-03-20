from dewey.core.base_script import BaseScript


class ConsolidatedGmailApi(BaseScript):
    """
    A class for interacting with the Gmail API.

    This class inherits from BaseScript and provides methods for
    consolidating and managing Gmail interactions.
    """

    def __init__(self) -> None:
        """
        Initializes the ConsolidatedGmailApi class.
        """
        super().__init__(config_section='consolidated_gmail_api')

    def run(self) -> None:
        """
        Executes the main logic of the ConsolidatedGmailApi script.
        """
        self.logger.info("Starting Consolidated Gmail API script")
        # Example of accessing configuration values
        api_key = self.get_config_value("api_key")
        if api_key:
            self.logger.debug("API key loaded from config")
        else:
            self.logger.warning("API key not found in config")

        # Add your main script logic here
        self.logger.info("Consolidated Gmail API script finished")
