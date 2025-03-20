import logging
from unittest.mock import patch

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.sync.sheets import Sheets


class TestSheets:
    """Tests for the Sheets class."""

    @pytest.fixture
    def sheets_instance(self) -> Sheets:
        """Fixture to create an instance of the Sheets class."""
        return Sheets()

    def test_sheets_initialization(self, sheets_instance: Sheets) -> None:
        """Test that the Sheets class initializes correctly."""
        assert isinstance(sheets_instance, BaseScript)
        assert sheets_instance.config_section == "sheets"

    @patch("dewey.core.sync.sheets.Sheets.get_config_value")
    @patch("dewey.core.sync.sheets.Sheets.logger")
    def test_run_method(
        self,
        mock_logger: logging.Logger,
        mock_get_config_value: Sheets,
        sheets_instance: Sheets,
    ) -> None:
        """Test the run method of the Sheets class."""
        mock_get_config_value.return_value = "test_sheet_id"

        sheets_instance.run()

        mock_logger.info.assert_called()
        assert mock_logger.info.call_count == 3
        mock_get_config_value.assert_called_once_with("sheet_id")

    @patch("dewey.core.sync.sheets.Sheets.get_config_value")
    @patch("dewey.core.sync.sheets.Sheets.logger")
    def test_run_method_no_sheet_id(
        self,
        mock_logger: logging.Logger,
        mock_get_config_value: Sheets,
        sheets_instance: Sheets,
    ) -> None:
        """Test the run method when sheet_id is not configured."""
        mock_get_config_value.return_value = None

        sheets_instance.run()

        mock_logger.info.assert_called()
        assert mock_logger.info.call_count == 3
        mock_get_config_value.assert_called_once_with("sheet_id")

    def test_get_config_value(self, sheets_instance: Sheets) -> None:
        """Test the get_config_value method."""
        # Mock the config attribute
        sheets_instance.config = {"test_key": "test_value"}
        value = sheets_instance.get_config_value("test_key")
        assert value == "test_value"

        # Test with a default value
        value = sheets_instance.get_config_value("non_existent_key", "default_value")
        assert value == "default_value"

        # Test with nested keys
        sheets_instance.config = {"nested": {"test_key": "nested_value"}}
        value = sheets_instance.get_config_value("nested.test_key")
        assert value == "nested_value"

        # Test with a non-existent nested key and a default value
        value = sheets_instance.get_config_value(
            "nested.non_existent_key", "default_value"
        )
        assert value == "default_value"

        # Test with a non-existent nested key and no default value
        value = sheets_instance.get_config_value("nested.non_existent_key")
        assert value is None
