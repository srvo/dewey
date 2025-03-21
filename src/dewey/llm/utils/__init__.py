from typing import Any, Dict

from dewey.core.base_script import BaseScript


class LLMUtils(BaseScript):
    """A utility class for interacting with Language Models (LLMs)."""

    def __init__(self, config: Dict[str, Any], dry_run: bool = False) -> None:
        """Initializes the LLMUtils class.

        Args:
            config (Dict[str, Any]): A dictionary containing the configuration parameters.
            dry_run (bool, optional): A boolean indicating whether to run in dry-run mode. Defaults to False.
        """
        super().__init__(config=config, dry_run=dry_run)

    def run(self) -> None:
        """Executes the main logic of the LLM utility.

        This method demonstrates the usage of various features such as accessing configuration values
        and logging messages.

        Returns:
            None

        Raises:
            ValueError: If a required configuration value is missing.
        """
        try:
            example_config_value = self.get_config_value("example_config_key")
            self.logger.info(f"Example config value: {example_config_value}")

            self.logger.info("LLM utility execution completed.")

        except KeyError as e:
            self.logger.error(f"Missing configuration key: {e}")
            raise ValueError(f"Required configuration key missing: {e}")
