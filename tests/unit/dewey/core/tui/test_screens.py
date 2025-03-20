import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.tui.screens import ScreenManager


class TestScreenManager:
    """Tests for the ScreenManager class."""

    @pytest.fixture
    def screen_manager(self) -> ScreenManager:
        """Fixture for creating a ScreenManager instance."""
        return ScreenManager()

    def test_init(self, screen_manager: ScreenManager) -> None:
        """Tests the __init__ method."""
        assert screen_manager.name == "ScreenManager"
        assert screen_manager.config_section == "screen_manager"
        assert isinstance(screen_manager.logger, logging.Logger)

    @patch("dewey.core.tui.screens.ScreenManager.get_config_value")
    @patch("builtins.print")
    def test_run(
        self, mock_print: MagicMock, mock_get_config_value: MagicMock, screen_manager: ScreenManager
    ) -> None:
        """Tests the run method."""
        mock_get_config_value.return_value = "TestScreen"
        screen_manager.run()
        mock_get_config_value.assert_called_once_with("default_screen", "MainScreen")
        mock_print.assert_called_once_with("Placeholder for screen display logic.")

    @patch("builtins.print")
    def test_display_screen(self, mock_print: MagicMock, screen_manager: ScreenManager) -> None:
        """Tests the display_screen method."""
        screen_name = "TestScreen"
        screen_manager.display_screen(screen_name)
        mock_print.assert_called_once_with(f"Displaying screen: {screen_name}")

    @patch("dewey.core.tui.screens.ScreenManager.get_config_value")
    @patch("builtins.print")
    def test_run_config_error(
        self, mock_print: MagicMock, mock_get_config_value: MagicMock, screen_manager: ScreenManager
    ) -> None:
        """Tests the run method when there's an error accessing config."""
        mock_get_config_value.side_effect = Exception("Config error")
        with pytest.raises(Exception, match="Config error"):
            screen_manager.run()

    @patch("dewey.core.tui.screens.ScreenManager.get_config_value")
    @patch("builtins.print")
    def test_run_no_default_screen(
        self, mock_print: MagicMock, mock_get_config_value: MagicMock, screen_manager: ScreenManager
    ) -> None:
        """Tests the run method when default_screen is not in config."""
        mock_get_config_value.return_value = None
        screen_manager.run()
        mock_get_config_value.assert_called_once_with("default_screen", "MainScreen")
        mock_print.assert_called_once_with("Placeholder for screen display logic.")

    def test_display_screen_empty_name(self, screen_manager: ScreenManager) -> None:
        """Tests the display_screen method with an empty screen name."""
        with patch("builtins.print") as mock_print:
            screen_manager.display_screen("")
            mock_print.assert_called_once_with("Displaying screen: ")

    def test_display_screen_none_name(self, screen_manager: ScreenManager) -> None:
        """Tests the display_screen method with a None screen name."""
        with patch("builtins.print") as mock_print:
            screen_manager.display_screen(None)  # type: ignore
            mock_print.assert_called_once_with("Displaying screen: None")
