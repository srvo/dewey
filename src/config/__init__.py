"""Central configuration loader with environment variable expansion."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def load_config() -> dict[str, Any]:
    """Load and parse the central configuration file."""
    load_dotenv()  # Load environment variables
    
    config_path = Path(__file__).parent.parent.parent / "config" / "dewey.yaml"
    
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
    elif isinstance(config, list):
        return [_expand_env_vars(v) for v in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        var_name = config[2:-1]
        return os.getenv(var_name, "")
    return config
