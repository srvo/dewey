#!/usr/bin/env python3
"""Test configuration and fixtures for the Dewey project."""

import os
import sys
import logging
import yaml
import importlib.util
from pathlib import Path
import pytest
from unittest.mock import MagicMock
from typing import Generator, AsyncGenerator

# Add project root to Python path
project_root = Path("/Users/srvo/dewey")
src_path = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

# Mock dependencies
sys.modules['dewey.utils'] = MagicMock()
sys.modules['dewey.llm.llm_utils'] = MagicMock()
sys.modules['dewey.core.engines'] = MagicMock()

# Import base script directly
base_script_path = project_root / "src/dewey/core/base_script.py"
if not base_script_path.exists():
    raise FileNotFoundError(f"Could not find base_script.py at {base_script_path}")

spec = importlib.util.spec_from_file_location("base_script", base_script_path)
base_script = importlib.util.module_from_spec(spec)
sys.modules["base_script"] = base_script
spec.loader.exec_module(base_script)
BaseScript = base_script.BaseScript

# Import config directly
config_path = project_root / "config/dewey.yaml"
if not config_path.exists():
    config_path = project_root / "src/dewey/config/dewey.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Could not find dewey.yaml in expected locations")

with open(config_path, "r") as f:
    config_data = yaml.safe_load(f)

# Configure logging
log_config = config_data.get("logging", {})
log_dir = log_config.get("log_dir", "logs")
os.makedirs(log_dir, exist_ok=True)

@pytest.fixture(autouse=True)
def clear_logs():
    """Clear log files between tests."""
    for log_file in Path(log_dir).glob("*.log"):
        log_file.unlink(missing_ok=True)
    yield

@pytest.fixture(autouse=True)
def clean_logging(caplog):
    """Ensure logs are cleared between tests."""
    caplog.clear()

@pytest.fixture
def base_script():
    """Fixture providing BaseScript instance for test setup"""
    class TestScript(BaseScript):
        def __init__(self):
            super().__init__(config_section="test")
    return TestScript()

@pytest.fixture
def test_data_dir(tmp_path) -> Path:
    """Create and return a temporary directory for test data."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir

@pytest.fixture
def test_config_dir(tmp_path) -> Path:
    """Create and return a temporary directory for test configuration."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir

@pytest.fixture
def mock_env(test_data_dir, test_config_dir, monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("DEWEY_DATA_DIR", str(test_data_dir))
    monkeypatch.setenv("DEWEY_CONFIG_DIR", str(test_config_dir))
    monkeypatch.setenv("MOTHERDUCK_TOKEN", "test_token")

@pytest.fixture
def sample_csv_file(test_data_dir) -> Path:
    """Create a sample CSV file for testing."""
    csv_file = test_data_dir / "test.csv"
    csv_file.write_text(
        "id,name,value\n"
        "1,test1,100\n"
        "2,test2,200\n"
    )
    return csv_file

@pytest.fixture
def sample_config_file(test_config_dir) -> Path:
    """Create a sample configuration file for testing."""
    config_file = test_config_dir / "dewey.yaml"
    config_file.write_text(
        "database:\n"
        "  motherduck_token: test_token\n"
        "  default_db: test_db\n"
    )
    return config_file

@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path):
    """Set up test environment variables."""
    os.environ["DEEPINFRA_API_KEY"] = "test_key"
    os.environ["DEWEY_DIR"] = str(tmp_path)
    os.environ["DEWEY_CONFIG_PATH"] = str(tmp_path / "dewey.yaml")
    os.environ["MOTHERDUCK_API_KEY"] = "test_motherduck_key"
    
    # Create minimal config file
    (tmp_path / "dewey.yaml").write_text("""
logging:
  level: DEBUG
  format: "[%(levelname)s] %(message)s"
""")
    
    yield
    del os.environ["DEEPINFRA_API_KEY"]
    del os.environ["DEWEY_DIR"]
    del os.environ["DEWEY_CONFIG_PATH"]
    del os.environ["MOTHERDUCK_API_KEY"]
