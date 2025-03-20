import logging
from unittest.mock import patch

import pytest

from dewey.core.tui import Tui
from dewey.core.base_script import BaseScript


class TestTui:
    """Unit tests for the Tui class."""

    @pytest.fixture
    def tui_instance(self) -> Tui:
        """Fixture to create a Tui instance."""
        return Tui()

    def test_inheritance(self, tui_instance: Tui) -> None:
        """Test that Tui inherits from BaseScript."""
        assert isinstance(tui_instance, BaseScript)

    def test_init(self, tui_instance: Tui) -> None:
        """Test the __init__ method."""
        assert tui_instance.config_section == 'tui'

    @patch("dewey.core.tui.Tui.get_config_value")
    @patch("dewey.core.tui.print")
    def test_run(self, mock_print, mock_get_config_value, tui_instance: Tui, caplog) -> None:
        """Test the run method."""
        mock_get_config_value.return_value = "test_value"
        with caplog.at_level(logging.INFO):
            tui_instance.run()
        assert "TUI module started." in caplog.text
        assert "Config value: test_value" in caplog.text
        mock_print.assert_called_with("Running TUI...")
