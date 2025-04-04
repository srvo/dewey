from dewey.core.base_script import BaseScript


class PypiSearch(BaseScript):
    """
    A class for searching PyPI packages.

    Inherits from BaseScript and provides methods for searching PyPI
    using configuration values.
    """

    def __init__(self, config_section: str | None = None) -> None:
        """
        Initializes the PypiSearch class.

        Calls the superclass constructor to initialize the base script.

        Args:
        ----
            config_section: The section of the config file to use for this script.

        """
        super().__init__(
            config_section=config_section, requires_db=False, enable_llm=False,
        )
        self.name = "PypiSearch"

    def run(self) -> None:
        """
        Executes the PyPI search.

        This method retrieves configuration values and performs the PyPI search.

        Raises
        ------
            Exception: If an error occurs during the PyPI search.

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
