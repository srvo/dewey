"""Shared test fixtures for unit/config tests."""

import pytest
from pathlib import Path
import tempfile
import yaml
import toml

@pytest.fixture
def test_unit_config_data():
    """Fixture providing test unit/configuration data."""
    return {
        "core": {
            "project_root": "/Users/srvo/dewey",
            "backup_strategy": "3-2-1",
            "default_timezone": "UTC",
            "conventions_document": "/Users/srvo/dewey/CONVENTIONS.md"
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "vector_stores": {
            "code_consolidation": {
                "persist_dir": ".chroma_cache",
                "collection_name": "code_functions",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
            }
        }
    }

@pytest.fixture
def temp_unit_config_dir():
    """Fixture providing a temporary directory for unit/config files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def yaml_unit_config_file(temp_unit_config_dir, test_unit_config_data):
    """Fixture providing a temporary YAML unit/config file."""
    config_file_path = temp_unit_config_dir / "config.yaml"
    with open(config_file_path, "w") as f:
        yaml.dump(test_unit_config_data, f)
    return config_file_path

@pytest.fixture
def toml_unit_config_file(temp_unit_config_dir, test_unit_config_data):
    """Fixture providing a temporary TOML unit/config file."""
    config_file_path = temp_unit_config_dir / "config.toml"
    with open(config_file_path, "w") as f:
        toml.dump(test_unit_config_data, f)
    return config_file_path

@pytest.fixture
def invalid_unit_config_file(temp_unit_config_dir):
    """Fixture providing an invalid unit/config file."""
    config_file_path = temp_unit_config_dir / "invalid.yaml"
    with open(config_file_path, "w") as f:
        f.write("This is not valid YAML or TOML")
    return config_file_path
