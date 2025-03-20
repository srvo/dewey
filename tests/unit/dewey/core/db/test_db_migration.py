"""Unit tests for the dewey.core.db.db_migration module."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.base_script import BaseScript
from dewey.core.db.db_migration import DBMigration
from dewey.core.db import utils
from dewey.llm import llm_utils


class TestDBMigration:
    """Test suite for the DBMigration class."""

    @pytest.fixture
    def db_migration(self) -> DBMigration:
        """Fixture to create a DBMigration instance."""
        return DBMigration()

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture to mock BaseScript."""
        with patch("dewey.core.db.db_migration.BaseScript", autospec=True) as MockBaseScript:
            yield MockBaseScript

    @pytest.fixture
    def mock_db_conn(self) -> MagicMock:
        """Fixture to mock DatabaseConnection."""
        mock_conn = MagicMock()
        mock_conn.connect.return_value.__enter__.return_value = mock_conn
        return mock_conn

    @pytest.fixture
    def mock_utils(self) -> MagicMock:
        """Fixture to mock the utils module."""
        with patch("dewey.core.db.db_migration.utils", autospec=True) as mock:
            yield mock

    @pytest.fixture
    def mock_llm_utils(self) -> MagicMock:
        """Fixture to mock the llm_utils module."""
        with patch("dewey.core.db.db_migration.llm_utils", autospec=True) as mock:
            yield mock

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Fixture to mock the logger."""
        mock_logger = MagicMock()
        return mock_logger

    @pytest.fixture
    def mock_config(self) -> dict:
        """Fixture to mock the configuration."""
        return {
            "db_migration": {
                "db_url": "test_db_url"
            },
            "core": {
                "database": {
                    "db_url": "test_db_url"
                }
            },
            "llm": {}
        }

    def test_init(self, mock_base_script: MagicMock) -> None:
        """Test the __init__ method."""
        db_migration = DBMigration()
        mock_base_script.assert_called_once_with(config_section='db_migration', requires_db=True)
        assert db_migration.name == "DBMigration"

    def test_run_success(
        self,
        db_migration: DBMigration,
        mock_db_conn: MagicMock,
        mock_utils: MagicMock,
        mock_llm_utils: MagicMock,
        mock_logger: MagicMock,
        mock_config: dict
    ) -> None:
        """Test the run method with successful database migration."""
        db_migration.logger = mock_logger
        db_migration.db_conn = mock_db_conn
        db_migration.llm_client = MagicMock()
        db_migration.config = mock_config

        mock_utils.table_exists.return_value = True
        mock_utils.execute_query.return_value = "test_result"
        mock_llm_utils.generate_response.return_value = "test_llm_response"
        db_migration.get_config_value = MagicMock(return_value="test_db_url")

        db_migration.run()

        mock_logger.info.assert_any_call("Starting database migration process.")
        mock_logger.info.assert_any_call("Using database URL: test_db_url")
        mock_utils.table_exists.assert_called_once()
        mock_utils.execute_query.assert_called_once()
        mock_llm_utils.generate_response.assert_called_once()
        mock_logger.info.assert_any_call("Database migration completed successfully.")

    def test_run_table_not_exists(
        self,
        db_migration: DBMigration,
        mock_db_conn: MagicMock,
        mock_utils: MagicMock,
        mock_llm_utils: MagicMock,
        mock_logger: MagicMock,
        mock_config: dict
    ) -> None:
        """Test the run method when the table does not exist."""
        db_migration.logger = mock_logger
        db_migration.db_conn = mock_db_conn
        db_migration.llm_client = MagicMock()
        db_migration.config = mock_config

        mock_utils.table_exists.return_value = False
        mock_utils.execute_query.return_value = "test_result"
        mock_llm_utils.generate_response.return_value = "test_llm_response"
        db_migration.get_config_value = MagicMock(return_value="test_db_url")

        db_migration.run()

        mock_logger.info.assert_any_call("Starting database migration process.")
        mock_logger.info.assert_any_call("Using database URL: test_db_url")
        mock_utils.table_exists.assert_called_once()
        mock_logger.info.assert_any_call("Table 'my_table' does not exist.")
        mock_utils.execute_query.assert_called_once()
        mock_llm_utils.generate_response.assert_called_once()
        mock_logger.info.assert_any_call("Database migration completed successfully.")

    def test_run_llm_error(
        self,
        db_migration: DBMigration,
        mock_db_conn: MagicMock,
        mock_utils: MagicMock,
        mock_llm_utils: MagicMock,
        mock_logger: MagicMock,
        mock_config: dict
    ) -> None:
        """Test the run method with an error during the LLM call."""
        db_migration.logger = mock_logger
        db_migration.db_conn = mock_db_conn
        db_migration.llm_client = MagicMock()
        db_migration.config = mock_config

        mock_utils.table_exists.return_value = True
        mock_utils.execute_query.return_value = "test_result"
        mock_llm_utils.generate_response.side_effect = Exception("LLM error")
        db_migration.get_config_value = MagicMock(return_value="test_db_url")

        db_migration.run()

        mock_logger.info.assert_any_call("Starting database migration process.")
        mock_logger.info.assert_any_call("Using database URL: test_db_url")
        mock_utils.table_exists.assert_called_once()
        mock_utils.execute_query.assert_called_once()
        mock_llm_utils.generate_response.assert_called_once()
        mock_logger.error.assert_called_with("Error during LLM call: LLM error")
        mock_logger.info.assert_any_call("Database migration completed successfully.")

    def test_run_migration_failure(
        self,
        db_migration: DBMigration,
        mock_db_conn: MagicMock,
        mock_utils: MagicMock,
        mock_llm_utils: MagicMock,
        mock_logger: MagicMock,
        mock_config: dict
    ) -> None:
        """Test the run method with a general exception during migration."""
        db_migration.logger = mock_logger
        db_migration.db_conn = mock_db_conn
        db_migration.llm_client = MagicMock()
        db_migration.config = mock_config

        mock_utils.table_exists.side_effect = Exception("Migration error")
        db_migration.get_config_value = MagicMock(return_value="test_db_url")

        with pytest.raises(Exception, match="Migration error"):
            db_migration.run()

        mock_logger.info.assert_any_call("Starting database migration process.")
        mock_logger.info.assert_any_call("Using database URL: test_db_url")
        mock_utils.table_exists.assert_called_once()
        mock_logger.error.assert_called_with(
            "Database migration failed: Migration error", exc_info=True
        )
