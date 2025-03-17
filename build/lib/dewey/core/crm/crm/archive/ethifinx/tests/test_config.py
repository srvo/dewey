import pytest

from ethifinx.core.config import Config


def test_config_default_values():
    """Test configuration with default values."""
    config = Config(
        API_BASE_URL="https://api.test.com/v1",
        API_KEY="test_key",
    )
    assert config.API_BASE_URL == "https://api.test.com/v1"
    assert config.API_KEY == "test_key"
    assert "sqlite://" in config.DATABASE_URI
    assert config.S3_BUCKET_NAME == "test_bucket"
    assert config.AWS_ACCESS_KEY_ID == "test_access_key"
    assert config.AWS_SECRET_ACCESS_KEY == "test_secret_key"
    assert config.AWS_REGION == "us-east-1"


def test_config_environment_variables(monkeypatch):
    """Test configuration with environment variables."""
    # Clear any existing environment variables
    monkeypatch.delenv("API_BASE_URL", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URI", raising=False)
    monkeypatch.delenv("S3_BUCKET_NAME", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)

    # Set new environment variables
    monkeypatch.setenv("API_BASE_URL", "https://test.api.com")
    monkeypatch.setenv("API_KEY", "test_api_key")
    monkeypatch.setenv("DATABASE_URI", "sqlite:///test.db")
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_access_key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret_key")
    monkeypatch.setenv("AWS_REGION", "us-west-2")

    config = Config()
    assert config.API_BASE_URL == "https://test.api.com"
    assert config.API_KEY == "test_api_key"
    assert config.DATABASE_URI == "sqlite:///test.db"
    assert config.S3_BUCKET_NAME == "test-bucket"
    assert config.AWS_ACCESS_KEY_ID == "test_access_key"
    assert config.AWS_SECRET_ACCESS_KEY == "test_secret_key"
    assert config.AWS_REGION == "us-west-2"


def test_config_path_creation():
    """Test that required directories are created."""
    config = Config()
    assert config.LOG_DIR.exists()
    assert config.DATA_DIR.exists()


def test_config_logging_setup():
    """Test logging configuration."""
    config = Config()
    assert config.LOG_FILE.parent == config.LOG_DIR
    assert config.LOG_LEVEL in [10, 20, 30, 40, 50]  # Valid logging levels
    assert isinstance(config.LOG_FORMAT, str)
