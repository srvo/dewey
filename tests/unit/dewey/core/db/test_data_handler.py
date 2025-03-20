from unittest.mock import MagicMock, patch

import pytest

from dewey.core.db.data_handler import DataHandler


class TestDataHandler:
    """Tests for the DataHandler class."""

    @pytest.fixture
    def mock_base_script(self):
        """Mocks the BaseScript class."""
        with patch("dewey.core.db.data_handler.BaseScript.__init__") as mock:
            yield mock

    @pytest.fixture
    def data_handler(self, mock_base_script):
        """Fixture for creating a DataHandler instance."""
        mock_base_script.return_value = None
        return DataHandler("TestHandler")

    def test_init_valid_name(self, mock_base_script):
        """Test that DataHandler initializes correctly with a valid name."""
        mock_base_script.return_value = None
        handler = DataHandler("ValidName")
        assert handler.name == "ValidName"
        assert handler.logger is not None
        mock_base_script.assert_called_once_with(config_section="db")

    def test_init_invalid_name(self, mock_base_script):
        """Test that DataHandler raises TypeError when name is not a string."""
        mock_base_script.return_value = None
        with pytest.raises(TypeError, match="Name must be a string."):
            DataHandler(123)

    def test_repr(self, data_handler):
        """Test that DataHandler's __repr__ method returns the correct string."""
        expected_repr = "DataHandler(name='TestHandler')"
        assert repr(data_handler) == expected_repr

    def test_run_method(self, data_handler, caplog):
        """Test the run method of DataHandler, including logging and error handling."""
        data_handler.get_config_value = MagicMock(
            return_value={"connection_string": "test_db"}
        )
        with patch("dewey.core.db.data_handler.get_connection") as mock_get_connection:
            mock_conn = MagicMock()
            mock_get_connection.return_value.__enter__.return_value = mock_conn
            data_handler.run()
            assert "Running DataHandler script..." in caplog.text
            assert "DataHandler script completed." in caplog.text

    def test_run_method_db_config_not_found(self, data_handler, caplog):
        """Test run method when database configuration is not found."""
        data_handler.get_config_value = MagicMock(return_value=None)
        data_handler.run()
        assert "Database configuration not found." in caplog.text

    def test_run_method_db_operation_error(self, data_handler, caplog):
        """Test run method when a database operation raises an exception."""
        data_handler.get_config_value = MagicMock(
            return_value={"connection_string": "test_db"}
        )
        with patch("dewey.core.db.data_handler.get_connection") as mock_get_connection:
            mock_get_connection.side_effect = Exception("Database error")
            data_handler.run()
            assert "Error during database operation: Database error" in caplog.text
