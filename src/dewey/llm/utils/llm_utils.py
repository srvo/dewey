from typing import Any, Dict

from dewey.core.base_script import BaseScript


class LLMUtils(BaseScript):
    """A utility class for interacting with Large Language Models (LLMs)."""

    def __init__(
        self, config_section: str = "llm_utils", dry_run: bool = False
    ) -> None:
        """Initializes the LLMUtils class.

        Args:
            config_section: The configuration section to use.
            dry_run: If True, the script will not perform any actions.

        """
        super().__init__(config_section=config_section, dry_run=dry_run)

    def execute(self) -> None:
        """Executes the main logic of the LLM utility.

        This method retrieves configuration values, initializes necessary
        components, and performs the core operations of the LLM utility.

        Returns:
            None

        Raises:
            Exception: If there is an error during execution.

        """
        try:
            example_config_value: Any = self.get_config_value("example_config")
            self.logger.info(f"Retrieved example_config: {example_config_value}")

            # Add your LLM utility logic here, using self.logger for logging
            self.logger.info("Executing LLM utility logic...")

        except Exception as e:
            self.logger.exception(f"An error occurred during execution: {e}")

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead."
        )
        self.execute()


if __name__ == "__main__":
    # Example usage (replace with your actual configuration)
    config: dict[str, Any] = {"example_config": "example_value"}
    llm_utils = LLMUtils()
    llm_utils.run()
