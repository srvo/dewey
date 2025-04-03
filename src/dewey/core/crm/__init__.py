"""Customer Relationship Management (CRM) Module for Dewey

This module provides CRM functionality for managing contacts, communication,
data import/export, and various CRM-related utilities.
"""

from typing import Any, Optional

from dewey.core.base_script import BaseScript
from dewey.core.crm.communication import EmailClient
from dewey.core.crm.contacts import ContactConsolidation, CsvContactIntegration
from dewey.core.crm.data import DataImporter
from dewey.core.db.connection import DatabaseConnection, get_connection

# TODO: Update all CRM modules to use LiteLLMClient directly instead of get_llm_client
# Temporary import fix during migration from llm_utils to litellm_client
from dewey.llm.litellm_client import LiteLLMClient


# Shim function to maintain compatibility during migration
def get_llm_client(*args, **kwargs):
    """Temporary compatibility function during migration to LiteLLMClient."""
    return LiteLLMClient(*args, **kwargs)


class CrmModule(BaseScript):
    """A module for managing CRM-related tasks within Dewey.

    This module inherits from BaseScript and provides a standardized
    structure for CRM scripts, including configuration loading, logging,
    and a `run` method to execute the script's primary logic.
    """

    def __init__(
        self,
        name: str = "CRM Module",
        description: str = "Manages CRM tasks.",
        config_section: str | None = "crm",
        requires_db: bool = True,
        enable_llm: bool = False,
    ) -> None:
        """Initializes the CRM module.

        Args:
            name: The name of the CRM module.
            description: A description of the CRM module.
            config_section: The configuration section to use for this module.
            requires_db: Whether this module requires a database connection.
            enable_llm: Whether this module requires an LLM client.

        """
        super().__init__(
            name=name,
            description=description,
            config_section=config_section,
            requires_db=requires_db,
            enable_llm=enable_llm,
        )

    def run(self) -> None:
        """Executes the primary logic of the CRM module.

        This method demonstrates accessing configuration values,
        logging information, and interacting with a database (if enabled).

        Raises:
            Exception: If there is an error during the CRM module execution.

        """
        self.logger.info("Starting CRM module...")

        try:
            # Example of accessing a configuration value
            api_key = self.get_config_value("api_key", default="default_api_key")
            self.logger.debug(f"CRM API Key: {api_key}")

            # Example of database interaction (if enabled)
            if self.db_conn:
                self.logger.info("Performing database operations...")
                # Example: Execute a query (replace with your actual query)
                try:
                    with self.db_conn.cursor() as cur:
                        cur.execute("SELECT 1;")
                        result = cur.fetchone()
                        self.logger.debug(f"Database query result: {result}")
                except Exception as db_error:
                    self.logger.error(f"Database error: {db_error}")
                    raise

            # Add your CRM logic here
            self.logger.info("CRM module completed.")

        except Exception as e:
            self.logger.error(f"Error in CRM module: {e}")
            raise

    def execute(self) -> None:
        """Executes the primary logic of the CRM module.

        This method demonstrates accessing configuration values,
        logging information, and interacting with a database (if enabled).

        Raises:
            Exception: If there is an error during the CRM module execution.

        """
        self.logger.info("Starting CRM module...")

        try:
            # Example of accessing a configuration value
            api_key = self.get_config_value("api_key", default="default_api_key")
            self.logger.debug(f"CRM API Key: {api_key}")

            # Example of database interaction (if enabled)
            if self.db_conn:
                self.logger.info("Performing database operations...")
                # Example: Execute a query (replace with your actual query)
                try:
                    with self.db_conn.cursor() as cur:
                        cur.execute("SELECT 1;")
                        result = cur.fetchone()
                        self.logger.debug(f"Database query result: {result}")
                except Exception as db_error:
                    self.logger.error(f"Database error: {db_error}")
                    raise

            # Add your CRM logic here
            self.logger.info("CRM module completed.")

        except Exception as e:
            self.logger.error(f"Error in CRM module: {e}")
            raise


__all__ = [
    "CrmModule",
    "ContactConsolidation",
    "CsvContactIntegration",
    "EmailClient",
    "DataImporter",
]
