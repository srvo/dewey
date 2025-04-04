"""Test configuration for database tests."""

import contextlib
import os
from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest

from dewey.core.base_script import BaseScript


class TestConfiguration(BaseScript):
    """
    Test configuration for database tests.

    Inherits from BaseScript to utilize standardized configuration and logging.
    """

    def __init__(self) -> None:
        """Initialize the test configuration."""
        super().__init__(config_section="test_config")

    @contextlib.contextmanager
    def mock_env_vars(self) -> Generator[None, None, None]:
        """
        Mock environment variables for testing.

        Yields
        ------
            None: This function is a generator that yields None.

        """
        with patch.dict(
            os.environ,
            {
                "MOTHERDUCK_TOKEN": self.get_config_value(
                    "motherduck_token", "test_token",
                ),
                "DEWEY_HOME": "/tmp/dewey_test",
                "EMAIL_USERNAME": "test@example.com",
                "EMAIL_PASSWORD": "test_password",
                "IMAP_SERVER": "imap.test.com",
                "IMAP_PORT": "993",
            },
        ):
            yield

    @contextlib.contextmanager
    def setup_test_db(self) -> Generator[None, None, None]:
        """
        Set up test database environment.

        Creates a test directory and cleans up after the test.

        Yields
        ------
            None: This function is a generator that yields None.

        """
        # Create test directory if it doesn't exist
        os.makedirs("/tmp/dewey_test", exist_ok=True)
        yield
        # Clean up test directory
        try:
            os.remove("/tmp/dewey_test/dewey.duckdb")
        except FileNotFoundError:
            self.logger.info("Test database file not found, skipping removal.")

    @contextlib.contextmanager
    def mock_duckdb(self) -> Generator[Mock, None, None]:
        """
        Mock DuckDB connection.

        Yields
        ------
            Mock: A mock DuckDB connection object.

        """
        with patch("duckdb.connect") as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            yield mock_conn

    def execute(self) -> None:
        """Execute the test configuration setup."""
        self.logger.info("Setting up test configuration...")
        # Add any test configuration setup logic here

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()


@pytest.fixture(autouse=True)
def mock_env_vars() -> Generator[None, None, None]:
    """
    Fixture to mock environment variables using TestConfiguration.

    Yields
    ------
        None: This fixture yields None.

    """
    test_config = TestConfiguration()
    with test_config.mock_env_vars():
        yield


@pytest.fixture(autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    """
    Fixture to set up test database environment using TestConfiguration.

    Yields
    ------
        None: This fixture yields None.

    """
    test_config = TestConfiguration()
    with test_config.setup_test_db():
        yield


@pytest.fixture()
def mock_duckdb() -> Generator[Mock, None, None]:
    """
    Fixture to mock DuckDB connection using TestConfiguration.

    Yields
    ------
        Mock: A mock DuckDB connection object.

    """
    test_config = TestConfiguration()
    with test_config.mock_duckdb() as mock_conn:
        yield mock_conn
