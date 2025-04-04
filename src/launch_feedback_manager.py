#!/usr/bin/env python3
"""
Launcher for the Dewey Feedback Manager.

This script provides a convenient way to launch the Feedback Manager TUI directly.
"""

import sys
from pathlib import Path

# Add project root to sys.path if needed
project_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_dir))

from src.ui.feedback_manager_tui import FeedbackManagerApp


def main():
    """Launch the Feedback Manager application."""
    print("Starting Dewey Feedback Manager...")

    # Create CSS file if it doesn't exist
    from src.ui.feedback_manager_tui import create_css_file

    css_path = Path(project_dir) / "src" / "ui" / "feedback_manager.tcss"
    if not css_path.exists():
        create_css_file()

    # Launch the app
    app = FeedbackManagerApp()
    app.run()


if __name__ == "__main__":
    main()
