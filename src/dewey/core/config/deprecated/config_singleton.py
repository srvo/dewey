"""Configuration management for Dewey project."""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from dewey.core.exceptions import ConfigurationError


class Config:
    """Centralized configuration manager for Dewey project."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {}
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Load configuration from dewey.yaml file."""
        config_path = Path("config/dewey.yaml")
        if not config_path.exists():
            config_path = Path("src/dewey/config/dewey.yaml")
            if not config_path.exists():
                raise ConfigurationError(
                    "Could not find dewey.yaml in expected locations"
                )

        try:
            with open(config_path) as f:
                self._config = yaml.safe_load(f)
        except Exception as e:
            raise ConfigurationError(f"Failed to load config: {str(e)}")

    def get(self, section: str, default: Any | None = None) -> dict[str, Any]:
        """Get a configuration section."""
        return self._config.get(section, default)

    def get_value(self, key: str, default: Any | None = None) -> Any:
        """Get a specific configuration value using dot notation."""
        keys = key.split(".")
        value = self._config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
