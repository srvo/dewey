"""
User Interface module for the Dewey project.

This module provides terminal and graphical user interfaces for interacting with Dewey.
"""

from dewey.core.base_script import BaseScript

from ui.app import TUIApp
from ui.screens import ScreenManager
from ui.workers import Workers

__all__ = ["ScreenManager", "TUIApp", "Tui", "Workers"]


class Tui(BaseScript):
    """
    A base class for TUI modules within the Dewey framework.

    This class inherits from BaseScript and provides a standardized
    interface for interacting with the terminal user interface.
    """

    def __init__(self) -> None:
        """Initializes the Tui module."""
        super().__init__(config_section="tui")

    def execute(self) -> None:
        """Executes the main logic of the TUI module."""
        self.logger.info("TUI module started.")
        # Add TUI logic here
        config_value = self.get_config_value("some_config_key", "default_value")
        self.logger.debug(f"Config value: {config_value}")
        print("Running TUI...")

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()
