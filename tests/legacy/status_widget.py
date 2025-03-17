
# Refactored from: status_widget
# Date: 2025-03-16T16:19:10.416659
# Refactor Version: 1.0
"""Status and notification widget."""

from datetime import datetime

from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Log, Static

from .base import BaseWidget


class StatusWidget(BaseWidget):
    """Widget for displaying system status and notifications."""

    BINDINGS = [
        Binding("c", "clear_notifications", "Clear"),
    ]

    def __init__(self) -> None:
        """Initialize the status widget."""
        super().__init__()
        self.notifications: list[dict] = []
        self.log = Log()
        self.status = Static()

    def compose_content(self) -> None:
        """Compose the status widget content."""
        try:
            # Update system status
            self._update_status()

            # Format notifications
            self._format_notifications()

            # Update the widget
            self.update(
                Vertical(
                    self.status,
                    Static(""),  # Spacer
                    self.log,
                ),
            )

        except Exception as e:
            self.handle_error(f"Error updating status: {e!s}")

    def _update_status(self) -> None:
        """Update system status information."""
        try:
            # TODO: Implement real status checks
            # For now, using mock data
            status_text = f"""[bold green]System Status: Online[/]
[bold]Last Update:[/] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
[bold]Database:[/] Connected
[bold]Services:[/]
  • Market Data: Active
  • ESG Analysis: Active
  • Lunar Phase: Active
"""
            self.status.update(status_text)

        except Exception:
            self.status.update("[bold red]Error: Unable to fetch system status[/]")
            raise

    def _format_notifications(self) -> str:
        """Format notifications for display."""
        if not self.notifications:
            return "[italic]No notifications[/]"

        return "\n".join(
            f"[{n['timestamp'].strftime('%H:%M:%S')}] {n['message']}"
            for n in self.notifications
        )

    def add_notification(self, message: str, level: str = "info") -> None:
        """Add a new notification."""
        timestamp = datetime.now()

        # Add to notifications list
        self.notifications.append(
            {
                "timestamp": timestamp,
                "message": message,
                "level": level,
            },
        )

        # Add to log with appropriate styling
        if level == "error":
            self.log.write(f"[red]{timestamp:%H:%M:%S} ERROR: {message}[/]")
        elif level == "warning":
            self.log.write(f"[yellow]{timestamp:%H:%M:%S} WARNING: {message}[/]")
        else:
            self.log.write(f"[green]{timestamp:%H:%M:%S} INFO: {message}[/]")

        # Refresh the widget
        self.refresh_content()

    def action_clear_notifications(self) -> None:
        """Clear all notifications."""
        self.notifications.clear()
        self.log.clear()
        self.refresh_content()

    def on_mount(self) -> None:
        """Handle widget mounting."""
        super().on_mount()
        self.add_notification("Status widget initialized", "info")
