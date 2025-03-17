"""Configuration management with type validation and environment variables.

This module provides a centralized configuration system using Pydantic's BaseSettings
for type-safe environment variable parsing and validation. It supports both production
and testing environments with proper separation of concerns.

Key Features:
- Type-safe configuration with Pydantic models
- Environment variable support with fallback defaults
- Path validation and conversion
- Test-specific configuration override
- Database connection string validation
- Logging configuration
- Gmail API credential management
"""

from pathlib import Path
from typing import Dict, Optional, Union

from pydantic import ConfigDict, Field, PostgresDsn, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable parsing."""

    # Core configuration
    project_root: Path = Field(default=Path(__file__).parent.parent)
    scripts_dir: Path = Field(default=Path(__file__).parent)
    data_dir: Path = Field(default=Path(__file__).parent.parent / "data")
    log_dir: Path = Field(default=Path(__file__).parent.parent / "logs")

    # Database configuration
    db_host: str = Field(default="localhost")
    db_port: str = Field(default="5432")
    db_name: str = Field(default="email")
    db_user: str = Field(default="email")
    DB_URL: str = Field(
        default="postgresql://localhost/email",
        description="PostgreSQL connection URL in DSN format",
    )
    DB_POOL_SIZE: int = Field(default=10)
    DB_MAX_OVERFLOW: int = Field(default=20)

    # Logging configuration
    LOG_FILE: Path = Field(default=Path("project.log"))
    LOG_LEVEL: str = Field(default="INFO")

    # Gmail API configuration
    CREDENTIALS_FILE: Path = Field(default=Path("credentials.json"))
    TOKEN_FILE: Path = Field(default=Path("token.pickle"))

    # Email processing settings
    checkpoint_file: Path = Field(default=Path("checkpoint.json"))
    fetch_interval: int = Field(default=300)
    default_max_emails: int = Field(default=10)
    ENRICH_BATCH_SIZE: int = Field(default=100)
    ENRICH_INTERVAL: int = Field(default=3600)

    # API keys
    deepinfra_api_key: str = Field(default="")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Allow extra fields but ignore them
    )

    @validator("LOG_FILE", "CREDENTIALS_FILE", "TOKEN_FILE", pre=True)
    def convert_to_path(cls, value: Union[str, Path]) -> Path:
        """Convert string paths to Path objects for consistent path handling.

        Args:
        ----
            value: Input value which can be either a string or Path object

        Returns:
        -------
            Path: Converted Path object

        Note:
        ----
            This validator runs before the main validation step (pre=True)
            to ensure proper type conversion.

        """
        if isinstance(value, str):
            return Path(value)
        return value

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


class TestSettings(Settings):
    """Test-specific configuration with override capabilities.

    This class extends the base Settings to provide test-specific configuration
    management, allowing temporary overrides of configuration values during testing.
    """

    _test_config: Optional[Dict] = None  # Stores test-specific configuration overrides
    _instance: Optional["TestSettings"] = None  # Singleton instance reference

    @classmethod
    def configure_for_test(cls, test_config: Dict) -> "TestSettings":
        """Configure settings for testing with provided configuration overrides.

        Args:
        ----
            test_config: Dictionary containing configuration overrides for testing

        Returns:
        -------
            TestSettings: Configured test settings instance

        Example:
        -------
            >>> test_config = {"DB_URL": "sqlite:///:memory:", "LOG_LEVEL": "DEBUG"}
            >>> TestSettings.configure_for_test(test_config)

        """
        cls._test_config = test_config
        cls._instance = None  # Reset instance to force reinitialization
        return cls()

    @classmethod
    def reset(cls) -> "TestSettings":
        """Reset configuration to use environment variables instead of test overrides.

        Returns:
        -------
            TestSettings: Reset settings instance

        Note:
        ----
            This should be called after tests complete to restore normal configuration.

        """
        cls._test_config = None
        cls._instance = None  # Reset instance to force reinitialization
        return cls()


class Config(Settings):
    """Main configuration class that extends Settings with additional methods."""

    @classmethod
    def configure_for_test(cls, test_config: Dict) -> None:
        """Configure settings for testing with provided configuration overrides."""
        for key, value in test_config.items():
            setattr(cls, key, value)

    @classmethod
    def reset(cls) -> None:
        """Reset configuration to default values."""
        cls.__init__ = Settings.__init__


# Global settings instance - initialized with default or environment values
config = Config()
