```python
"""Test configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ethifinx.core.config import Config
from ethifinx.db.models import Base  # Ensure models.py exists


def _load_test_env_variables() -> None:
    """Loads test environment variables from .env.test or sets defaults."""
    env_test_path = Path(".env.test")
    if env_test_path.exists():
        load_dotenv(env_test_path)
    else:
        # Set default test environment variables if .env.test doesn't exist
        os.environ.update(
            {
                "DATABASE_URI": "sqlite:///:memory:",
                "AWS_ACCESS_KEY_ID": "test_access_key",
                "AWS_SECRET_ACCESS_KEY": "test_secret_key",
                "AWS_REGION": "us-east-1",
                "S3_BUCKET_NAME": "test_bucket",
                "DEEPSEEK_API_KEY": "test_api_key",
                "API_KEY": "test_api_key",
                "API_BASE_URL": "https://api.test.com/v1",
            }
        )


@pytest.fixture(scope="session")
def test_config() -> Generator[Config, None, None]:
    """Provides test configuration.

    Yields:
        Config: Test configuration object.
    """
    # Create a temporary file for the SQLite database
    temp_db_fd, temp_db_path = tempfile.mkstemp()
    os.close(temp_db_fd)  # Close the file descriptor

    config = Config(
        DATABASE_URI=f"sqlite:///{temp_db_path}",  # Use file-based SQLite
        AWS_ACCESS_KEY_ID="test_access_key",
        AWS_SECRET_ACCESS_KEY="test_secret_key",
        AWS_REGION="us-east-1",
        S3_BUCKET_NAME="test_bucket",
        DEEPSEEK_API_KEY="test_api_key",
        API_KEY="test_api_key",
        API_BASE_URL="https://api.test.com/v1",
    )

    yield config

    # Teardown: Remove the temporary database file after tests
    os.remove(temp_db_path)


@pytest.fixture(scope="session")
def test_engine(test_config: Config) -> Generator[Engine, None, None]:
    """Creates test database engine.

    Args:
        test_config: The test configuration object.

    Yields:
        Engine: SQLAlchemy engine instance.
    """
    engine = create_engine(test_config.DATABASE_URI)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(test_engine: Engine) -> Generator[None, None, None]:
    """Sets up test database with required tables using SQLAlchemy models.

    Args:
        test_engine: The SQLAlchemy engine instance.

    Yields:
        None
    """
    # Create all tables defined in the models
    Base.metadata.create_all(bind=test_engine)
    yield
    # Drop all tables after tests are done
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Creates a new database session for a test.

    Args:
        test_engine: The SQLAlchemy engine instance.

    Yields:
        Session: SQLAlchemy session instance.
    """
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch: pytest.MonkeyPatch, test_config: Config) -> None:
    """Sets up test environment variables.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        test_config: The test configuration object.
    """
    # Override any production environment variables with test values
    test_values = {
        "DATABASE_URI": test_config.DATABASE_URI,
        "AWS_ACCESS_KEY_ID": test_config.AWS_ACCESS_KEY_ID,
        "AWS_SECRET_ACCESS_KEY": test_config.AWS_SECRET_ACCESS_KEY,
        "AWS_REGION": test_config.AWS_REGION,
        "S3_BUCKET_NAME": test_config.S3_BUCKET_NAME,
        "DEEPSEEK_API_KEY": test_config.DEEPSEEK_API_KEY,
        "API_KEY": test_config.API_KEY,
        "API_BASE_URL": test_config.API_BASE_URL,
    }
    for key, value in test_values.items():
        monkeypatch.setenv(key, value)


def pytest_sessionstart(session: pytest.Session) -> None:
    """Set up test environment before session.

    Args:
        session: Pytest session object.
    """
    _load_test_env_variables()
```
