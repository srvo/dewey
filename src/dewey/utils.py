"""Utility functions for Dewey project."""

from typing import Any, Dict
import yaml
from pathlib import Path

def load_config(config_path: str = "config/dewey.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file.
    
    Args:
        config_path (str): Path to config file. Defaults to "config/dewey.yaml".
        
    Returns:
        Dict[str, Any]: Loaded configuration
        
    Raises:
        FileNotFoundError: If config file not found
        yaml.YAMLError: For invalid YAML syntax
    """
    config_file = Path(__file__).parent.parent / config_path
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
        
    with open(config_file, "r") as f:
        return yaml.safe_load(f)

def get_deepinfra_client() -> Any:
    """Initialize and return DeepInfra client using config."""
    # Implementation would depend on your DeepInfraClient class structure
    pass

def validate_test_output(content: str) -> bool:
    """Validate generated test content meets project standards."""
    # Basic validation logic
    required_phrases = ["import pytest", "def test_"]
    return all(phrase in content for phrase in required_phrases)
