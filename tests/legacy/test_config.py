
# Refactored from: test_config
# Date: 2025-03-16T16:19:10.116043
# Refactor Version: 1.0
"""Test configuration module."""

import os
from unittest.mock import patch

import pytest
from ecic.config import Config, ConfigError


def test_load_config() -> None:
    """Test loading configuration from environment variables."""
    test_env = {
        "DATABASE_URL": "postgresql://user:pass@localhost/test",
        "API_KEY": "test_key",
        "TICK_INTERVAL": "60",
        "LOG_LEVEL": "DEBUG",
    }

    with patch.dict(os.environ, test_env, clear=True):
        config = Config.load()

        assert config.database_url == "postgresql://user:pass@localhost/test"
        assert config.api_key == "test_key"
        assert config.tick_interval == 60
        assert config.log_level == "DEBUG"


def test_load_config_missing_required() -> None:
    """Test loading config with missing required variables."""
    test_env = {"API_KEY": "test_key"}  # Missing DATABASE_URL

    with patch.dict(os.environ, test_env, clear=True):
        with pytest.raises(ConfigError) as exc_info:
            Config.load()
        assert "DATABASE_URL" in str(exc_info.value)


def test_load_config_invalid_interval() -> None:
    """Test loading config with invalid tick interval."""
    test_env = {
        "DATABASE_URL": "postgresql://user:pass@localhost/test",
        "API_KEY": "test_key",
        "TICK_INTERVAL": "invalid",
    }

    with patch.dict(os.environ, test_env, clear=True):
        with pytest.raises(ConfigError) as exc_info:
            Config.load()
        assert "TICK_INTERVAL" in str(exc_info.value)


def test_load_config_defaults() -> None:
    """Test loading config with default values."""
    test_env = {
        "DATABASE_URL": "postgresql://user:pass@localhost/test",
        "API_KEY": "test_key",
    }

    with patch.dict(os.environ, test_env, clear=True):
        config = Config.load()

        assert config.tick_interval == 300  # Default 5 minutes
        assert config.log_level == "INFO"  # Default log level


def test_config_validation() -> None:
    """Test config validation."""
    test_env = {"DATABASE_URL": "invalid-url", "API_KEY": "test_key"}

    with patch.dict(os.environ, test_env, clear=True):
        with pytest.raises(ConfigError) as exc_info:
            Config.load()
        assert "DATABASE_URL" in str(exc_info.value)
