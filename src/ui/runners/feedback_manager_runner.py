"""
Feedback Manager Runner

A standalone script to run the Feedback Manager screen for testing and development.
"""

import os
import sys

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from textual.app import App

from src.ui.screens.feedback_manager_screen import FeedbackManagerScreen


class FeedbackManagerApp(App):
    """Simple app to run the Feedback Manager screen."""

    CSS_PATH = os.path.join(
        os.path.dirname(__file__), "../assets/feedback_manager.tcss",
    )
    TITLE = "Dewey TUI — Feedback Manager & Port5 Research"

    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.push_screen(FeedbackManagerScreen())


def main():
    """Run the app."""
    app = FeedbackManagerApp()
    app.run()


if __name__ == "__main__":
    main()
