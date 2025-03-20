from typing import Any

from dewey.core.base_script import BaseScript


class LogManager(BaseScript):
    """Manages logging configuration, rotation, and analysis.

    Inherits from BaseScript to provide standardized access to configuration,
    logging, and other utilities.
    """

    def __init__(self, config_section: str = "log_manager") -> None:
        """Initializes the LogManager.

        Args:
            config_section: The configuration section to use for this script.
        """
        super().__init__(config_section=config_section)

    def run(self) -> None:
        """Executes the main logic of the LogManager.

        This method is intended to be overridden by subclasses to implement
        specific logging management tasks.
        """
        self.logger.info("LogManager is running.")

    def get_log_level(self) -> str:
        """Retrieves the log level from the configuration.

        Returns:
            The log level as a string (e.g., "INFO", "DEBUG").
        """
        return self.get_config_value("log_level", default="INFO")

    def get_log_file_path(self) -> str:
        """Retrieves the log file path from the configuration.

        Returns:
            The log file path as a string.
        """
        return self.get_config_value("log_file_path", default="application.log")

    def some_other_function(self, arg: Any) -> None:
        """Example function demonstrating config and logging.

        Args:
            arg: An example argument.
        """
        value = self.get_config_value("some_config_key", default="default_value")
        self.logger.info(f"Some value: {value}, Arg: {arg}")


if __name__ == "__main__":
    log_manager = LogManager()
    log_manager.execute()
