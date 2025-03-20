"""Unit tests for the dewey.core.db.connection module."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch

import duckdb
import pytest

from dewey.core.db.connection import (
    DatabaseConnection,
    get_connection,
    get_local_connection,
    get_motherduck_connection,
)
from dewey.core.base_script import BaseScript


class TestDatabaseConnection:
    """Tests for the DatabaseConnection class."""

    @pytest.fixture
    def mock_base_script(self, mocker):
        """Mocks the BaseScript class."""
        mock = mocker.MagicMock(spec=BaseScript)
        mock.logger = mocker.MagicMock()
        mock.get_config_value.return_value = 'md:'
        return mock

    def test_init_duckdb(self, tmp_path, mock_base_script):
        """Test initializing a DatabaseConnection with DuckDB."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        assert conn.connection_string == str(db_path)
        assert not conn.is_motherduck
        assert conn.conn is not None
        conn.close()

    def test_init_motherduck(self, mock_base_script):
        """Test initializing a DatabaseConnection with MotherDuck."""
        connection_string = "md:test_db"
        with patch("dewey.core.db.connection.duckdb.connect") as mock_connect:
            conn = DatabaseConnection(connection_string)
            assert conn.connection_string == connection_string
            assert conn.is_motherduck
            assert conn.conn is not None
            mock_connect.assert_called_with(connection_string)
            conn.close()

    def test_init_connection_error(self, mock_base_script):
        """Test initializing a DatabaseConnection with a connection error."""
        with pytest.raises(RuntimeError), patch(
            "dewey.core.db.connection.duckdb.connect", side_effect=Exception("Connection failed")
        ):
            DatabaseConnection("test_db")

    def test_connect_duckdb(self, tmp_path, mock_base_script):
        """Test the _connect method with DuckDB."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.close()  # Close the initial connection
        conn.conn = None
        conn._connect()
        assert conn.conn is not None
        conn.close()

    def test_connect_motherduck(self, mock_base_script):
        """Test the _connect method with MotherDuck."""
        connection_string = "md:test_db"
        conn = DatabaseConnection(connection_string)
        conn.close()  # Close the initial connection
        conn.conn = None
        with patch("dewey.core.db.connection.duckdb.connect") as mock_connect:
            conn._connect()
            assert conn.conn is not None
            mock_connect.assert_called_with(connection_string)
        conn.close()

    def test_execute_success(self, tmp_path, mock_base_script):
        """Test executing a SQL query successfully."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER, name VARCHAR)")
        result = conn.execute("SELECT * FROM test")
        assert result.empty
        conn.close()

    def test_execute_with_parameters(self, tmp_path, mock_base_script):
        """Test executing a SQL query with parameters."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER, name VARCHAR)")
        conn.execute("INSERT INTO test (id, name) VALUES (?, ?)", parameters={"1": 1, "2": "test"})
        result = conn.execute("SELECT * FROM test")
        assert not result.empty
        assert result["id"][0] == 1
        assert result["name"][0] == "test"
        conn.close()

    def test_execute_failure(self, tmp_path, mock_base_script):
        """Test executing a SQL query that fails."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        with pytest.raises(RuntimeError):
            conn.execute("SELECT * FROM non_existent_table")
        conn.close()

    def test_close_success(self, tmp_path, mock_base_script):
        """Test closing the database connection successfully."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.close()
        assert conn.conn is None

    def test_close_error(self, tmp_path, mock_base_script, mocker):
        """Test closing the database connection with an error."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        mocker.patch.object(conn.conn, "close", side_effect=Exception("Close failed"))
        conn.close()
        assert conn.conn is None

    def test_run(self, tmp_path, mock_base_script):
        """Test the abstract run method (placeholder)."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        # The run method is a placeholder and should not raise any errors
        conn.run()
        conn.close()


class TestGetConnection:
    """Tests for the get_connection function."""

    def test_get_connection_duckdb(self, tmp_path):
        """Test getting a DuckDB connection."""
        db_path = tmp_path / "test.duckdb"
        config = {"connection_string": str(db_path), "motherduck": False}
        conn = get_connection(config)
        assert isinstance(conn, DatabaseConnection)
        assert conn.connection_string == str(db_path)
        assert not conn.is_motherduck
        conn.close()

    def test_get_connection_motherduck(self):
        """Test getting a MotherDuck connection."""
        config = {"motherduck": True, "token": "test_token", "database": "test_db"}
        with patch.dict(os.environ, {"MOTHERDUCK_TOKEN": "test_token"}):
            conn = get_connection(config)
            assert isinstance(conn, DatabaseConnection)
            assert conn.is_motherduck
            conn.close()

    def test_get_connection_motherduck_no_token(self):
        """Test getting a MotherDuck connection without a token."""
        config = {"motherduck": True, "database": "test_db"}
        with pytest.raises(ValueError, match="MotherDuck token is required"):
            get_connection(config)

    def test_get_connection_motherduck_token_from_env(self):
        """Test getting a MotherDuck connection with token from environment."""
        config = {"motherduck": True, "database": "test_db"}
        with patch.dict(os.environ, {"MOTHERDUCK_TOKEN": "test_token"}):
            conn = get_connection(config)
            assert isinstance(conn, DatabaseConnection)
            assert conn.is_motherduck
            conn.close()

    def test_get_connection_additional_kwargs(self, tmp_path):
        """Test getting a connection with additional kwargs."""
        db_path = tmp_path / "test.duckdb"
        config = {"connection_string": str(db_path), "motherduck": False, "read_only": True}
        conn = get_connection(config)
        assert isinstance(conn, DatabaseConnection)
        assert conn.connection_string == str(db_path)
        assert not conn.is_motherduck
        conn.close()


class TestGetMotherduckConnection:
    """Tests for the get_motherduck_connection function."""

    def test_get_motherduck_connection_success(self):
        """Test getting a MotherDuck connection successfully."""
        with patch.dict(os.environ, {"MOTHERDUCK_TOKEN": "test_token"}):
            conn = get_motherduck_connection("test_db")
            assert isinstance(conn, DatabaseConnection)
            assert conn.is_motherduck
            conn.close()

    def test_get_motherduck_connection_no_token(self):
        """Test getting a MotherDuck connection without a token."""
        with pytest.raises(ValueError, match="MotherDuck token is required"):
            get_motherduck_connection("test_db")

    def test_get_motherduck_connection_token_provided(self):
        """Test getting a MotherDuck connection with a token provided."""
        conn = get_motherduck_connection("test_db", token="test_token")
        assert isinstance(conn, DatabaseConnection)
        assert conn.is_motherduck
        conn.close()


class TestGetLocalConnection:
    """Tests for the get_local_connection function."""

    def test_get_local_connection_default_path(self, tmp_path, monkeypatch):
        """Test getting a local connection with the default path."""
        default_path = tmp_path / "default.duckdb"
        monkeypatch.setattr("dewey.core.db.connection.Path.home", lambda: tmp_path)
        conn = get_local_connection()
        assert isinstance(conn, DatabaseConnection)
        assert conn.connection_string == str(default_path)
        assert not conn.is_motherduck
        conn.close()

    def test_get_local_connection_custom_path(self, tmp_path):
        """Test getting a local connection with a custom path."""
        db_path = tmp_path / "test.duckdb"
        conn = get_local_connection(db_path)
        assert isinstance(conn, DatabaseConnection)
        assert conn.connection_string == str(db_path)
        assert not conn.is_motherduck
        conn.close()
