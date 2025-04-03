from dewey.core.base_script import BaseScript


class SecEngine(BaseScript):
    """A class for the SEC Engine."""

    def __init__(self) -> None:
        """Initializes the SecEngine class."""
        super().__init__(config_section="sec_engine")

    def execute(self) -> None:
        """Executes the main logic of the SEC Engine."""
        self.logger.info("Starting SEC Engine...")
        # Example of accessing configuration values
        api_key = self极.get_config_value("api_key")
        self.logger.info(f"API Key: {api_key}")
        # Add your main logic here
        self.logger.info("SEC Engine finished.")

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead."
        )
        self.execute()
