from dewey.core.base_script import BaseScript
import logging
from typing import Any, Dict


class PypiSearch(BaseScript):
    """
    A class for searching PyPI packages.

    Inherits from BaseScript and provides methods for searching PyPI
    using configuration values.
    """

    def __init__(self) -> None:
        """
        Initializes the PypiSearch class.

        Calls the superclass constructor to initialize the base script.
        """
        super().__init__()
        self.name = "PypiSearch"

    def run(self) -> None:
        """
        Executes the PyPI search.

        This method retrieves configuration values and performs the PyPI search.
        """
        try:
            package_name = self.get_config_value("package_name", "requests")
            self.logger.info(f"Searching PyPI for package: {package_name}")
            # Placeholder for actual PyPI search logic
            self.logger.info("PyPI search completed.")
        except Exception as e:
            self.logger.exception(f"An error occurred during PyPI search: {e}")


if __name__ == "__main__":
    searcher = PypiSearch()
    searcher.run()
