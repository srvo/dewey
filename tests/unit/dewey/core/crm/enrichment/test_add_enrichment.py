import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from dewey.core.crm.enrichment.add_enrichment import AddEnrichmentCapabilities
from dewey.core.base_script import BaseScript
from pathlib import Path
from typing import Any


class TestAddEnrichmentCapabilities:
    """Tests for the AddEnrichmentCapabilities class."""

    @pytest.fixture
    def add_enrichment_capabilities(self) -> AddEnrichmentCapabilities:
        """Fixture to create an instance of AddEnrichmentCapabilities."""
        return AddEnrichmentCapabilities()

    @pytest.fixture
    def mock_base_script(self, mocker: Any) -> MagicMock:
        """Fixture to mock BaseScript."""
        mock = mocker.MagicMock(spec=BaseScript)
        mock.config = {"crm": {"db_path": ":memory:"}}
        mock.logger = mocker.MagicMock()
        return mock

    @pytest.fixture
    def mock_sqlite_connection(self, mocker: Any) -> MagicMock:
        """Fixture to mock sqlite3.connect."""
        mock_connection = mocker.MagicMock(spec=sqlite3.Connection)
        mock_cursor = mocker.MagicMock(spec=sqlite3.Cursor)
        mock_connection.cursor.return_value = mock_cursor
        mocker.patch("sqlite3.connect", return_value=mock_connection)
        return mock_connection

    def test_init(self, add_enrichment_capabilities: AddEnrichmentCapabilities) -> None:
        """Test the __init__ method."""
        assert add_enrichment_capabilities.config_section == "crm"
        assert add_enrichment_capabilities.requires_db is True

    @patch(
        "dewey.core.crm.enrichment.add_enrichment.AddEnrichmentCapabilities.get_config_value"
    )
    def test_run_success(
        self,
        mock_get_config_value: MagicMock,
        add_enrichment_capabilities: AddEnrichmentCapabilities,
        mock_sqlite_connection: MagicMock,
    ) -> None:
        """Test the run method with successful database operations."""
        mock_get_config_value.return_value = ":memory:"
        add_enrichment_capabilities.logger = MagicMock()

        add_enrichment_capabilities.run()

        cursor = mock_sqlite_connection.cursor()
        assert cursor.execute.call_count == 10
        mock_sqlite_connection.commit.assert_called_once()
        mock_sqlite_connection.close.assert_called_once()
        add_enrichment_capabilities.logger.info.assert_called_with(
            "Successfully added enrichment capabilities"
        )

    @patch(
        "dewey.core.crm.enrichment.add_enrichment.AddEnrichmentCapabilities.get_config_value"
    )
    def test_run_db_error(
        self,
        mock_get_config_value: MagicMock,
        add_enrichment_capabilities: AddEnrichmentCapabilities,
        mock_sqlite_connection: MagicMock,
    ) -> None:
        """Test the run method with a database error."""
        mock_get_config_value.return_value = ":memory:"
        cursor = mock_sqlite_connection.cursor()
        cursor.execute.side_effect = sqlite3.Error("Database error")
        add_enrichment_capabilities.logger = MagicMock()

        with pytest.raises(sqlite3.Error):
            add_enrichment_capabilities.run()

        mock_sqlite_connection.rollback.assert_called_once()
        mock_sqlite_connection.close.assert_called_once()
        add_enrichment_capabilities.logger.exception.assert_called_once()

    @patch(
        "dewey.core.crm.enrichment.add_enrichment.AddEnrichmentCapabilities.get_config_value"
    )
    def test_run_general_error(
        self,
        mock_get_config_value: MagicMock,
        add_enrichment_capabilities: AddEnrichmentCapabilities,
        mock_sqlite_connection: MagicMock,
    ) -> None:
        """Test the run method with a general exception."""
        mock_get_config_value.return_value = ":memory:"
        mock_sqlite_connection.cursor.side_effect = Exception("General error")
        add_enrichment_capabilities.logger = MagicMock()

        with pytest.raises(Exception):
            add_enrichment_capabilities.run()

        mock_sqlite_connection.rollback.assert_called_once()
        mock_sqlite_connection.close.assert_called_once()
        add_enrichment_capabilities.logger.exception.assert_called_once()

    @patch(
        "dewey.core.crm.enrichment.add_enrichment.AddEnrichmentCapabilities.get_config_value"
    )
    def test_run_no_connection(
        self,
        mock_get_config_value: MagicMock,
        add_enrichment_capabilities: AddEnrichmentCapabilities,
    ) -> None:
        """Test the run method when connection fails."""
        mock_get_config_value.return_value = ":memory:"
        with patch("sqlite3.connect", side_effect=Exception("Connection failed")):
            add_enrichment_capabilities.logger = MagicMock()
            with pytest.raises(Exception):
                add_enrichment_capabilities.run()

    @patch(
        "dewey.core.crm.enrichment.add_enrichment.AddEnrichmentCapabilities.get_config_value"
    )
    def test_execute(
        self,
        mock_get_config_value: MagicMock,
        add_enrichment_capabilities: AddEnrichmentCapabilities,
        mocker: Any,
    ) -> None:
        """Test the execute method."""
        mock_get_config_value.return_value = ":memory:"
        add_enrichment_capabilities.run = mocker.MagicMock()
        add_enrichment_capabilities.parse_args = mocker.MagicMock()
        add_enrichment_capabilities._cleanup = mocker.MagicMock()
        add_enrichment_capabilities.logger = MagicMock()

        add_enrichment_capabilities.execute()

        add_enrichment_capabilities.parse_args.assert_called_once()
        add_enrichment_capabilities.run.assert_called_once()
        add_enrichment_capabilities._cleanup.assert_called_once()
        add_enrichment_capabilities.logger.info.assert_called()

    def test_cleanup(
        self,
        add_enrichment_capabilities: AddEnrichmentCapabilities,
        mock_sqlite_connection: MagicMock,
    ) -> None:
        """Test the _cleanup method."""
        add_enrichment_capabilities.db_conn = mock_sqlite_connection
        add_enrichment_capabilities.logger = MagicMock()

        add_enrichment_capabilities._cleanup()

        mock_sqlite_connection.close.assert_called_once()
        add_enrichment_capabilities.logger.debug.assert_called_with(
            "Closing database connection"
        )

    def test_cleanup_no_connection(
        self, add_enrichment_capabilities: AddEnrichmentCapabilities
    ) -> None:
        """Test the _cleanup method when there is no database connection."""
        add_enrichment_capabilities.db_conn = None
        add_enrichment_capabilities.logger = MagicMock()

        add_enrichment_capabilities._cleanup()

        # Assert that close is not called and no error is raised
        assert not hasattr(add_enrichment_capabilities.db_conn, "close")

    def test_cleanup_close_error(
        self,
        add_enrichment_capabilities: AddEnrichmentCapabilities,
        mock_sqlite_connection: MagicMock,
    ) -> None:
        """Test the _cleanup method when closing the connection raises an exception."""
        mock_sqlite_connection.close.side_effect = Exception("Close error")
        add_enrichment_capabilities.db_conn = mock_sqlite_connection
        add_enrichment_capabilities.logger = MagicMock()

        add_enrichment_capabilities._cleanup()

        mock_sqlite_connection.close.assert_called_once()
        add_enrichment_capabilities.logger.warning.assert_called_once()

    def test_get_path_absolute(
        self, add_enrichment_capabilities: AddEnrichmentCapabilities
    ) -> None:
        """Test get_path with an absolute path."""
        absolute_path = "/absolute/path"
        result = add_enrichment_capabilities.get_path(absolute_path)
        assert str(result) == absolute_path

    def test_get_path_relative(
        self, add_enrichment_capabilities: AddEnrichmentCapabilities
    ) -> None:
        """Test get_path with a relative path."""
        relative_path = "relative/path"
        result = add_enrichment_capabilities.get_path(relative_path)
        expected_path = Path(__file__).parent.parent.parent.parent / relative_path
        assert str(result) == str(expected_path)

    def test_get_config_value_existing(
        self, add_enrichment_capabilities: AddEnrichmentCapabilities
    ) -> None:
        """Test get_config_value with an existing key."""
        add_enrichment_capabilities.config = {"level1": {"level2": "value"}}
        result = add_enrichment_capabilities.get_config_value("level1.level2")
        assert result == "value"

    def test_get_config_value_default(
        self, add_enrichment_capabilities: AddEnrichmentCapabilities
    ) -> None:
        """Test get_config_value with a non-existing key and a default value."""
        add_enrichment_capabilities.config = {"level1": {"level2": "value"}}
        result = add_enrichment_capabilities.get_config_value(
            "level1.level3", "default"
        )
        assert result == "default"

    def test_get_config_value_missing(
        self, add_enrichment_capabilities: AddEnrichmentCapabilities
    ) -> None:
        """Test get_config_value with a non-existing key and no default value."""
        add_enrichment_capabilities.config = {"level1": {"level2": "value"}}
        result = add_enrichment_capabilities.get_config_value("level1.level3")
        assert result is None
