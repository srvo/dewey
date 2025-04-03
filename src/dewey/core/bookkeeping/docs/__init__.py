"""
Module for managing documentation tasks within Dewey.

This module provides a standardized structure for documentation-related scripts,
including configuration loading, logging, and a `run` method to execute the
script's primary logic.
"""

from typing import Any, Protocol

from dewey.core.base_script import BaseScript


class DocumentationTask(Protocol):
    """An interface for defining documentation tasks."""

    def execute(self) -> None:
        """Executes the documentation task."""
        raise NotImplementedError


class DocsModule(BaseScript):
    """
    A module for managing documentation tasks within Dewey.
    This module inherits from BaseScript and provides a
    standardized structure for documentation-related scripts,
    including configuration loading, logging, and a `run` method
    to execute the script's primary logic.
    """

    def __init__(
        self,
        name: str,
        description: str = "Documentation Module",
        documentation_task: DocumentationTask | None = None,
    ):
        """
        Initializes the DocsModule.

        Args:
        ----
            name (str): The name of the module.
            description (str, optional): A brief description of the module.
                Defaults to "Documentation Module".
            documentation_task (DocumentationTask, optional): The documentation task to execute.
                Defaults to None.

        """
        super().__init__(name=name, description=description, config_section="docs")
        self._documentation_task = documentation_task

    def execute(self) -> None:
        """
        Executes the primary logic of the documentation module.

        This method should be overridden in subclasses to implement
        specific documentation tasks.

        Args:
        ----
            None

        Returns:
        -------
            None

        Raises:
        ------
            Exception: If something goes wrong during the documentation task.

        """
        self.logger.info("Running the Docs module...")
        try:
            self._execute_documentation_task()
            self.logger.info("Documentation tasks completed.")

        except Exception as e:
            self.logger.error(
                f"An error occurred during documentation: {e}", exc_info=True,
            )
            raise

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()

    def _execute_documentation_task(self) -> None:
        """Executes the documentation task."""
        if self._documentation_task:
            self._documentation_task.execute()
        else:
            # Example of accessing a configuration value
            example_config_value = self.get_config_value(
                "docs_setting", "default_value",
            )
            self.logger.info(f"Example config value: {example_config_value}")

            # Add your documentation logic here

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value associated with the given key.

        Args:
        ----
            key (str): The key of the configuration value to retrieve.
            default (Any, optional): The default value to return if the key
                is not found in the configuration. Defaults to None.

        Returns:
        -------
            Any: The configuration value associated with the key, or the
                default value if the key is not found.

        """
        return super().get_config_value(key, default)
