from typing import Any

from dewey.core.base_script import BaseScript


class ResearchWorkflow(BaseScript):
    """Base class for research workflows within Dewey.

    This class provides a standardized structure for research scripts,
    including configuration loading, logging, and a `run` method to
    execute the script's primary logic.
    """

    def __init__(self, name: str, description: str):
        """Initializes the ResearchWorkflow.

        Args:
            name: Name of the workflow.
            description: Description of the workflow.

        """
        super().__init__(name, description)

    def run(self) -> None:
        """Executes the primary logic of the research workflow."""
        self.logger.info(f"Running research workflow: {self.name}")
        # Add your workflow logic here

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value using the base script method.

        Args:
            key: The configuration key to retrieve.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value, or the default if not found.

        """
        return super().get_config_value(key, default)
