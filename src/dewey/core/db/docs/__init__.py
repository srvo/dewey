from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_connection
from dewey.llm.llm_utils import generate_text
from typing import Any


class DocsModule(BaseScript):
    """
    A module for managing database documentation tasks within Dewey.

    This module inherits from BaseScript and provides a standardized
    structure for documentation-related scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the DocsModule."""
        super().__init__(*args, config_section="docs_module", **kwargs)
        self.module_name = "DocsModule"

    def run(self) -> None:
        """
        Executes the primary logic of the database documentation module.

        This includes connecting to the database, retrieving table schemas,
        generating documentation using an LLM, and updating the database
        with the generated documentation.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If any error occurs during the documentation process.
        """
        self.logger.info(f"Running {self.module_name}...")

        try:
            # Example of accessing a configuration value
            example_config_value = self.get_config_value(
                "example_config", "default_value"
            )
            self.logger.info(f"Example config value: {example_config_value}")

            # Connect to the database
            with get_connection() as connection:
                # Example: Execute a query
                result = connection.execute("SELECT 1")
                self.logger.info(f"Database query result: {result}")

            # Example: Use LLM to generate documentation
            prompt = "Write a brief description of the database schema."
            documentation = generate_text(prompt, llm_client=self.llm_client)
            self.logger.info(f"Generated documentation: {documentation}")

            # Add your main script logic here
            self.logger.info(f"{self.module_name} completed.")

        except Exception as e:
            self.logger.error(f"Error in {self.module_name}: {e}", exc_info=True)
            raise

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value associated with the given key.

        Args:
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value, or the default value if the key is not found.
        """
        return super().get_config_value(key, default)


if __name__ == "__main__":
    docs_module = DocsModule()
    docs_module.execute()
