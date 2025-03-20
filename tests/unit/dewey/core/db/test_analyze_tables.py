import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.db.analyze_tables import AnalyzeTables


class TestAnalyzeTables:
    """Unit tests for the AnalyzeTables class."""

    @pytest.fixture
    def mock_base_script(self):
        """Mocks the BaseScript class and its methods."""
        with patch(
            "dewey.core.db.analyze_tables.BaseScript", autospec=True
        ) as MockBaseScript:
            mock_instance = MockBaseScript.return_value
            mock_instance.logger = MagicMock()
            mock_instance.get_config_value.return_value = "test_db"
            mock_instance.db_conn = MagicMock()
            yield mock_instance

    @pytest.fixture
    def analyze_tables(self, mock_base_script):
        """Creates an instance of AnalyzeTables with mocked dependencies."""
        return AnalyzeTables()

    def test_init(self):
        """Tests the __init__ method of AnalyzeTables."""
        analyzer = AnalyzeTables()
        assert analyzer.name == "AnalyzeTables"
        assert analyzer.config_section == "analyze_tables"
        assert analyzer.requires_db is True

    def test_run_success(self, analyze_tables, mock_base_script):
        """Tests the run method with a successful database analysis."""
        mock_cursor = MagicMock()
        mock_base_script.db_conn.cursor.return_value.__enter__.return_value = (
            mock_cursor
        )
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = [10]
        mock_table_names = ["table1", "table2"]
        with patch(
            "dewey.core.db.analyze_tables.db_utils.get_table_names",
            return_value=mock_table_names,
        ):
            analyze_tables.run()

        mock_base_script.logger.info.assert_any_call("Starting table analysis...")
        mock_base_script.logger.info.assert_any_call(
            "Analyzing tables in database: test_db"
        )
        mock_base_script.logger.info.assert_any_call(
            f"Found tables: {mock_table_names}"
        )
        mock_base_script.logger.info.assert_any_call("Analyzing table: table1")
        mock_cursor.execute.assert_any_call("SELECT COUNT(*) FROM table1")
        mock_base_script.logger.info.assert_any_call("Analyzing table: table2")
        mock_cursor.execute.assert_any_call("SELECT COUNT(*) FROM table2")
        mock_base_script.logger.info.assert_any_call("Table analysis completed.")

    def test_run_db_error(self, analyze_tables, mock_base_script):
        """Tests the run method when a database error occurs."""
        mock_cursor = MagicMock()
        mock_base_script.db_conn.cursor.return_value.__enter__.return_value = (
            mock_cursor
        )
        mock_cursor.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            analyze_tables.run()

        mock_base_script.logger.error.assert_called_with(
            "Error during table analysis: Database error"
        )

    def test_run_no_tables(self, analyze_tables, mock_base_script):
        """Tests the run method when no tables are found."""
        mock_cursor = MagicMock()
        mock_base_script.db_conn.cursor.return_value.__enter__.return_value = (
            mock_cursor
        )
        with patch(
            "dewey.core.db.analyze_tables.db_utils.get_table_names", return_value=[]
        ):
            analyze_tables.run()

        mock_base_script.logger.info.assert_any_call("Starting table analysis...")
        mock_base_script.logger.info.assert_any_call(
            "Analyzing tables in database: test_db"
        )
        mock_base_script.logger.info.assert_any_call("Found tables: []")
        mock_base_script.logger.info.assert_any_call("Table analysis completed.")

    def test_execute(self, analyze_tables, mock_base_script):
        """Tests the execute method."""
        analyze_tables.run = MagicMock()
        analyze_tables.parse_args = MagicMock()
        analyze_tables._cleanup = MagicMock()
        analyze_tables.execute()

        analyze_tables.parse_args.assert_called_once()
        mock_base_script.logger.info.assert_any_call(
            "Starting execution of AnalyzeTables"
        )
        analyze_tables.run.assert_called_once()
        mock_base_script.logger.info.assert_any_call(
            "Completed execution of AnalyzeTables"
        )
        analyze_tables._cleanup.assert_called_once()

    def test_execute_keyboard_interrupt(self, analyze_tables, mock_base_script):
        """Tests the execute method when a KeyboardInterrupt occurs."""
        analyze_tables.run = MagicMock(side_effect=KeyboardInterrupt)
        analyze_tables.parse_args = MagicMock()
        analyze_tables._cleanup = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            analyze_tables.execute()

        assert exc_info.value.code == 1
        mock_base_script.logger.warning.assert_called_with("Script interrupted by user")
        analyze_tables._cleanup.assert_called_once()

    def test_execute_exception(self, analyze_tables, mock_base_script):
        """Tests the execute method when a general exception occurs."""
        analyze_tables.run = MagicMock(side_effect=Exception("Test exception"))
        analyze_tables.parse_args = MagicMock()
        analyze_tables._cleanup = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            analyze_tables.execute()

        assert exc_info.value.code == 1
        mock_base_script.logger.error.assert_called_with(
            "Error executing script: Test exception", exc_info=True
        )
        analyze_tables._cleanup.assert_called_once()

    def test_cleanup(self, analyze_tables, mock_base_script):
        """Tests the _cleanup method."""
        analyze_tables.db_conn = MagicMock()
        analyze_tables._cleanup()
        analyze_tables.db_conn.close.assert_called_once()
        mock_base_script.logger.debug.assert_called_with("Closing database connection")

    def test_cleanup_no_db_conn(self, analyze_tables):
        """Tests the _cleanup method when db_conn is None."""
        analyze_tables.db_conn = None
        analyze_tables._cleanup()

    def test_cleanup_db_conn_error(self, analyze_tables, mock_base_script):
        """Tests the _cleanup method when closing the database connection raises an exception."""
        analyze_tables.db_conn = MagicMock()
        analyze_tables.db_conn.close.side_effect = Exception("Close error")
        analyze_tables._cleanup()
        mock_base_script.logger.warning.assert_called_with(
            "Error closing database connection: Close error"
        )
