import logging
from unittest.mock import patch

import pytest

from dewey.core.db.errors import DatabaseErrorHandler


class TestDatabaseErrorHandler:
    """Tests for the DatabaseErrorHandler class."""

    @pytest.fixture
    def error_handler(self) -> DatabaseErrorHandler:
        """Fixture to create a DatabaseErrorHandler instance."""
        return DatabaseErrorHandler()

    def test_init(self, error_handler: DatabaseErrorHandler) -> None:
        """Test that the DatabaseErrorHandler is initialized correctly."""
        assert error_handler.config_section == 'database_error_handler'
        assert error_handler.logger is not None

    @patch.object(logging.Logger, 'error')
    def test_run_error_logged(self, mock_error: logging.Logger, error_handler: DatabaseErrorHandler) -> None:
        """Test that the run method logs an error."""
        error_handler.run()
        mock_error.assert_called_once()
        assert "Simulated database error" in str(mock_error.call_args)

    @patch.object(DatabaseErrorHandler, 'handle_error')
    def test_run_handle_error_called(self, mock_handle_error: DatabaseErrorHandler, error_handler: DatabaseErrorHandler) -> None:
        """Test that the run method calls handle_error."""
        error_handler.run()
        mock_handle_error.assert_called_once()
        assert "Simulated database error" in str(mock_handle_error.call_args)

    @patch.object(logging.Logger, 'info')
    def test_handle_error_log(self, mock_info: logging.Logger, error_handler: DatabaseErrorHandler) -> None:
        """Test that handle_error logs the message when error_handling_method is 'log'."""
        error_message = "Test error message"
        error_handler.handle_error(error_message)
        mock_info.assert_called_once()
        assert error_message in str(mock_info.call_args)

    @patch.object(logging.Logger, 'info')
    def test_handle_error_retry(self, mock_info: logging.Logger, error_handler: DatabaseErrorHandler) -> None:
        """Test that handle_error logs the message when error_handling_method is 'retry'."""
        error_message = "Test error message"
        with patch.object(error_handler, 'get_config_value', return_value='retry'):
            error_handler.handle_error(error_message)
        mock_info.assert_called_once()
        assert error_message in str(mock_info.call_args)

    @patch.object(logging.Logger, 'warning')
    def test_handle_error_unknown(self, mock_warning: logging.Logger, error_handler: DatabaseErrorHandler) -> None:
        """Test that handle_error logs a warning when error_handling_method is unknown."""
        error_message = "Test error message"
        with patch.object(error_handler, 'get_config_value', return_value='unknown'):
            error_handler.handle_error(error_message)
        mock_warning.assert_called_once()
        assert "Unknown error handling method" in str(mock_warning.call_args)

    @patch.object(logging.Logger, 'info')
    def test_handle_error_config_default(self, mock_info: logging.Logger, error_handler: DatabaseErrorHandler) -> None:
        """Test that handle_error uses the default error_handling_method when not in config."""
        error_message = "Test error message"
        with patch.object(error_handler, 'get_config_value', return_value=None):
            error_handler.handle_error(error_message)
        mock_info.assert_called_once()
        assert error_message in str(mock_info.call_args)

    def test_get_config_value_existing_key(self, error_handler: DatabaseErrorHandler) -> None:
        """Test that get_config_value returns the correct value for an existing key."""
        error_handler.config = {'test_key': 'test_value'}
        assert error_handler.get_config_value('test_key') == 'test_value'

    def test_get_config_value_nested_key(self, error_handler: DatabaseErrorHandler) -> None:
        """Test that get_config_value returns the correct value for a nested key."""
        error_handler.config = {'nested': {'test_key': 'test_value'}}
        assert error_handler.get_config_value('nested.test_key') == 'test_value'

    def test_get_config_value_missing_key(self, error_handler: DatabaseErrorHandler) -> None:
        """Test that get_config_value returns the default value for a missing key."""
        error_handler.config = {}
        assert error_handler.get_config_value('missing_key', 'default_value') == 'default_value'

    def test_get_config_value_missing_nested_key(self, error_handler: DatabaseErrorHandler) -> None:
        """Test that get_config_value returns the default value for a missing nested key."""
        error_handler.config = {'nested': {}}
        assert error_handler.get_config_value('nested.missing_key', 'default_value') == 'default_value'

    def test_get_config_value_invalid_key(self, error_handler: DatabaseErrorHandler) -> None:
        """Test that get_config_value returns the default value when a part of the key is not a dictionary."""
        error_handler.config = {'test_key': 'test_value'}
        assert error_handler.get_config_value('test_key.invalid_key', 'default_value') == 'default_value'
