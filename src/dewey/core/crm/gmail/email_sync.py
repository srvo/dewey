from dewey.core.base_script import BaseScript


class EmailSync(BaseScript):
    """
    A module for synchronizing emails from Gmail.

    This module inherits from BaseScript and provides a standardized
    structure for email synchronization scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, *args, **kwargs):
        """Initializes the EmailSync module."""
        super().__init__(*args, **kwargs)

    def run(self) -> None:
        """
        Executes the email synchronization process.
        """
        self.logger.info("Starting email synchronization...")

        # Example of accessing configuration values
        api_key = self.get_config_value("gmail_api_key")
        if api_key:
            self.logger.debug("Gmail API key found in configuration.")
        else:
            self.logger.warning("Gmail API key not found in configuration.")

        # Add your email synchronization logic here
        self.logger.info("Email synchronization completed.")
