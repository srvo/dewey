"""ECIC Terminal Application."""

import logging

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static

from .config import Config
from .services.ssh import ServerInfo
from .services.tick_processor import TickProcessor
from .widgets.server_menu import ServerMenu
from .widgets.terminal import TerminalWidget
from .widgets.tools_menu import ToolsMenu

logger = logging.getLogger(__name__)


class WarningBanner(Static):
    """A banner that displays warnings."""

    def __init__(self, warnings=None) -> None:
        """Initialize the warning banner."""
        super().__init__("")
        self.warnings = warnings or []
        self._update_content()

    def _update_content(self) -> None:
        """Update the warning banner content."""
        if self.warnings:
            warning_text = "\n".join(f"⚠️  {warning}" for warning in self.warnings)
            self.update(warning_text)
        else:
            self.update("")


class ECICApp(App):
    """Main ECIC Application.

    A modular terminal user interface for ethical investment management.
    """

    TITLE = "Ethical Capital Investment Collaborative"
    CSS_PATH = "styles/main.css"

    # Reactive state
    current_view = reactive("main")
    selected_ticker = reactive(None)

    # Key bindings
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("h", "toggle_help", "Help"),
        Binding("p", "show_portfolio", "Portfolio"),
        Binding("l", "show_lunar", "Lunar"),
        Binding("s", "show_status", "Status"),
        Binding("m", "toggle_server_menu", "Toggle Server Menu", show=True),
        Binding("t", "toggle_tools_menu", "Toggle Tools Menu", show=True),
        Binding("esc", "show_main", "Main"),
    ]

    def __init__(self, config: Config) -> None:
        """Initialize the application with configuration."""
        super().__init__()
        self.config = config
        self.server_menu = ServerMenu()
        self.tools_menu = ToolsMenu()
        self.warning_banner = WarningBanner(config.warnings)
        self.terminal = TerminalWidget()
        self.tick_processor = None
        self.async_session = None

    async def initialize_services(self) -> None:
        """Initialize core services."""
        try:
            if self.config.database_url:
                await self.initialize_database()

            # Initialize tick processor
            self.tick_processor = TickProcessor(tick_interval=self.config.tick_interval)
            self.tick_processor.start()

        except Exception as e:
            logger.exception(f"Error initializing services: {e!s}")
            self.warning_banner.warnings.append(f"Error initializing services: {e!s}")

    async def initialize_database(self) -> None:
        """Initialize the database connection."""
        try:
            # Create database engine and session
            engine = create_async_engine(self.config.database_url)
            async_session = sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            self.async_session = async_session

        except Exception as e:
            logger.exception(f"Database initialization error: {e!s}")
            raise

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield self.warning_banner

        with Container(), Horizontal():
            # Left sidebar with 32% width
            with Vertical(id="sidebar", classes="sidebar"):
                yield self.server_menu
                yield self.tools_menu

            # Main content area
            with Vertical(id="main-content"):
                yield self.terminal

        yield Footer()

    async def on_mount(self) -> None:
        """Handle application startup."""
        await self.initialize_services()
        try:
            # Write welcome message
            welcome_msg = """
[bold green]Welcome to ECIC Terminal[/]
[dim]Ethical Capital Investment Collaborative[/]

Use the following keyboard shortcuts:
• [bold]q[/] - Quit
• [bold]h[/] - Help
• [bold]p[/] - Portfolio view
• [bold]l[/] - Lunar phase view
• [bold]s[/] - Status view
• [bold]m[/] - Toggle server menu
• [bold]t[/] - Toggle tools menu
• [bold]esc[/] - Return to main view

[italic]Type a command or use the menus to get started...[/]
"""
            self.terminal.write(welcome_msg)

            logger.info("Application mounted successfully")
        except Exception as e:
            logger.exception(f"Error during application mount: {e!s}")
            self.warning_banner.warnings.append(
                f"Error during application mount: {e!s}",
            )

    async def on_unmount(self) -> None:
        """Clean up when app is closed."""
        try:
            # Stop tick processor
            if self.tick_processor:
                self.tick_processor.stop()

            logger.info("Application services stopped")

        except Exception as e:
            logger.exception(f"Error stopping services: {e!s}")
            self.warning_banner.warnings.append(f"Error stopping services: {e!s}")

    def action_show_main(self) -> None:
        """Show the main view."""
        self.current_view = "main"
        self.refresh()

    def action_show_portfolio(self) -> None:
        """Show the portfolio view."""
        self.current_view = "portfolio"
        self.refresh()

    def action_show_lunar(self) -> None:
        """Show the lunar view."""
        self.current_view = "lunar"
        self.refresh()

    def action_show_status(self) -> None:
        """Show the status view."""
        self.current_view = "status"
        self.refresh()

    def action_show_servers(self) -> None:
        """Show the servers view."""
        self.current_view = "servers"
        self.refresh()

    def action_toggle_help(self) -> None:
        """Toggle the help screen."""
        self.current_view = "help" if self.current_view != "help" else "main"
        self.refresh()

    def action_toggle_tools_menu(self) -> None:
        """Toggle the tools menu visibility."""
        self.tools_menu.visible = not self.tools_menu.visible

    async def on_server_menu_service_selected(
        self,
        message: ServerMenu.ServiceSelected,
    ) -> None:
        """Handle service selection from server menu."""
        self.status_widget.add_notification(
            f"Selected service {message.service['name']} on {message.server}",
            "info",
        )

    async def _add_test_servers(self) -> None:
        """Add test servers for development."""
        try:
            # Add some test servers (replace with your actual servers)
            servers = [
                ServerInfo(
                    name="production",
                    host="prod.example.com",
                    username="deploy",
                    key_path="~/.ssh/id_rsa",
                ),
                ServerInfo(
                    name="staging",
                    host="staging.example.com",
                    username="deploy",
                    key_path="~/.ssh/id_rsa",
                ),
            ]

            for server in servers:
                await self.server_menu.add_server(server)

        except Exception as e:
            logger.exception(f"Error adding test servers: {e!s}")
            self.warning_banner.warnings.append(f"Failed to add test servers: {e!s}")

    async def on_terminal_widget_command_entered(
        self,
        message: TerminalWidget.CommandEntered,
    ) -> None:
        """Handle commands entered in the terminal."""
        command = message.command

        # Handle built-in commands
        if command == "clear":
            self.terminal.action_clear()
        elif command == "help":
            self.terminal.write("\n[bold]Available Commands:[/]")
            self.terminal.write("\n• clear - Clear the terminal")
            self.terminal.write("\n• help - Show this help message")
            self.terminal.write("\n• exit/quit - Exit the application")
        elif command in ["exit", "quit"]:
            self.exit()
        else:
            self.terminal.write(
                "\n[red]Unknown command. Type 'help' for available commands.[/]",
            )
