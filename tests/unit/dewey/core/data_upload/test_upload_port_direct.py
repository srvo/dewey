import logging
from unittest.mock import patch

import pytest

from dewey.core.data_upload.upload_port_direct import UploadPortDirect


class TestUploadPortDirect:
    """Unit tests for the UploadPortDirect class."""

    @pytest.fixture
    def upload_port_direct(self):
        """Fixture to create an instance of UploadPortDirect."""
        return UploadPortDirect()

    def test_init(self, upload_port_direct: UploadPortDirect):
        """Test the initialization of the UploadPortDirect class."""
        assert upload_port_direct.config_section == "upload_port_direct"
        assert upload_port_direct.logger is not None
        assert isinstance(upload_port_direct.logger, logging.Logger)

    @patch("dewey.core.data_upload.upload_port_direct.UploadPortDirect.get_config_value")
    def test_run_success(self, mock_get_config_value, upload_port_direct: UploadPortDirect, caplog):
        """Test the run method with a successful data upload."""
        mock_get_config_value.return_value = "test_port"
        with caplog.at_level(logging.INFO):
            upload_port_direct.run()
        assert "Starting data upload to port: test_port" in caplog.text
        assert "Data upload process completed." in caplog.text
        mock_get_config_value.assert_called_once_with("port_name", "default_port")

    @patch("dewey.core.data_upload.upload_port_direct.UploadPortDirect.get_config_value")
    def test_run_exception(self, mock_get_config_value, upload_port_direct: UploadPortDirect, caplog):
        """Test the run method when an exception occurs during data upload."""
        mock_get_config_value.side_effect = Exception("Test exception")
        with caplog.at_level(logging.ERROR):
            upload_port_direct.run()
        assert "An error occurred during data upload: Test exception" in caplog.text
        assert "Traceback" in caplog.text
        mock_get_config_value.assert_called_once_with("port_name", "default_port")
