from dewey.core.base_script import BaseScript


class SecEtl(BaseScript):
    """A class for performing SEC ETL operations.

    This class inherits from BaseScript and provides methods for
    extracting, transforming, and loading data from SEC filings.
    """

    def __init__(self) -> None:
        """Initializes the SecEtl class."""
        super().__init__(config_section="sec_etl")

    def run(self) -> None:
        """Executes the SEC ETL process."""
        self.logger.info("Starting SEC ETL process.")
        # Access configuration values using self.get_config_value()
        some_config_value = self.get_config_value("some_config_key", "default_value")
        self.logger.info(f"Some config value: {some_config_value}")

        # Add your ETL logic here
        self.logger.info("SEC ETL process completed.")
