from dewey.core.base_script import BaseScript


class SecEngine(BaseScript):
    """
    A class for the SEC Engine.
    """

    def __init__(self) -> None:
        """
        Initializes the SecEngine class.
        """
        super().__init__(config_section='sec_engine')

    def run(self) -> None:
        """
        Executes the main logic of the SEC Engine.
        """
        self.logger.info("Starting SEC Engine...")
        # Example of accessing configuration values
        api_key = self.get_config_value("api_key")
        self.logger.info(f"API Key: {api_key}")
        # Add your main logic here
        self.logger.info("SEC Engine finished.")
