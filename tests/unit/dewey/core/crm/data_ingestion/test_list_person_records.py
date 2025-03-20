import logging
from unittest.mock import MagicMock

import pytest

from dewey.core.crm.data_ingestion.list_person_records import ListPersonRecords


class TestListPersonRecords:
    """Unit tests for the ListPersonRecords class."""

    @pytest.fixture
    def list_person_records(self) -> ListPersonRecords:
        """Fixture to create an instance of ListPersonRecords."""
        return ListPersonRecords()

    def test_init(self, list_person_records: ListPersonRecords) -> None:
        """Test the __init__ method."""
        assert list_person_records.config_section == "crm"
        assert list_person_records.requires_db is True
        assert list_person_records.db_conn is None  # Connection is lazy-loaded

    def test_run_success(self, list_person_records: ListPersonRecords, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method with a successful database query."""
        # Mock the database connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("John Doe", ), ("Jane Smith", )]
        mock_db_conn = MagicMock()
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor
        list_person_records.db_conn = mock_db_conn

        # Capture log messages
        caplog.set_level(logging.INFO)

        # Run the script
        list_person_records.run()

        # Assertions
        mock_db_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT * FROM persons;")
        assert "Starting to list person records..." in caplog.text
        assert "Record: ('John Doe', )" in caplog.text
        assert "Record: ('Jane Smith', )" in caplog.text
        assert "Finished listing person records." in caplog.text

    def test_run_empty_records(self, list_person_records: ListPersonRecords, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method when the database query returns no records."""
        # Mock the database connection and cursor
        mock_cursor=None, list_person_records: ListPersonRecords, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method when an exception occurs during the database query."""
        # Mock the database connection and cursor to raise an exception
        mock_db_conn = MagicMock()
        mock_db_conn.cursor.side_effect = Exception("Database error")
        list_person_records.db_conn = mock_db_conn

        # Capture log messages
        caplog.set_level(logging.ERROR)

        # Run the script and assert that it raises an exception
        with pytest.raises(Exception, match="Database error"):
            if caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method when the database query returns no records."""
        # Mock the database connection and cursor
        mock_cursor is None:
                caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method when the database query returns no records."""
        # Mock the database connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_db_conn = MagicMock()
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor
        list_person_records.db_conn = mock_db_conn

        # Capture log messages
        caplog.set_level(logging.INFO)

        # Run the script
        list_person_records.run()

        # Assertions
        mock_db_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT * FROM persons;")
        assert "Starting to list person records..." in caplog.text
        assert "Finished listing person records." in caplog.text
        assert "Record:" not in caplog.text  # Ensure no records are logged

    def test_run_exception(self
            list_person_records.run()

        # Assertions
        assert "Starting to list person records..." in caplog.text
        assert "Error listing person records: Database error" in caplog.text

    def test_run_no_db_connection(self, list_person_records: ListPersonRecords, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method when the database connection is not initialized."""
        list_person_records.db_conn = None

        # Capture log messages
        caplog.set_level(logging.ERROR)

        # Mock the database connection and cursor to raise an exception
        mock_db_conn = MagicMock()
        mock_db_conn.cursor.side_effect = Exception("Database error")
        list_person_records.db_conn = mock_db_conn

        # Run the script and assert that it raises an exception
        with pytest.raises(Exception, match="Database error"):
            list_person_records.run()

        # Assertions
        assert "Starting to list person records..." in caplog.text
        assert "Error listing person records: Database error" in caplog.text
