from dewey.core.base_script import BaseScript
import logging
from typing import Any

class DataUploader(BaseScript):
    """
    A base class for data upload scripts within the Dewey framework.

    This class provides standardized access to configuration, logging,
    and other utilities provided by the BaseScript class.
    """

    def __init__(self, config_section: str = 'data_uploader') -> None:
        """
        Initializes the DataUploader.

        Args:
            config_section: The configuration section to use for this script.
        """
        super().__init__(config_section=config_section)

    def run(self) -> None:
        """
        Executes the data upload process.

        This method should be overridden by subclasses to implement the
        specific data upload logic.
        """
        self.logger.info("Data upload process started.")
        try:
            # Example of accessing a configuration value
            api_key = self.get_config_value('api_key')
            if api_key:
                self.logger.debug(f"API Key: {api_key}")
            else:
                self.logger.warning("API Key not found in configuration.")

            # Add your data upload logic here
            self.logger.info("Data upload process completed successfully.")

        except Exception as e:
            self.logger.exception(f"An error occurred during data upload: {e}")

if __name__ == '__main__':
    uploader = DataUploader()
    uploader.run()
