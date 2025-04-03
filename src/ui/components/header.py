"""Header component for the TUI application."""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static


class Header(Static):
    """A header component for the TUI application."""

    def __init__(self, title: str = "Dewey") -> None:
        """Initialize the header with a title.

        Args:
            title: The title to display in the header

        """
        self.title = title
        super().__init__("")

    def compose(self) -> ComposeResult:
        """Compose the header content."""
        yield Static(self.title, classes="header-title")

    def on_mount(self) -> None:
        """Called when the header is mounted."""
        title_text = Text(self.title, style="bold white on blue")
        self.update(title_text)

    def update_title(self, new_title: str) -> None:
        """Update the header title.

        Args:
            new_title: The new title to display

        """
        self.title = new_title
        title_text = Text(self.title, style="bold white on blue")
        self.update(title_text)
