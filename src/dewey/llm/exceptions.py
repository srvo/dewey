from dewey.core.base_script import BaseScript
from typing import Any, Dict

class MyLLMScript(BaseScript):
    """
    A sample script demonstrating Dewey conventions.
    """

    def __init__(self, config: Dict[str, Any], dry_run: bool = False):
        """
        Initializes the MyLLMScript.

        Args:
            config (Dict[str, Any]): The configuration dictionary.
            dry_run (bool, optional):  If True, the script will not execute any
                actions that modify state. Defaults to False.
        """
        super().__init__(config=config, dry_run=dry_run)

    def run(self) -> None:
        """
        Executes the core logic of the script.

        This method demonstrates accessing configuration values,
        logging messages, and performing actions.

        Returns:
            None

        Raises:
            ValueError: If a required configuration value is missing.
        """
        try:
            example_config_value = self.get_config_value("example_config")
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
    config = {"example_config": "example_value"}
    script = MyLLMScript(config=config)
    script.run()
