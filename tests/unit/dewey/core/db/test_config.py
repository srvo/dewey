import logging
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.base_script import BaseScript
from dewey.core.db.config import Config
from dewey.core.db.connection import DatabaseConnection, get_connection, get_motherduck_connection


class TestConfig:
    """Tests for the Config class."""

    @pytest.fixture
    def mock_base_script(self, mocker: MagicMock) -> MagicMock:
        """Mocks the BaseScript class."""
        mock = mocker.MagicMock(spec=BaseScript)
        mock.config = {"host": "test_host"}
        mock.logger = mocker.MagicMock()
        return mock

    @pytest.fixture
    def config_instance(self, mocker: MagicMock) -> Config:
        """Creates an instance of the Config class with mocked dependencies."""
        mocker.patch("dewey.core.db.config.BaseScript.__init__", return_value=None)
        config = Config()
        config.config = {"host": "test_host"}
        config.logger = mocker.MagicMock()
        return config

    def test_config_initialization(self, mocker: MagicMock) -> None:
        """Tests the initialization of the Config class."""
        mocker.patch("dewey.core.db.config.BaseScript.__init__", return_value=None)
        config = Config()
        assert config.config_section == "db_config"
        assert config.requires_db is True

    def test_run_method(self, config_instance: Config, mocker: MagicMock) -> None:
        """Tests the run method of the Config class."""
        mock_get_config_value = mocker.patch.object(config_instance, "get_config_value", return_value="localhost")
        mock_get_motherduck_connection = mocker.patch(
            "dewey.core.db.config.get_motherduck_connection", return_value=mocker.MagicMock(spec=DatabaseConnection)
        )
        mock_get_connection = mocker.patch(
            "dewey.core.db.config.get_connection", return_value=mocker.MagicMock(spec=DatabaseConnection)
        )

        config_instance.run()

        config_instance.logger.info.assert_called()
        mock_get_config_value.assert_called_with("host", "localhost")
        mock_get_motherduck_connection.assert_called_with(config_instance.config.get("test_config", {}))
        mock_get_connection.assert_called_with(config_instance.config.get("test_config", {}))

    def test_run_method_exception(self, config_instance: Config, mocker: MagicMock) -> None:
        """Tests the run method of the Config class when an exception occurs."""
        mocker.patch.object(config_instance, "get_config_value", return_value="localhost")
        mocker.patch("dewey.core.db.config.get_motherduck_connection", side_effect=Exception("Test Exception"))

        with pytest.raises(Exception, match="Test Exception"):
            config_instance.run()

        config_instance.logger.error.assert_called()

    def test_get_motherduck_connection_success(self, mocker: MagicMock) -> None:
        """Tests successful retrieval of a MotherDuck connection."""
        mock_connection = mocker.MagicMock(spec=DatabaseConnection)
        mocker.patch("dewey.core.db.connection.DatabaseConnection", return_value=mock_connection)

        config = {"motherduck_token": "test_token"}
        connection = get_motherduck_connection(config)

        assert connection is mock_connection
        # DatabaseConnection was called with the correct arguments
        # dewey.core.db.connection.DatabaseConnection.assert_called_with(drivername="duckdb", **config)

    def test_get_motherduck_connection_no_token(self, mocker: MagicMock) -> None:
        """Tests retrieval of a MotherDuck connection when no token is provided."""
        with pytest.raises(ValueError, match="MotherDuck token is required"):
            get_motherduck_connection({})

    def test_get_connection_success(self, mocker: MagicMock) -> None:
        """Tests successful retrieval of a generic database connection."""
        mock_connection = mocker.MagicMock(spec=DatabaseConnection)
        mocker.patch("dewey.core.db.connection.DatabaseConnection", return_value=mock_connection)

        config = {"host": "test_host", "port": 1234, "user": "test_user", "password": "test_password", "database": "test_db"}
        connection = get_connection(config)

        assert connection is mock_connection
        # dewey.core.db.connection.DatabaseConnection.assert_called_with(**config)

    def test_get_connection_missing_params(self) -> None:
        """Tests retrieval of a generic database connection when parameters are missing."""
        with pytest.raises(ValueError, match="Missing required database parameters"):
            get_connection({})

    def test_get_connection_connection_string(self, mocker: MagicMock) -> None:
        """Tests retrieval of a generic database connection using a connection string."""
        mock_connection = mocker.MagicMock(spec=DatabaseConnection)
        mocker.patch("dewey.core.db.connection.DatabaseConnection", return_value=mock_connection)

        config = {"connection_string": "test_connection_string"}
        connection = get_connection(config)

        assert connection is mock_connection
        # dewey.core.db.connection.DatabaseConnection.assert_called_with(connection_string="test_connection_string")

    def test_get_connection_connection_string_and_params(self, mocker: MagicMock) -> None:
        """Tests retrieval of a generic database connection using both a connection string and parameters."""
        mock_connection = mocker.MagicMock(spec=DatabaseConnection)
        mocker.patch("dewey.core.db.connection.DatabaseConnection", return_value=mock_connection)

        config = {
            "connection_string": "test_connection_string",
            "host": "test_host",
            "port": 1234,
            "user": "test_user",
            "password": "test_password",
            "database": "test_db",
        }
        connection = get_connection(config)

        assert connection is mock_connection
        # dewey.core.db.connection.DatabaseConnection.assert_called_with(connection_string="test_connection_string")
