```python
"""Configuration module."""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Application configuration."""

    model_config = {
        "extra": "allow",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    # API Settings
    API_BASE_URL: str = "https://api.example.com"
    API_KEY: str = "default_key"

    # Database Settings
    DATABASE_URI: str = "sqlite:///:memory:"

    # AWS Settings
    AWS_ACCESS_KEY_ID: str = "test_access_key"
    AWS_SECRET_ACCESS_KEY: str = "test_secret_key"
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "research-backup"

    # DeepSeek Settings
    DEEPSEEK_API_KEY: str = "test_api_key"

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOG_DIR: Path = BASE_DIR / "logs"
    LOG_FILE: Path = LOG_DIR / "app.log"

    # Logging
    LOG_LEVEL: int = logging.INFO
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize config and create required directories."""
        super().__init__(**kwargs)
        self._create_directories()

    def _create_directories(self) -> None:
        """Create the log and data directories if they don't exist."""
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def __getattr__(self, name: str) -> Any:
        """Get attribute with case-insensitive lookup.

        Args:
            name: The name of the attribute.

        Returns:
            The value of the attribute.

        Raises:
            AttributeError: If the attribute is not found.
        """
        try:
            return super().__getattr__(name.upper())
        except AttributeError:
            try:
                return super().__getattr__(name.lower())
            except AttributeError:
                return super().__getattr__(name)


# Create singleton instance
config = Config()


@lru_cache
def get_settings() -> Config:
    """Get application settings.

    Returns:
        Config: Application configuration instance
    """
    return config
```
