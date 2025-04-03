#!/usr/bin/env python3
"""Run TUI

A standalone script to run the Dewey TUI with the new screens.
"""

import os
import sys

from textual.app import App
from textual.binding import Binding

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import screens
from src.ui.screens.feedback_manager_screen import FeedbackManagerScreen
from src.ui.screens.port5_screen import Port5Screen


class SimpleDeweyTUI(App):
    """Simple Dewey TUI Application."""

    TITLE = "Dewey TUI"
    SUB_TITLE = "Feedback Manager & Port5 Research"

    CSS_PATH = ["assets/feedback_manager.tcss", "assets/port5.tcss"]

    SCREENS = {
        "feedback": FeedbackManagerScreen,
        "port5": Port5Screen,
    }

    BINDINGS = [
        Binding("f", "switch_screen('feedback')", "Feedback Manager"),
        Binding("p", "switch_screen('port5')", "Port5 Research"),
        Binding("q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        """Handle app mount event."""
        # Start with the feedback manager screen
        self.push_screen("feedback")

    def action_switch_screen(self, screen_name: str) -> None:
        """Switch to the specified screen.

        Args:
            screen_name: The name of the screen to switch to

        """
        self.switch_screen(screen_name)


if __name__ == "__main__":
    app = SimpleDeweyTUI()
    app.run()
