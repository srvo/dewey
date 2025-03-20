import logging
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.research.output_handler import OutputHandler


class TestOutputHandler:
    """Unit tests for the OutputHandler class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture to mock BaseScript methods."""
        mock = MagicMock()
        mock.get_config_value.return_value = "test_output_path"
        mock.logger = MagicMock()
        return mock

    @pytest.fixture
    def output_handler(self, mock_base_script: MagicMock) -> OutputHandler:
        """Fixture to create an OutputHandler instance with mocked dependencies."""
        with patch(
            "dewey.core.research.output_handler.BaseScript.__init__",
            new=lambda self, config_section, **kwargs: None,
        ):
            handler = OutputHandler(config_path="test_config_path")
            handler.get_config_value = mock_base_script.get_config_value
            handler.logger = mock_base_script.logger
            return handler

    def test_init(self) -> None:
        """Test the initialization of the OutputHandler."""
        with patch("dewey.core.research.output_handler.BaseScript.__init__") as mock_init:
            OutputHandler(config_path="test_config_path")
            mock_init.assert_called_once_with(config_section="output_handler")

    def test_run_success(self, output_handler: OutputHandler, mock_base_script: MagicMock) -> None:
        """Test the successful execution of the run method."""
        output_handler.write_output = MagicMock()
        output_handler.run()

        mock_base_script.get_config_value.assert_called_once_with("output_path")
        output_handler.write_output.assert_called_once_with(
            "test_output_path", {"status": "success", "message": "Data processed successfully."}
        )
        output_handler.logger.info.assert_called_once()
        output_handler.logger.debug.assert_called_once()

    def test_run_missing_output_path(self, output_handler: OutputHandler, mock_base_script: MagicMock) -> None:
        """Test the run method when the output path is missing in the config."""
        mock_base_script.get_config_value.return_value = None
        output_handler.run()

        mock_base_script.get_config_value.assert_called_once_with("output_path")
        output_handler.logger.error.assert_called_once()

    def test_run_exception(self, output_handler: OutputHandler, mock_base_script: MagicMock) -> None:
        """Test the run method when an unexpected exception occurs."""
        mock_base_script.get_config_value.side_effect = Exception("Test exception")
        output_handler.run()

        mock_base_script.get_config_value.assert_called_once_with("output_path")
        output_handler.logger.exception.assert_called_once()

    def test_write_output_success(self, output_handler: OutputHandler) -> None:
        """Test the successful execution of the write_output method."""
        output_path = "test_output_path"
        data = {"test": "data"}
        output_handler.write_output(output_path, data)

        output_handler.logger.info.assert_called_once_with(f"Writing output to: {output_path}")
        output_handler.logger.debug.assert_called_once_with(f"Output data: {data}")

    def test_write_output_exception(self, output_handler: OutputHandler) -> None:
        """Test the write_output method when an exception occurs."""
        output_path = "test_output_path"
        data = {"test": "data"}
        output_handler.logger.info.side_effect = Exception("Test exception")
        output_handler.write_output(output_path, data)

        output_handler.logger.error.assert_called_once()
