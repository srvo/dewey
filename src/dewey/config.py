"""Config module to provide access to centralized configuration."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """Load configuration from dewey.yaml."""
    config_path = Path(os.getcwd()) / "config" / "dewey.yaml"
    if not config_path.exists():
        raise RuntimeError("Please run this script from the project root directory (config/dewey.yaml not found)")
        
    with open(config_path) as f:
        return yaml.safe_load(f) 