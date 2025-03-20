from dewey.core.base_script import BaseScript
from typing import Any, Dict

class MyLLMScript(BaseScript):
    """A sample script demonstrating Dewey conventions.

    Attributes:
        name (str): Name of the script (used for logging).
        config (Dict[str, Any]): The configuration dictionary.
        dry_run (bool): If True, the script will not execute any
            actions that modify state. Defaults to False.
    """

    def __init__(self, config: Dict[str, Any], dry_run: bool = False) -> None:
        """Initializes the MyLLMScript.

        Args:
            config (Dict[str, Any]): The configuration dictionary.
            dry_run (bool, optional): If True, the script will not execute any
                actions that modify state. Defaults to False.
        """
        super().__init__(config_section='my_llm_script', config=config, dry_run=dry_run)

    def run(self) -> None:
        """Executes the core logic of the script.

        This method demonstrates accessing configuration values,
        logging messages, and performing actions.

        Raises:
            ValueError: If a required configuration value is missing.
        """
        try:
            example_config_value: str = self.get_config_value("example_config")
            self.logger.info(f"Retrieved example_config: {example_config_value}")

            if not self.dry_run:
                self.logger.info("Performing some action...")
                # Simulate an action
            else:
                self.logger.info("Dry run mode: Skipping action.")

        except KeyError as e:
            self.logger.error(f"Missing configuration value: {e}")
            raise ValueError(f"Required configuration value missing: {e}")

if __name__ == "__main__":
    # Example usage (replace with your actual configuration)
    config: Dict[str, Any] = {"example_config": "example_value"}
    script: MyLLMScript = MyLLMScript(config=config)
    script.run()
