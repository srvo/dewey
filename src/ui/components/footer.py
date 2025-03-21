"""
Footer component for the TUI application.
"""

from textual.widgets import Static
from textual.app import ComposeResult
from rich.text import Text


class Footer(Static):
    """A footer component for the TUI application."""
    
    def __init__(self, status: str = "Ready") -> None:
        """Initialize the footer with a status.
        
        Args:
            status: The status to display in the footer
        """
        self.status = status
        super().__init__("")
        
    def compose(self) -> ComposeResult:
        """Compose the footer content."""
        yield Static(self.status, classes="footer-status")
        
    def on_mount(self) -> None:
        """Called when the footer is mounted."""
        status_text = Text(self.status, style="white on dark_blue")
        self.update(status_text)
        
    def update_status(self, new_status: str) -> None:
        """Update the footer status.
        
        Args:
            new_status: The new status to display
        """
        self.status = new_status
        status_text = Text(self.status, style="white on dark_blue")
        self.update(status_text) 