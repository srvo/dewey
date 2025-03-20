from dewey.core.base_script import BaseScript
import logging
from typing import Any, Dict


class OpenFigi(BaseScript):
    """
    A class for interacting with the OpenFIGI API.

    Inherits from BaseScript and provides methods for querying the OpenFIGI
    API to retrieve security data.
    """

    def __init__(self) -> None:
        """
        Initializes the OpenFigi class.

        Calls the superclass constructor to initialize the base script.
        """
        super().__init__(config_section='openfigi')

    def run(self) -> None:
        """
        Executes the main logic of the OpenFigi script.

        This method should be overridden by subclasses to implement the
        specific functionality of the script.
        """
        self.logger.info("OpenFigi script started.")
        # Example of accessing a config value
        api_key = self.get_config_value("api_key")
        if api_key:
            self.logger.info("API Key loaded from config")
        else:
            self.logger.warning("No API Key found in config")
        self.logger.info("OpenFigi script finished.")


if __name__ == '__main__':
    open_figi = OpenFigi()
    open_figi.run()
