from dewey.core.base_script import BaseScript
from typing import Any, Dict


class LLMUtils(BaseScript):
    """
    A utility class for interacting with LLMs, adhering to Dewey conventions.
    """

    def __init__(self, config: Dict[str, Any], dry_run: bool = False):
        """
        Initializes the LLMUtils class.

        Args:
            config (Dict[str, Any]): A dictionary containing the configuration parameters.
            dry_run (bool, optional): If True, the script will not perform any actions. Defaults to False.
        """
        super().__init__(config=config, dry_run=dry_run)

    def run(self) -> None:
        """
        Executes the core logic of the LLM utility.

        This method demonstrates the usage of the Dewey conventions, such as accessing
        configuration values and using the logger.

        Returns:
            None

        Raises:
            ValueError: If a required configuration value is missing.
        """
        try:
            example_config_value = self.get_config_value("example_config_value")
            self.logger.info(f"Retrieved example_config_value: {example_config_value}")

            # Example of using the logger for different log levels
            self.logger.debug("This is a debug message.")
            self.logger.info("This is an info message.")
            self.logger.warning("This is a warning message.")
            self.logger.error("This is an error message.")

            if self.dry_run:
                self.logger.info("Dry run mode is enabled. No actions will be performed.")
            else:
                self.logger.info("Executing LLM utility logic...")
                # Add your core logic here, utilizing the configuration and logger.
                pass

        except KeyError as e:
            self.logger.error(f"Missing required configuration value: {e}")
            raise ValueError(f"Missing required configuration value: {e}") from e
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred: {e}")
            raise
