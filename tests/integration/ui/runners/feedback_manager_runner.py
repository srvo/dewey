#!/usr/bin/env python

"""Feedback Manager Runner for Production Testing.

This runner initializes and runs the Feedback Manager screen as a standalone app.
"""

import logging
import os
import sys

# Add the project root to sys.path to ensure imports work correctly
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)

# Configure logging to show detailed debug information
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("feedback_manager_runner")

from textual.app import App

from src.ui.screens.feedback_manager_screen import FeedbackManagerScreen


class FeedbackManagerApp(App):
    """A simple app to run the Feedback Manager screen."""

    CSS_PATH = None
    SCREENS = {"feedback_manager": FeedbackManagerScreen}

    def on_mount(self) -> None:
        """Push the feedback manager screen when the app starts."""
        logger.debug("FeedbackManagerApp mounted")
        self.push_screen("feedback_manager")


def main():
    """Run the app."""
    logger.info("Starting Feedback Manager application")

    # Check for development mode flags
    dev_mode = "--dev" in sys.argv
    debug_mode = "--debug" in sys.argv or dev_mode

    if debug_mode:
        logger.info("Running in debug mode - extra logging enabled")

    try:
        # Initialize the app
        app = FeedbackManagerApp()

        # Always run with logging for better diagnostics
        logger.info("Starting the Feedback Manager app with debug logging")
        app.run()

    except Exception as e:
        logger.error(f"Error running Feedback Manager: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()