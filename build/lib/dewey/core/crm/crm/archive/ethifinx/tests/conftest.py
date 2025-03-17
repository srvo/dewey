"""Test configuration and fixtures."""

import os
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ethifinx.core.config import Config
from ethifinx.db.exceptions import (  # Import exceptions
    DatabaseRetrievalError,
    DatabaseSaveError,
)
from ethifinx.db.models import Base  # Ensure models.py exists


def pytest_sessionstart(session):
    """Set up test environment before session."""
    # Load test environment variables
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
def test_config():
    """Provide test configuration."""
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
def test_engine(test_config):
    """Create test database engine."""
    engine = create_engine(test_config.DATABASE_URI)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(test_engine):
    """Set up test database with required tables using SQLAlchemy models."""
    # Create all tables defined in the models
    Base.metadata.create_all(bind=test_engine)
    yield
    # Drop all tables after tests are done
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(test_engine):
    """Create a new database session for a test."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, test_config):
    """Set up test environment variables."""
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
