import logging
from unittest.mock import patch

import pytest

from dewey.core.data_upload.upload import Upload


class TestUpload:
    """Tests for the Upload class."""

    @pytest.fixture
    def upload_instance(self):
        """Fixture to create an instance of the Upload class."""
        return Upload()

    def test_init(self, upload_instance):
        """Test the __init__ method."""
        assert upload_instance.config_section == "upload"
        assert upload_instance.logger is not None
        assert isinstance(upload_instance.logger, logging.Logger)

    @patch("dewey.core.data_upload.upload.Upload.get_config_value")
    @patch("dewey.core.data_upload.upload.Upload.logger")
    def test_run_success(self, mock_logger, mock_get_config_value, upload_instance):
        """Test the run method with successful data upload."""
        mock_get_config_value.return_value = "test_url"
        upload_instance.run()

        mock_get_config_value.assert_called_once_with("upload_url", "default_url")
        mock_logger.info.assert_called()
        assert (
            "Data upload completed successfully"
            in mock_logger.info.call_args_list[-1][0][0]
        )

    @patch("dewey.core.data_upload.upload.Upload.get_config_value")
    @patch("dewey.core.data_upload.upload.Upload.logger")
    def test_run_exception(self, mock_logger, mock_get_config_value, upload_instance):
        """Test the run method when an exception occurs during data upload."""
        mock_get_config_value.side_effect = Exception("Upload failed")
        upload_instance.run()

        mock_get_config_value.assert_called_once_with("upload_url", "default_url")
        mock_logger.exception.assert_called_once()
        assert (
            "An error occurred during data upload"
            in mock_logger.exception.call_args[0][0]
        )

    @patch("dewey.core.data_upload.upload.Upload.parse_args")
    @patch("dewey.core.data_upload.upload.Upload.run")
    @patch("dewey.core.data_upload.upload.Upload.logger")
    def test_execute_success(
        self, mock_logger, mock_run, mock_parse_args, upload_instance
    ):
        """Test the execute method with successful script execution."""
        mock_parse_args.return_value = None
        upload_instance.execute()

        mock_parse_args.assert_called_once()
        mock_logger.info.assert_called()
        assert (
            f"Starting execution of {upload_instance.name}"
            in mock_logger.info.call_args_list[0][0][0]
        )
        mock_run.assert_called_once()
        assert (
            f"Completed execution of {upload_instance.name}"
            in mock_logger.info.call_args_list[-1][0][0]
        )

    @patch("dewey.core.data_upload.upload.Upload.parse_args")
    @patch("dewey.core.data_upload.upload.Upload.run")
    @patch("dewey.core.data_upload.upload.Upload.logger")
    def test_execute_keyboard_interrupt(
        self, mock_logger, mock_run, mock_parse_args, upload_instance
    ):
        """Test the execute method when a KeyboardInterrupt occurs."""
        mock_parse_args.return_value = None
        mock_run.side_effect = KeyboardInterrupt
        with pytest.raises(SystemExit) as exc_info:
            upload_instance.execute()

        assert exc_info.value.code == 1
        mock_logger.warning.assert_called_once_with("Script interrupted by user")

    @patch("dewey.core.data_upload.upload.Upload.parse_args")
    @patch("dewey.core.data_upload.upload.Upload.run")
    @patch("dewey.core.data_upload.upload.Upload.logger")
    def test_execute_exception(
        self, mock_logger, mock_run, mock_parse_args, upload_instance
    ):
        """Test the execute method when a generic exception occurs."""
        mock_parse_args.return_value = None
        mock_run.side_effect = Exception("Generic error")
        with pytest.raises(SystemExit) as exc_info:
            upload_instance.execute()

        assert exc_info.value.code == 1
        mock_logger.error.assert_called_once()
        assert "Error executing script" in mock_logger.error.call_args[0][0]
        assert "Generic error" in str(mock_logger.error.call_args[0][1])

    @patch("dewey.core.data_upload.upload.Upload.db_conn")
    @patch("dewey.core.data_upload.upload.Upload.logger")
    def test_cleanup_db_connection(self, mock_logger, mock_db_conn, upload_instance):
        """Test the _cleanup method when a database connection exists."""
        upload_instance.db_conn = mock_db_conn
        upload_instance._cleanup()

        mock_logger.debug.assert_called_once_with("Closing database connection")
        mock_db_conn.close.assert_called_once()

    @patch("dewey.core.data_upload.upload.Upload.db_conn")
    @patch("dewey.core.data_upload.upload.Upload.logger")
    def test_cleanup_no_db_connection(self, mock_logger, mock_db_conn, upload_instance):
        """Test the _cleanup method when no database connection exists."""
        upload_instance.db_conn = None
        upload_instance._cleanup()

        mock_logger.debug.assert_not_called()
        mock_db_conn.close.assert_not_called()

    @patch("dewey.core.data_upload.upload.Upload.db_conn")
    @patch("dewey.core.data_upload.upload.Upload.logger")
    def test_cleanup_db_connection_exception(
        self, mock_logger, mock_db_conn, upload_instance
    ):
        """Test the _cleanup method when closing the database connection raises an exception."""
        upload_instance.db_conn = mock_db_conn
        mock_db_conn.close.side_effect = Exception("Close failed")
        upload_instance._cleanup()

        mock_logger.debug.assert_called_once_with("Closing database connection")
        mock_db_conn.close.assert_called_once()
        mock_logger.warning.assert_called_once()
        assert (
            "Error closing database connection" in mock_logger.warning.call_args[0][0]
        )
        assert "Close failed" in str(mock_logger.warning.call_args[0][1])
