from dewey.core.base_script import BaseScript

"""Textual UI implementation for the service manager."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    TextArea,
)

# Import screens
from .screens.feedback_screen import FeedbackScreen


class ServiceItem(BaseScript, BaseScriptListItem):
    """A list item representing a service."""

    def __init__(self, service_name: str, status: str) -> None:
        """Initialize service item.

        Args:
        ----
            service_name: Name of the service
            status: Current status of the service

        """
        super().__init__()
        self.service_name = service_name
        self.status = status

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        status_color = "green" if self.status == "running" else "red"
        with Horizontal():
            yield Label(self.service_name)
            yield Label(f"[{status_color}]{self.status}[/]", classes="status")


class ServiceList(BaseScriptListView):
    """A list view of services."""

    def __init__(self, services: list[dict[str, str]]) -> None:
        """Initialize service list.

        Args:
        ----
            services: List of services with their status

        """
        super().__init__()
        self.services = services

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        for service in self.services:
            yield ServiceItem(service["name"], service["status"])


class ServiceControlScreen(BaseScriptScreen):
    """Service control screen."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back", show=True),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, service_manager) -> None:
        """Initialize service control screen.

        Args:
        ----
            service_manager: Service manager instance

        """
        super().__init__()
        self.service_manager = service_manager

    def compose(self) -> ComposeResult:
        """Compose the screen."""
        yield Header()
        with Container(), Vertical():
            yield Label("Services", classes="title")
            services = [
                {"name": s.name, "status": "running" if s.containers else "stopped"}
                for s in self.service_manager.get_services()
            ]
            yield ServiceList(services)
            with Horizontal():
                yield Button("Start", variant="success", id="start")
                yield Button("Stop", variant="error", id="stop")
                yield Button("Restart", variant="warning", id="restart")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        selected = self.query_one(ServiceList).highlighted
        if selected is None:
            self.notify("Please select a service first", severity="error")
            return

        service_item = selected.query_one(ServiceItem)
        action = event.button.id
        if self.service_manager.control_service(service_item.service_name, action):
            self.notify(f"Service {action}ed successfully", severity="information")
        else:
            self.notify(f"Failed to {action} service", severity="error")

    def action_refresh(self) -> None:
        """Refresh service list."""
        services = [
            {"name": s.name, "status": "running" if s.containers else "stopped"}
            for s in self.service_manager.get_services()
        ]
        self.query_one(ServiceList).services = services
        self.refresh()


class IssueScreen(BaseScriptScreen):
    """GitHub issue creation screen."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back", show=True),
        Binding("ctrl+s", "submit", "Submit"),
    ]

    def __init__(self, service_manager) -> None:
        """Initialize issue screen.

        Args:
        ----
            service_manager: Service manager instance

        """
        super().__init__()
        self.service_manager = service_manager

    def compose(self) -> ComposeResult:
        """Compose the screen."""
        yield Header()
        with Container():
            yield Label("Create GitHub Issue", classes="title")
            yield Input(placeholder="Issue title", id="title")
            yield TextArea(placeholder="Issue description", id="description")
            yield Button("Submit", variant="primary", id="submit")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "submit":
            self.action_submit()

    def action_submit(self) -> None:
        """Submit the issue."""
        title = self.query_one("#title").value
        description = self.query_one("#description").text

        if not title:
            self.notify("Please enter a title", severity="error")
            return

        try:
            issue_url = self.service_manager.github.create_github_issue(
                None,
                title,
                description,
                {},
            )
            self.notify(f"Issue created: {issue_url}", severity="information")
            self.app.pop_screen()
        except Exception as e:
            self.notify(f"Failed to create issue: {e}", severity="error")


class ServiceManagerApp(BaseScriptApp):
    """Main service manager application."""

    CSS = """
    Screen {
        align: center middle;
    }

    .title {
        text-style: bold;
        margin: 1 0;
    }

    ServiceList {
        width: 100%;
        height: auto;
        border: solid green;
    }

    ServiceItem {
        height: 3;
        padding: 0 1;
    }

    ServiceItem:hover {
        background: $boost;
    }

    ServiceItem > Horizontal {
        width: 100%;
        height: 100%;
        align: left middle;
    }

    ServiceItem .status {
        margin-left: 2;
    }

    Button {
        margin: 1 1;
    }

    Input, TextArea {
        margin: 1 0;
    }

    #description {
        height: 10;
    }
    """

    TITLE = "Service Manager"
    SCREENS = {
        "services": ServiceControlScreen,
        "issue": IssueScreen,
        "feedback": FeedbackScreen,
    }
    BINDINGS = [
        Binding("s", "push_screen('services')", "Services", show=True),
        Binding("i", "push_screen('issue')", "Issue", show=True),
        Binding("f", "push_screen('feedback')", "Feedback", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, service_manager) -> None:
        """Initialize service manager app.

        Args:
        ----
            service_manager: Service manager instance

        """
        super().__init__()
        self.service_manager = service_manager

    def compose(self) -> ComposeResult:
        """Compose the app."""
        yield Header()
        with Container():
            yield Label("Welcome to Service Manager", classes="title")
            yield Label("Press 's' for Services, 'i' for Issues, or 'q' to Quit")
        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount event."""
        self.title = self.TITLE

    def push_screen(self, screen_name: str) -> None:
        """Push a screen onto the stack.

        Args:
        ----
            screen_name: Name of the screen to push

        """
        screen_class = self.SCREENS.get(screen_name)
        if screen_class:
            self.push_screen(screen_class(self.service_manager))
