from dewey.core.base_script import BaseScript


class FinancialPipeline(BaseScript):
    """
    A class for managing the financial analysis pipeline.

    Inherits from BaseScript to provide standardized access to configuration,
    logging, and other utilities.
    """

    def __init__(
        self,
        name: str = "FinancialPipeline",
        description: str = "Manages financial analysis",
    ) -> None:
        """
        Initializes the FinancialPipeline.

        Args:
            name: The name of the script.
            description: A description of what the script does.
        """
        super().__init__(name=name, description=description)

    def run(self) -> None:
        """
        Executes the financial analysis pipeline.
        """
        self.logger.info("Starting financial analysis pipeline...")

        # Example of accessing configuration values
        api_key = self.get_config_value("financial_api_key")
        if api_key:
            self.logger.info("API key loaded successfully.")
        else:
            self.logger.warning("API key not found in configuration.")

        # Add your financial analysis logic here
        self.logger.info("Financial analysis completed.")


if __name__ == "__main__":
    pipeline = FinancialPipeline()
    pipeline.run()
