"""Unit tests for the dewey.core.db.connection module."""

import os
import re
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
from typing import Dict, List, Any, Optional
from pathlib import Path

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import (
    DatabaseConnection,
    get_connection,
    get_local_connection,
    get_motherduck_connection,
    get_local_dewey_connection,
    get_modified_tables,
    DEFAULT_MOTHERDUCK_PREFIX,
    _locally_modified_tables,
    INSERT_PATTERN,
    UPDATE_PATTERN,
    DELETE_PATTERN,
    CREATE_PATTERN,
    DROP_PATTERN,
    ALTER_PATTERN,
)


class TestDatabaseConnection:
    """Tests for the DatabaseConnection class."""

    def test_init_duckdb(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test initializing a DatabaseConnection with DuckDB."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        assert conn.connection_string == str(db_path)
        assert not conn.is_motherduck
        assert conn.conn is not None
        conn.close()

    def test_init_motherduck(self, mock_base_script: MagicMock) -> None:
        """Test initializing a DatabaseConnection with MotherDuck."""
        connection_string = "md:test_db"
        with patch("dewey.core.db.connection.duckdb.connect") as mock_connect:
            conn = DatabaseConnection(connection_string)
            assert conn.connection_string == connection_string
            assert conn.is_motherduck
            assert conn.conn is not None
            mock_connect.assert_called_with(connection_string)
            conn.close()

    def test_init_connection_error(self, mock_base_script: MagicMock) -> None:
        """Test initializing a DatabaseConnection with a connection error."""
        with (
            pytest.raises(RuntimeError),
            patch(
                "dewey.core.db.connection.duckdb.connect",
                side_effect=Exception("Connection failed"),
            ),
        ):
            DatabaseConnection("test_db")

    def test_connect_duckdb(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test the _connect method with DuckDB."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.close()  # Close the initial connection
        conn.conn = None
        conn._connect()
        assert conn.conn is not None
        conn.close()

    def test_connect_motherduck(self, mock_base_script: MagicMock) -> None:
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

    def test_execute_success(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test executing a SQL query successfully."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER, name VARCHAR)")
        result = conn.execute("SELECT * FROM test")
        assert result.empty
        conn.close()

    def test_execute_with_parameters(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test executing a SQL query with parameters."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER, name VARCHAR)")
        conn.execute(
            "INSERT INTO test (id, name) VALUES (?, ?)",
            parameters={"1": 1, "2": "test"},
        )
        result = conn.execute("SELECT * FROM test")
        assert not result.empty
        assert result["id"][0] == 1
        assert result["name"][0] == "test"
        conn.close()

    def test_execute_failure(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test executing a SQL query that fails."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        with pytest.raises(RuntimeError):
            conn.execute("SELECT * FROM non_existent_table")
        conn.close()

    def test_close_success(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test closing the database connection successfully."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.close()
        assert conn.conn is None

    def test_close_error(self, tmp_path: Path, mock_base_script: MagicMock, mocker: Any) -> None:
        """Test closing the database connection with an error."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        mocker.patch.object(conn.conn, "close", side_effect=Exception("Close failed"))
        conn.close()
        assert conn.conn is None

    def test_run(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test the abstract run method (placeholder)."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        # The run method is a placeholder and should not raise any errors
        conn.run()
        conn.close()

    def test_track_modified_table_insert(self, tmp_path: Path, mock_base_script: MagicMock, mock_get_duckdb_sync: MagicMock, mock_sync_instance: MagicMock) -> None:
        """Test tracking a modified table with INSERT."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.auto_sync = True
        mock_get_duckdb_sync.return_value = mock_sync_instance
        query = "INSERT INTO my_table (id, name) VALUES (1, 'test')"
        conn._track_modified_table(query)
        assert "my_table" in _locally_modified_tables
        mock_get_duckdb_sync.assert_called_once()
        mock_sync_instance.mark_table_modified.assert_called_with("my_table")
        conn.close()
        _locally_modified_tables.clear()

    def test_track_modified_table_update(self, tmp_path: Path, mock_base_script: MagicMock, mock_get_duckdb_sync: MagicMock, mock_sync_instance: MagicMock) -> None:
        """Test tracking a modified table with UPDATE."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.auto_sync = True
        mock_get_duckdb_sync.return_value = mock_sync_instance
        query = "UPDATE my_table SET name = 'new_test' WHERE id = 1"
        conn._track_modified_table(query)
        assert "my_table" in _locally_modified_tables
        mock_get_duckdb_sync.assert_called_once()
        mock_sync_instance.mark_table_modified.assert_called_with("my_table")
        conn.close()
        _locally_modified_tables.clear()

    def test_track_modified_table_delete(self, tmp_path: Path, mock_base_script: MagicMock, mock_get_duckdb_sync: MagicMock, mock_sync_instance: MagicMock) -> None:
        """Test tracking a modified table with DELETE."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.auto_sync = True
        mock_get_duckdb_sync.return_value = mock_sync_instance
        query = "DELETE FROM my_table WHERE id = 1"
        conn._track_modified_table(query)
        assert "my_table" in _locally_modified_tables
        mock_get_duckdb_sync.assert_called_once()
        mock_sync_instance.mark_table_modified.assert_called_with("my_table")
        conn.close()
        _locally_modified_tables.clear()

    def test_track_modified_table_create(self, tmp_path: Path, mock_base_script: MagicMock, mock_get_duckdb_sync: MagicMock, mock_sync_instance: MagicMock) -> None:
        """Test tracking a modified table with CREATE."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.auto_sync = True
        mock_get_duckdb_sync.return_value = mock_sync_instance
        query = "CREATE TABLE my_table (id INTEGER, name VARCHAR)"
        conn._track_modified_table(query)
        assert "my_table" in _locally_modified_tables
        mock_get_duckdb_sync.assert_called_once()
        mock_sync_instance.mark_table_modified.assert_called_with("my_table")
        conn.close()
        _locally_modified_tables.clear()

    def test_track_modified_table_drop(self, tmp_path: Path, mock_base_script: MagicMock, mock_get_duckdb_sync: MagicMock, mock_sync_instance: MagicMock) -> None:
        """Test tracking a modified table with DROP."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.auto_sync = True
        mock_get_duckdb_sync.return_value = mock_sync_instance
        query = "DROP TABLE my_table"
        conn._track_modified_table(query)
        assert "my_table" in _locally_modified_tables
        mock_get_duckdb_sync.assert_called_once()
        mock_sync_instance.mark_table_modified.assert_called_with("my_table")
        conn.close()
        _locally_modified_tables.clear()

    def test_track_modified_table_alter(self, tmp_path: Path, mock_base_script: MagicMock, mock_get_duckdb_sync: MagicMock, mock_sync_instance: MagicMock) -> None:
        """Test tracking a modified table with ALTER."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.auto_sync = True
        mock_get_duckdb_sync.return_value = mock_sync_instance
        query = "ALTER TABLE my_table RENAME COLUMN id TO new_id"
        conn._track_modified_table(query)
        assert "my_table" in _locally_modified_tables
        mock_get_duckdb_sync.assert_called_once()
        mock_sync_instance.mark_table_modified.assert_called_with("my_table")
        conn.close()
        _locally_modified_tables.clear()

    def test_track_modified_table_motherduck(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test that modified tables are not tracked for MotherDuck connections."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(f"{DEFAULT_MOTHERDUCK_PREFIX}{db_path}")
        query = "INSERT INTO my_table (id, name) VALUES (1, 'test')"
        conn._track_modified_table(query)
        assert "my_table" not in _locally_modified_tables
        conn.close()

    def test_track_modified_table_no_auto_sync(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test that auto_sync can be disabled."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path), auto_sync=False)
        query = "INSERT INTO my_table (id, name) VALUES (1, 'test')"
        conn._track_modified_table(query)
        conn.close()
        assert "my_table" in _locally_modified_tables
        _locally_modified_tables.clear()

    def test_track_modified_table_internal_table(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test that internal tables are not tracked."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        query = "INSERT INTO sqlite_master (id, name) VALUES (1, 'test')"
        conn._track_modified_table(query)
        assert "sqlite_master" not in _locally_modified_tables
        conn.close()

        query = "INSERT INTO dewey_sync_table (id, name) VALUES (1, 'test')"
        conn._track_modified_table(query)
        assert "dewey_sync_table" not in _locally_modified_tables
        conn.close()

        query = "INSERT INTO information_schema (id, name) VALUES (1, 'test')"
        conn._track_modified_table(query)
        assert "information_schema" not in _locally_modified_tables
        conn.close()

    def test_track_modified_table_schema_table(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test that tables with schema prefixes are tracked correctly."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        query = "INSERT INTO schema.my_table (id, name) VALUES (1, 'test')"
        conn._track_modified_table(query)
        assert "my_table" in _locally_modified_tables
        conn.close()
        _locally_modified_tables.clear()

    def test_track_modified_table_quoted_table(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test that quoted tables are tracked correctly."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        query = 'INSERT INTO "my_table" (id, name) VALUES (1, \'test\')'
        conn._track_modified_table(query)
        assert "my_table" in _locally_modified_tables
        conn.close()
        _locally_modified_tables.clear()

    def test_track_modified_table_no_match(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test when no table name is matched."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        query = "SELECT * FROM my_table"
        conn._track_modified_table(query)
        assert "my_table" not in _locally_modified_tables
        conn.close()

    def test_sync_modified_tables(self, tmp_path: Path, mock_base_script: MagicMock, mock_get_duckdb_sync: MagicMock, mock_sync_instance: MagicMock) -> None:
        """Test syncing modified tables."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        mock_get_duckdb_sync.return_value = mock_sync_instance
        _locally_modified_tables.add("my_table")
        conn._sync_modified_tables()
        mock_get_duckdb_sync.assert_called_once()
        mock_sync_instance.sync_modified_to_motherduck.assert_called_once()
        conn.close()
        _locally_modified_tables.clear()

    def test_sync_modified_tables_error(self, tmp_path: Path, mock_base_script: MagicMock, mock_get_duckdb_sync: MagicMock) -> None:
        """Test syncing modified tables with an error."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        mock_get_duckdb_sync.side_effect = Exception("Sync failed")
        _locally_modified_tables.add("my_table")
        conn._sync_modified_tables()
        conn.close()
        _locally_modified_tables.clear()

    def test_close_with_sync(self, tmp_path: Path, mock_base_script: MagicMock, mock_get_duckdb_sync: MagicMock, mock_sync_instance: MagicMock) -> None:
        """Test closing the connection with sync."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        mock_get_duckdb_sync.return_value = mock_sync_instance
        _locally_modified_tables.add("my_table")
        conn.close()
        mock_get_duckdb_sync.assert_called_once()
        mock_sync_instance.sync_modified_to_motherduck.assert_called_once()
        assert conn.conn is None
        _locally_modified_tables.clear()

    def test_close_without_sync(self, tmp_path: Path, mock_base_script: MagicMock) -> None:
        """Test closing the connection without sync."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        conn.close()
        assert conn.conn is None

    def test_trigger_sync(self, tmp_path: Path, mock_base_script: MagicMock, mock_get_duckdb_sync: MagicMock, mock_sync_instance: MagicMock) -> None:
        """Test triggering a sync."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        mock_get_duckdb_sync.return_value = mock_sync_instance
        conn._trigger_sync("my_table")
        mock_get_duckdb_sync.assert_called_once()
        mock_sync_instance.mark_table_modified.assert_called_with("my_table")
        conn.close()

    def test_trigger_sync_error(self, tmp_path: Path, mock_base_script: MagicMock, mock_get_duckdb_sync: MagicMock) -> None:
        """Test triggering a sync with an error."""
        db_path = tmp_path / "test.duckdb"
        conn = DatabaseConnection(str(db_path))
        mock_get_duckdb_sync.side_effect = Exception("Sync failed")
        conn._trigger_sync("my_table")
        conn.close()


class TestGetConnection:
    """Tests for the get_connection function."""

    def test_get_connection_duckdb(self, tmp_path: Path) -> None:
        """Test getting a DuckDB connection."""
        db_path = tmp_path / "test.duckdb"
        config = {"connection_string": str(db_path), "motherduck": False}
        conn = get_connection(config)
        assert isinstance(conn, DatabaseConnection)
        assert conn.connection_string == str(db_path)
        assert not conn.is_motherduck
        conn.close()

    def test_get_connection_motherduck(self, mock_os_environ: MagicMock) -> None:
        """Test getting a MotherDuck connection."""
        config = {"motherduck": True, "token": "test_token", "database": "test_db"}
        mock_os_environ["MOTHERDUCK_TOKEN"] = "test_token"
        conn = get_connection(config)
        assert isinstance(conn, DatabaseConnection)
        assert conn.is_motherduck
        conn.close()

    def test_get_connection_motherduck_no_token(self) -> None:
        """Test getting a MotherDuck connection without a token."""
        config = {"motherduck": True, "database": "test_db"}
        with pytest.raises(ValueError, match="MotherDuck token is required"):
            get_connection(config)

    def test_get_connection_motherduck_token_from_env(self, mock_os_environ: MagicMock) -> None:
        """Test getting a MotherDuck connection with token from environment."""
        config = {"motherduck": True, "database": "test_db"}
        mock_os_environ["MOTHERDUCK_TOKEN"] = "test_token"
        conn = get_connection(config)
        assert isinstance(conn, DatabaseConnection)
        assert conn.is_motherduck
        conn.close()

    def test_get_connection_additional_kwargs(self, tmp_path: Path) -> None:
        """Test getting a connection with additional kwargs."""
        db_path = tmp_path / "test.duckdb"
        config = {
            "connection_string": str(db_path),
            "motherduck": False,
            "read_only": True,
        }
        conn = get_connection(config)
        assert isinstance(conn, DatabaseConnection)
        assert conn.connection_string == str(db_path)
        assert not conn.is_motherduck
        conn.close()


class TestGetMotherduckConnection:
    """Tests for the get_motherduck_connection function."""

    def test_get_motherduck_connection_success(self, mock_os_environ: MagicMock) -> None:
        """Test getting a MotherDuck connection successfully."""
        mock_os_environ["MOTHERDUCK_TOKEN"] = "test_token"
        conn = get_motherduck_connection("test_db")
        assert isinstance(conn, DatabaseConnection)
        assert conn.is_motherduck
        conn.close()

    def test_get_motherduck_connection_no_token(self) -> None:
        """Test getting a MotherDuck connection without a token."""
        with pytest.raises(ValueError, match="MotherDuck token is required"):
            get_motherduck_connection("test_db")

    def test_get_motherduck_connection_token_provided(self) -> None:
        """Test getting a MotherDuck connection with a token provided."""
        conn = get_motherduck_connection("test_db", token="test_token")
        assert isinstance(conn, DatabaseConnection)
        assert conn.is_motherduck
        conn.close()


class TestGetLocalConnection:
    """Tests for the get_local_connection function."""

    def test_get_local_connection_default_path(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test getting a local connection with the default path."""
        default_path = tmp_path / "default.duckdb"
        monkeypatch.setattr("dewey.core.db.connection.Path.home", lambda: tmp_path)
        conn = get_local_connection()
        assert isinstance(conn, DatabaseConnection)
        assert conn.connection_string == str(default_path)
        assert not conn.is_motherduck
        conn.close()

    def test_get_local_connection_custom_path(self, tmp_path: Path) -> None:
        """Test getting a local connection with a custom path."""
        db_path = tmp_path / "test.duckdb"
        conn = get_local_connection(db_path)
        assert isinstance(conn, DatabaseConnection)
        assert conn.connection_string == str(db_path)
        assert not conn.is_motherduck
        conn.close()


class TestGetLocalDeweyConnection:
    """Tests for the get_local_dewey_connection function."""

    @patch("dewey.core.db.connection.Path.cwd")
    @patch("dewey.core.db.connection.get_local_connection")
    def test_get_local_dewey_connection_repo_root(
        self,
        mock_get_local_connection: MagicMock,
        mock_path_cwd: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test getting a local Dewey connection with repo root."""
        mock_path_cwd.return_value = tmp_path
        (tmp_path / "pyproject.toml").touch()
        get_local_dewey_connection()
        mock_get_local_connection.assert_called_once_with(tmp_path / "dewey.duckdb")

    @patch("dewey.core.db.connection.Path.cwd")
    @patch("dewey.core.db.connection.get_local_connection")
    def test_get_local_dewey_connection_no_repo_root(
        self,
        mock_get_local_connection: MagicMock,
        mock_path_cwd: MagicMock,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """Test getting a local Dewey connection without repo root."""
        mock_path_cwd.return_value = tmp_path
        monkeypatch.setattr("dewey.core.db.connection.Path.home", lambda: tmp_path)
        get_local_dewey_connection()
        mock_get_local_connection.assert_called_once_with()

    @patch("dewey.core.db.connection.Path.cwd")
    @patch("dewey.core.db.connection.get_local_connection")
    def test_get_local_dewey_connection_exception(
        self,
        mock_get_local_connection: MagicMock,
        mock_path_cwd: MagicMock,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """Test getting a local Dewey connection with exception."""
        mock_path_cwd.return_value = tmp_path
        mock_get_local_connection.side_effect = Exception("Failed to connect")
        monkeypatch.setattr("dewey.core.db.connection.Path.home", lambda: tmp_path)
        get_local_dewey_connection()
        mock_get_local_connection.assert_called_with()


class TestGetModifiedTables:
    """Tests for the get_modified_tables function."""

    def test_get_modified_tables(self) -> None:
        """Test getting modified tables."""
        _locally_modified_tables.add("table1")
        _locally_modified_tables.add("table2")
        modified_tables = get_modified_tables()
        assert "table1" in modified_tables
        assert "table2" in modified_tables
        _locally_modified_tables.clear()

class TestRegexPatterns:
    """Tests for the regex patterns."""

    def test_insert_pattern(self) -> None:
        """Test the INSERT_PATTERN."""
        assert INSERT_PATTERN.search("INSERT INTO my_table (id) VALUES (1)")
        assert INSERT_PATTERN.search(" insert into my_table (id) VALUES (1)")
        assert not INSERT_PATTERN.search("SELECT * FROM my_table")

    def test_update_pattern(self) -> None:
        """Test the UPDATE_PATTERN."""
        assert UPDATE_PATTERN.search("UPDATE my_table SET id = 1")
        assert UPDATE_PATTERN.search(" update my_table SET id = 1")
        assert not UPDATE_PATTERN.search("SELECT * FROM my_table")

    def test_delete_pattern(self) -> None:
        """Test the DELETE_PATTERN."""
        assert DELETE_PATTERN.search("DELETE FROM my_table WHERE id = 1")
        assert DELETE_PATTERN.search(" delete from my_table WHERE id = 1")
        assert not DELETE_PATTERN.search("SELECT * FROM my_table")

    def test_create_pattern(self) -> None:
        """Test the CREATE_PATTERN."""
        assert CREATE_PATTERN.search("CREATE TABLE my_table (id INTEGER)")
        assert CREATE_PATTERN.search(" create table my_table (id INTEGER)")
        assert not CREATE_PATTERN.search("SELECT * FROM my_table")

    def test_drop_pattern(self) -> None:
        """Test the DROP_PATTERN."""
        assert DROP_PATTERN.search("DROP TABLE my_table")
        assert DROP_PATTERN.search(" drop table my_table")
        assert not DROP_PATTERN.search("SELECT * FROM my_table")

    def test_alter_pattern(self) -> None:
        """Test the ALTER_PATTERN."""
        assert ALTER_PATTERN.search("ALTER TABLE my_table RENAME COLUMN id TO new_id")
        assert ALTER_PATTERN.search(" alter table my_table RENAME COLUMN id TO new_id")
        assert not ALTER_PATTERN.search("SELECT * FROM my_table")
