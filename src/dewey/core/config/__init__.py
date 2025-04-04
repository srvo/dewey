import logging
import os
from pathlib import Path
from typing import Any, Protocol

import yaml
from dotenv import load_dotenv

from dewey.core.base_script import BaseScript

logger = logging.getLogger(__name__)


def load_config() -> dict[str, Any]:
    """Load and parse the central configuration file."""
    load_dotenv()  # Load environment variables

    config_path = Path(__file__).parent.parent.parent.parent / "config" / "dewey.yaml"

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return _expand_env_vars(config)
    except FileNotFoundError:
        logger.error("Missing config/dewey.yaml - using defaults")
        return {}
    except Exception as e:
        logger.exception("Failed to load configuration")
        raise RuntimeError("Invalid configuration") from e


def _expand_env_vars(config: Any) -> Any:
    """Recursively expand environment variables in config values."""
    if isinstance(config, dict):
        return {k: _expand_env_vars(v) for k, v in config.items()}
    if isinstance(config, list):
        return [_expand_env_vars(v) for v in config]
    if isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        var_name = config[2:-1]
        return os.getenv(var_name, "")
    return config


class DatabaseInterface(Protocol):
    """An interface for database operations, allowing for easy mocking in tests."""

    def execute(self, query: str) -> Any: ...


class MotherDuckInterface(Protocol):
    """An interface for MotherDuck operations, allowing for easy mocking in tests."""

    def execute(self, query: str) -> Any: ...


class ConfigManager(BaseScript):
    """
    Manages configuration settings for the application.

    This class inherits from BaseScript and provides methods for loading
    and accessing configuration values.
    """

    def __init__(
        self,
        config_section: str = "config_manager",
        db_connection: DatabaseInterface | None = None,
        motherduck_connection: MotherDuckInterface | None = None,
    ) -> None:
        """
        Initializes the ConfigManager.

        Args:
        ----
            config_section: The section in the configuration file to use.
            db_connection: An optional database connection to use.  Defaults to None, which will create a connection.
            motherduck_connection: An optional MotherDuck connection to use. Defaults to None, which will create a connection.

        """
        super().__init__(config_section=config_section, requires_db=True)
        self.logger.info("ConfigManager initialized.")
        self._db_connection = db_connection
        self._motherduck_connection = motherduck_connection

    def execute(self) -> None:
        """
        Executes the configuration manager.

        This method performs setup and initialization tasks, and demonstrates
        accessing a configuration value.
        """
        self.logger.info("ConfigManager executing.")
        example_value = self.get_config_value("utils.example_config", "default_value")
        self.logger.info(f"Example configuration value: {example_value}")

        # Example of using the database connection
        try:
            if self._db_connection is None:
                # Import here to avoid circular imports
                from dewey.core.db.connection import DatabaseConnection

                db_conn = DatabaseConnection(self.config)
            else:
                db_conn = self._db_connection

            with db_conn:
                # Execute a query
                result = db_conn.execute("SELECT value FROM example_table WHERE id = 1")
                self.logger.info(f"Database query result: {result}")

                # Example of using MotherDuck connection
                if self._motherduck_connection is None:
                    # Import here to avoid circular imports
                    from dewey.core.db.connection import get_motherduck_connection

                    md_conn = get_motherduck_connection()
                else:
                    md_conn = self._motherduck_connection

                md_result = md_conn.execute("SELECT 42")
                self.logger.info(f"MotherDuck query result: {md_result}")

        except Exception as e:
            self.logger.error(f"Error during database operation: {e}")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value.

        Args:
        ----
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
        -------
            The configuration value, or the default value if the key is not found.

        """
        value = super().get_config_value(key, default)
        self.logger.debug(f"Retrieved config value for key '{key}': {value}")
        return value


if __name__ == "__main__":
    config_manager = ConfigManager()
    config_manager.execute()
