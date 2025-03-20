from dewey.core.base_script import BaseScript


class DataIngestion(BaseScript):
    """
    A class for ingesting data, adhering to Dewey conventions.

    Inherits from BaseScript to provide standardized access to configuration,
    logging, and other utilities.
    """

    def __init__(self) -> None:
        """
        Initializes the DataIngestion class.

        Calls the BaseScript constructor with the 'data_ingestion' config section.
        """
        super().__init__(config_section='data_ingestion')

    def run(self) -> None:
        """
        Executes the data ingestion process.

        This method retrieves configuration values, logs messages, and performs
        the core data ingestion logic.
        """
        try:
            # Example of accessing configuration values
            input_path = self.get_config_value('input_path', '/default/input/path')
            output_path = self.get_config_value('output_path', '/default/output/path')

            self.logger.info(f"Starting data ingestion from {input_path} to {output_path}")

            # Add your data ingestion logic here
            self.logger.info("Data ingestion process completed successfully.")

        except Exception as e:
            self.logger.exception(f"An error occurred during data ingestion: {e}")


if __name__ == "__main__":
    ingestion = DataIngestion()
    ingestion.run()
