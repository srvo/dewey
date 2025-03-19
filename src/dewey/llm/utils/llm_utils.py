from dewey.core.base_script import BaseScript
from typing import Any, Dict


class LLMUtils(BaseScript):
    """
    A utility class for interacting with Large Language Models (LLMs).
    """

    def __init__(self, config: Dict[str, Any], dry_run: bool = False):
        """
        Initializes the LLMUtils class.

        Args:
            config (Dict[str, Any]): A dictionary containing configuration parameters.
            dry_run (bool, optional): If True, the script will not perform any actions. Defaults to False.
        """
        super().__init__(config=config, dry_run=dry_run)

    def run(self) -> None:
        """
        Executes the main logic of the LLM utility.

        This method retrieves configuration values, initializes necessary components,
        and performs the core operations of the LLM utility.

        Returns:
            None

        Raises:
            Exception: If there is an error during execution.
        """
        try:
            example_config_value = self.get_config_value("example_config")
            self.logger.info(f"Retrieved example_config: {example_config_value}")

            # Add your LLM utility logic here, using self.logger for logging
            self.logger.info("Executing LLM utility logic...")

        except Exception as e:
            self.logger.exception(f"An error occurred during execution: {e}")


if __name__ == "__main__":
    # Example usage (replace with your actual configuration)
    config = {"example_config": "example_value"}
    llm_utils = LLMUtils(config=config)
    llm_utils.run()
