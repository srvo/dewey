"""Server menu widget for displaying and managing remote servers."""

from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.message import Message
from textual.widgets import Static

from ..services.ssh import ServerInfo, SSHService
from .base import BaseWidget

if TYPE_CHECKING:
    from textual.widgets.tree import Tree


class ServerMenu(BaseWidget):
    """A widget for displaying and managing remote servers."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("c", "connect", "Connect"),
        Binding("d", "disconnect", "Disconnect"),
    ]

    class ServiceSelected(Message):
        """Message sent when a service is selected."""

        def __init__(self, server: str, service: dict[str, Any]) -> None:
            """Initializes the ServiceSelected message.

            Args:
                server: The name of the server.
                service: The service data.

            """
            self.server = server
            self.service = service
            super().__init__()

    def __init__(self) -> None:
        """Initializes the server menu."""
        super().__init__()
        self.ssh = SSHService()
        self._tree: Tree | None = None
        self._selected_server: str | None = None

    def compose(self) -> ComposeResult:
        """Composes the server menu."""
        with Container():
            yield Static("[bold]Server Status[/]", classes="menu-header")
            yield Static(
                "[dim]Server monitoring is simplified in this version.[/]",
                classes="menu-info",
            )
            yield Static(
                "[dim]Future versions will include detailed server management.[/]",
                classes="menu-info",
            )

    async def add_server(self, server: ServerInfo) -> None:
        """Adds a server to the menu.

        Args:
            server: The server information.

        """
        try:
            await self.ssh.add_server(server)
        except Exception as e:
            self.handle_error(f"Error adding server: {e!s}")

    async def refresh_server(self, server_name: str) -> None:
        """Refreshes services for a specific server.

        Args:
            server_name: The name of the server.

        """
        try:
            await self.ssh.get_services(server_name)
        except Exception as e:
            self.handle_error(f"Error refreshing server {server_name}: {e!s}")

    async def action_refresh(self) -> None:
        """Refreshes server information."""
        try:
            await self.ssh.refresh_services()
        except Exception as e:
            self.handle_error(f"Error refreshing services: {e!s}")

    async def action_connect(self) -> None:
        """Connects to the selected server."""
        try:
            if self._selected_server:
                await self.ssh.connect(self._selected_server)
            else:
                self.handle_error("No server selected")
        except Exception as e:
            self.handle_error(f"Error connecting to server: {e!s}")

    async def action_disconnect(self) -> None:
        """Disconnects from the selected server."""
        try:
            if self._selected_server:
                await self.ssh.disconnect(self._selected_server)
            else:
                self.handle_error("No server selected")
        except Exception as e:
            self.handle_error(f"Error disconnecting from server: {e!s}")

    async def on_unmount(self) -> None:
        """Handles widget unmounting."""
        await self.ssh.disconnect_all()
