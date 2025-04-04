from dewey.core.base_script import BaseScript


class YahooFinanceEngine(BaseScript):
    """
    A class for fetching and processing data from Yahoo Finance.

    Inherits from BaseScript to provide standardized access to configuration,
    logging, and other utilities.
    """

    def __init__(self) -> None:
        """Initializes the YahooFinanceEngine."""
        super().__init__(config_section="research_engines.yahoo_finance")

    def execute(self) -> None:
        """
        Executes the main logic of the Yahoo Finance engine.

        Args:
        ----
            None

        Returns:
        -------
            None

        Raises:
        ------
            None

        """
        self.logger.info("Starting Yahoo Finance engine...")
        api_key = self.get_config_value("api_key")
        if not api_key:
            self.logger.error("API key not found in configuration.")
            return

        # Example usage of logger and config value
        self.logger.info(f"API Key: {api_key[:4]}... (truncated for security)")
        self.logger.info("Yahoo Finance engine completed.")

    def run(self) -> None:
        """
        Executes the main logic of the Yahoo Finance engine.

        Args:
        ----
            None

        Returns:
        -------
            None

        Raises:
        ------
            None

        """
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()
