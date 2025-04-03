"""Module for port modules within Dewey."""
"""
Dewey Research Port Module.

This module provides functionality for managing port modules within Dewey.
"""
from typing import Any

from dewey.core.base_script import BaseScript


class PortModule(BaseScript):
    """
    Base class for port modules within Dewey.

    This class provides a standardized structure for port scripts,
    including configuration loading, logging, and a `run` method to
    execute the script's primary logic.
    """

    def __init__(
        self,
        name: str,
        description: str = "Port Module",
        config_section: str | None = None,
        requires_db: bool = False,
        enable_llm: bool = False,
    ) -> None:
        """
        Initializes the PortModule.

        Args:
        ----
            name: The name of the port module.
            description: A description of the port module.
            config_section: The configuration section to use.
            requires_db: Whether the module requires a database connection.
            enable_llm: Whether the module requires an LLM client.

        """
        super().__init__(
            name=name,
            description=description,
            config_section=config_section,
            requires_db=requires_db,
            enable_llm=enable_llm,
        )

    def run(self) -> None:
        """Executes the primary logic of the port module."""
        self.logger.info("Running the port module...")
        # Add your implementation here
        config_value = self.get_config_value("some_config_key", "default_value")
        self.logger.info(f"Config value: {config_value}")

        # Example database usage
        if self.db_conn:
            try:
                # Execute a query (replace with your actual query)
                with self.db_conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    self.logger.info(f"Database query result: {result}")
            except Exception as e:
                self.logger.error(f"Error executing database query: {e}")

        # Example LLM usage
        if self.llm_client:
            try:
                response = self.llm_client.generate(prompt="Write a short poem.")
                self.logger.info(f"LLM response: {response}")
            except Exception as e:
                self.logger.error(f"Error calling LLM: {e}")

    def execute(self) -> None:
        """Executes the primary logic of the port module."""
        self.logger.info("Running the port module...")
        # Add your implementation here
        config_value = self.get_config_value("some_config_key", "default_value")
        self.logger.info(f"Config value: {config_value}")

        # Example database usage
        if self.db_conn:
            try:
                # Execute a query (replace with your actual query)
                with self.db_conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    self.logger.info(f"Database query result: {result}")
            except Exception as e:
                self.logger.error(f"Error executing database query: {e}")

        # Example LLM usage
        if self.llm_client:
            try:
                response = self.llm_client.generate(prompt="Write a short poem.")
                self.logger.info(f"LLM response: {response}")
            except Exception as e:
                self.logger.error(f"Error calling LLM: {e}")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value by key.

        Args:
        ----
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
        -------
            The configuration value, or the default value if the key is not found.

        """
        return super().get_config_value(key, default)
