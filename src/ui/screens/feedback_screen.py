"""
Feedback Manager Screen

A screen for the Dewey UI that provides access to the Feedback Manager.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Static

from ..feedback_manager_tui import FeedbackManagerApp


class FeedbackScreen(Screen):
    """A screen for the Feedback Manager in the Dewey UI system."""

    def compose(self) -> ComposeResult:
        """Compose the screen."""
        yield Static("Feedback Manager", id="screen-title")
        yield Static(
            "Manage feedback, flag follow-ups, and annotate contacts",
            id="screen-description",
        )
        yield Button("Launch Feedback Manager", id="launch-button", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "launch-button":
            self.launch_feedback_manager()

    def launch_feedback_manager(self) -> None:
        """Launch the feedback manager application."""
        # First remove this screen
        self.app.pop_screen()

        # Launch the feedback manager app
        feedback_app = FeedbackManagerApp()
        feedback_app.run()
