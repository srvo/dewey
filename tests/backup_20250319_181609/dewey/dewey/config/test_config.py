import pytest
import os
from pathlib import Path
from src.dewey.config import load_config
from typing import Dict, Any

@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary directory with a valid config structure for testing.

    Yields:
        Path: The temporary directory path.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "dewey.yaml"
    config_path.write_text("core: {}")
    original_dir = Path.cwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_dir)

def test_load_config_valid(temp_config_dir):
    """Test that load_config successfully loads a valid config file."""
    config = load_config()
    assert isinstance(config, dict)
    assert "core" in config

def test_load_config_missing(temp_config_dir):
    """Test that load_config raises RuntimeError when config is missing."""
    config_dir = temp_config_dir / "config"
    config_path = config_dir / "dewey.yaml"
    config_path.unlink()
    with pytest.raises(RuntimeError) as exc_info:
        load_config()
    assert "config/dewey.yaml not found" in str(exc_info.value)
