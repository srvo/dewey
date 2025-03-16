from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


def load_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from file.

    Args:
    ----
        config_path: Path to configuration file

    Returns:
    -------
        Configuration dictionary

    Raises:
    ------
        FileNotFoundError: If configuration file does not exist
        json.JSONDecodeError: If configuration file is invalid JSON

    """
    if not config_path.exists():
        msg = f"Configuration file not found: {config_path}"
        raise FileNotFoundError(msg)

    with open(config_path) as f:
        return json.load(f)


def save_config(config: dict[str, Any], config_path: Path) -> None:
    """Save configuration to file.

    Args:
    ----
        config: Configuration dictionary
        config_path: Path to save configuration to

    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def setup_logging(
    log_dir: Path,
    level: int = logging.INFO,
    filename: str | None = None,
) -> logging.Logger:
    """Set up logging configuration.

    Args:
    ----
        log_dir: Directory to store log files
        level: Logging level
        filename: Optional log filename (defaults to service_manager.log)

    Returns:
    -------
        Configured logger

    """
    log_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = "service_manager.log"

    log_path = log_dir / filename

    # Configure logging
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler()],
    )

    return logging.getLogger(__name__)


def validate_config(config: dict[str, Any]) -> None:
    """Validate configuration dictionary.

    Args:
    ----
        config: Configuration dictionary to validate

    Raises:
    ------
        ValueError: If configuration is invalid

    """
    required_fields = ["services"]
    for field in required_fields:
        if field not in config:
            msg = f"Missing required field: {field}"
            raise ValueError(msg)

    if not isinstance(config["services"], dict):
        msg = "'services' must be a dictionary"
        raise ValueError(msg)

    for service_name, service_config in config["services"].items():
        if not isinstance(service_config, dict):
            msg = f"Service '{service_name}' configuration must be a dictionary"
            raise ValueError(
                msg,
            )

        if "image" not in service_config:
            msg = f"Service '{service_name}' missing required field: image"
            raise ValueError(msg)


def template_config(template: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Apply template variables to configuration.

    Args:
    ----
        template: Configuration template
        **kwargs: Template variables

    Returns:
    -------
        Templated configuration dictionary

    """
    config_str = json.dumps(template)

    # Replace template variables
    for key, value in kwargs.items():
        config_str = config_str.replace(f"${{{key}}}", str(value))

    return json.loads(config_str)


def get_env_config(prefix: str = "SERVICE_MANAGER_") -> dict[str, str]:
    """Get configuration from environment variables.

    Args:
    ----
        prefix: Environment variable prefix

    Returns:
    -------
        Dictionary of configuration values

    """
    config = {}

    for key, value in os.environ.items():
        if key.startswith(prefix):
            config_key = key[len(prefix) :].lower()
            config[config_key] = value

    return config


def merge_configs(*configs: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple configuration dictionaries.

    Args:
    ----
        *configs: Configuration dictionaries to merge

    Returns:
    -------
        Merged configuration dictionary

    """
    result = {}

    for config in configs:
        _deep_merge(result, config)

    return result


def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> None:
    """Deep merge source dictionary into target dictionary.

    Args:
    ----
        target: Target dictionary to merge into
        source: Source dictionary to merge from

    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value
