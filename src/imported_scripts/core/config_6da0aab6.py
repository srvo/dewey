"""Configuration management for ECIC."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Configuration for ECIC application."""

    database_url: str | None = None
    tick_interval: int = 60
    log_level: str = "INFO"
    warnings: list[str] = None

    def __post_init__(self):
        """Initialize warnings list."""
        if self.warnings is None:
            self.warnings = []


def load_config(config_path: str | None = None) -> Config:
    """Load configuration from file or environment."""
    if config_path is None:
        config_path = os.path.expanduser("~/.ecic/config.yaml")

    config_dict = {}

    try:
        if os.path.exists(config_path):
            with open(config_path) as f:
                config_dict = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Error loading config file: {e!s}")

    # Create config object
    config = Config(
        database_url=config_dict.get("database_url"),
        tick_interval=config_dict.get("tick_interval", 60),
        log_level=config_dict.get("log_level", "INFO"),
    )

    # Add warnings for missing optional configs
    if not config.database_url:
        config.warnings.append(
            "No database_url specified. Database features will not be available.",
        )

    return config


def create_default_config(config_path: str | None = None) -> None:
    """Create a default configuration file."""
    if config_path is None:
        config_path = os.path.expanduser("~/.ecic/config.yaml")

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    # Only create if it doesn't exist
    if not os.path.exists(config_path):
        default_config = {
            "database_url": "postgresql+asyncpg://localhost/ecic",
            "tick_interval": 60,
            "log_level": "INFO",
        }

        with open(config_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)

        logger.info(f"Created default config at {config_path}")
