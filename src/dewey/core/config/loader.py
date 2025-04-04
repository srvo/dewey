"""
Configuration loading functionality for Dewey project.
Separated to avoid circular imports between config and db modules.
"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _expand_env_vars(config_data: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively expand environment variables in the configuration.

    Args:
    ----
        config_data: The configuration data.

    Returns:
    -------
        The configuration data with environment variables expanded.

    """
    if not isinstance(config_data, dict):
        return config_data

    result = {}
    for key, value in config_data.items():
        if isinstance(value, dict):
            # Recursively process nested dictionaries
            result[key] = _expand_env_vars(value)
        elif isinstance(value, list):
            # Process lists (handle lists of dictionaries)
            result[key] = [
                _expand_env_vars(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, str):
            # Expand environment variables in strings
            # Format: ${VAR_NAME} or ${VAR_NAME:-default}
            if "${" in value and "}" in value:
                # Check if this is a simple variable with default format: ${VAR:-default}
                if value.startswith("${") and value.endswith("}") and ":-" in value:
                    var_parts = value[2:-1].split(":-", 1)
                    env_name = var_parts[0]
                    default = var_parts[1] if len(var_parts) > 1 else ""
                    result[key] = os.environ.get(env_name, default)
                else:
                    # Extract parts between ${ and }
                    parts = value.split("${")
                    result_value = parts[0]  # Start with text before first ${
                    for part in parts[1:]:
                        if "}" in part:
                            env_part, rest = part.split("}", 1)
                            # Check if there's a default value with :- syntax
                            if ":-" in env_part:
                                env_name, default = env_part.split(":-", 1)
                                env_value = os.environ.get(env_name, default)
                            else:
                                env_value = os.environ.get(env_part, "")
                            result_value += str(env_value) + rest
                        else:
                            # No closing brace, keep as is
                            result_value += "${" + part
                    result[key] = result_value
            else:
                result[key] = value
        else:
            # Keep other values as is
            result[key] = value

    return result


def load_config(force_reload: bool = False) -> dict[str, Any]:
    """
    Load configuration from dewey.yaml.

    Args:
    ----
        force_reload: Whether to force reload the configuration from disk.

    Returns:
    -------
        The configuration loaded from dewey.yaml.

    """
    # Check if we have a cached config and don't need to reload
    if (
        not force_reload
        and ConfigSingleton._instance
        and ConfigSingleton._instance._config
    ):
        return ConfigSingleton._instance._config

    # Define possible configuration file paths
    possible_paths = [
        Path.cwd() / "config" / "dewey.yaml",  # /Users/srvo/dewey/config/dewey.yaml
        Path.cwd() / "dewey.yaml",  # /Users/srvo/dewey/dewey.yaml
        Path.cwd()
        / "src"
        / "config"
        / "dewey.yaml",  # /Users/srvo/dewey/src/config/dewey.yaml
        Path(__file__).parent.parent.parent.parent
        / "config"
        / "dewey.yaml",  # src/dewey/core/config -> dewey/config
    ]

    # Try to find an existing configuration file
    config_path = None
    for path in possible_paths:
        if path.exists():
            config_path = path
            logger.info(f"Found configuration file at: {config_path}")
            break

    # Load configuration
    if config_path and config_path.exists():
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                # Expand environment variables
                config = _expand_env_vars(config)
                return config
        except (yaml.YAMLError, OSError) as e:
            logger.error(f"Error loading configuration file: {e}")
            # Fall back to defaults
    else:
        # Log all possible paths that were checked
        paths_str = "\n - ".join([str(p) for p in possible_paths])
        logger.warning(
            f"No configuration file found in any of these locations:\n - {paths_str}\nUsing defaults",
        )

    # Return default configuration if no file is found or loading failed
    return _get_default_config()


def _get_default_config() -> dict[str, Any]:
    """
    Get the default configuration.

    Returns
    -------
        The default configuration.

    """
    return {
        "core": {
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            },
            "database": {
                "type": "postgres",
                "postgres": {
                    "host": os.environ.get("DB_HOST", "localhost"),
                    "port": int(os.environ.get("DB_PORT", "5432")),
                    "dbname": os.environ.get("DB_NAME", "dewey"),
                    "user": os.environ.get(
                        "DB_USER", os.environ.get("USER", "postgres"),
                    ),
                    "password": os.environ.get("DB_PASSWORD", ""),
                    "sslmode": "prefer",
                    "pool_min": 5,
                    "pool_max": 10,
                },
            },
        },
    }


class ConfigSingleton:
    """
    Singleton for accessing configuration throughout the application.

    This provides a consistent way to access config without reloading
    the file multiple times.
    """

    _instance = None
    _config = None

    def __new__(cls):
        """Create a new instance if one doesn't exist."""
        if cls._instance is None:
            cls._instance = super(ConfigSingleton, cls).__new__(cls)
            cls._instance._config = None
        return cls._instance

    @property
    def config(self) -> dict[str, Any]:
        """Get the configuration."""
        if self._config is None:
            self._config = load_config()
        return self._config

    def reload(self) -> dict[str, Any]:
        """Reload the configuration."""
        self._config = load_config(force_reload=True)
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        if "." in key:
            # Handle nested keys like "core.database.host"
            parts = key.split(".")
            value = self.config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value
        return self.config.get(key, default)


# Create a singleton instance
config_instance = ConfigSingleton()
