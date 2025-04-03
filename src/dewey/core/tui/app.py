#!/usr/bin/env python3
"""TUI Application Module

This module provides the main TUI application class.
"""

import argparse
import os
import sys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

from dewey.core.base_script import BaseScript

# Use relative imports
from ....ui.screens.feedback_manager_screen import FeedbackManagerScreen
from ....ui.screens.port5_screen import Port5Screen


class ModuleScreen(BaseScript, Screen):
    """Base screen for module displays."""

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("b", "go_back", "Back", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    def __init__(self, title: str) -> None:
        """Initialize module screen.

        Args:
            title: The title of the module screen.

        """
        super().__init__(config_section="tui")
        self.title = title
        self.status = reactive("Idle")

    def compose(self) -> ComposeResult:
        """Create child widgets.

        Yields:
            ComposeResult: The composed widgets.

        """
        yield Header(show_clock=True)
        yield Container(
            Vertical(
                Label(f"Module: {self.title}", id="module-title"),
                Label("Status: [yellow]Loading...[/]", id="status"),
                Static("", id="content"),
                id="main-content",
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        """Handle screen mount event."""
        self.update_content()

    def update_content(self) -> None:
        """Update screen content."""
        pass

    async def action_go_back(self) -> None:
        """Go back to main menu."""
        await self.app.push_screen("main")

    async def action_refresh(self) -> None:
        """Refresh screen content."""
        self.update_content()

    def execute(self) -> None:
        """Execute the module screen.

        This is a base class and should be overridden in subclasses.
        """
        self.logger.info(
            "ModuleScreen.execute() called. This is a base class and should be overridden."
        )


class ResearchScreen(ModuleScreen):
    """Research module screen."""

    def update_content(self) -> None:
        """Update research content."""
        content = self.query_one("#content", Static)
        content.update(
            """[bold]Research Module[/bold]

• Financial Analysis
  - Company Analysis
  - Portfolio Analysis
  - ESG Scoring

• Ethical Analysis
  - ESG Reports
  - Sustainability Metrics

• Research Workflows
  - Data Collection
  - Analysis Pipeline
  - Report Generation"""
        )


class DatabaseScreen(ModuleScreen):
    """Database module screen."""

    def update_content(self) -> None:
        """Update database content."""
        content = self.query_one("#content", Static)
        content.update(
            """[bold]Database Module[/bold]

• Schema Management
  - Table Definitions
  - Index Management
  - Migrations

• Data Operations
  - Query Interface
  - Backup/Restore
  - Data Validation"""
        )


class LLMAgentsScreen(ModuleScreen):
    """LLM Agents module screen."""

    def update_content(self) -> None:
        """Update LLM agents content."""
        content = self.query_one("#content", Static)
        content.update(
            """[bold]LLM Agents[/bold]

• RAG Agent
  - Document Retrieval
  - Context Generation
  - Response Synthesis

• Ethical Analysis Agent
  - ESG Assessment
  - Risk Analysis
  - Recommendations

• Research Agent
  - Data Collection
  - Analysis
  - Report Generation"""
        )


class EnginesScreen(ModuleScreen):
    """Engines module screen."""

    def update_content(self) -> None:
        """Update engines content."""
        content = self.query_one("#content", Static)
        content.update(
            """[bold]Engines Module[/bold]

• Research Engines
  - Base Engine
  - Deepseek Engine

• Analysis Engines
  - Financial Analysis
  - ESG Analysis

• Data Processing
  - ETL Pipeline
  - Data Validation"""
        )


class MainMenu(Screen):
    """Main menu screen."""

    BINDINGS = [Binding("q", "quit", "Quit", show=True)]

    def compose(self) -> ComposeResult:
        """Create child widgets.

        Yields:
            ComposeResult: The composed widgets.

        """
        yield Header(show_clock=True)
        yield Container(
            Vertical(
                Label("[bold]Dewey Core Modules[/bold]", id="title"),
                Horizontal(
                    Button("Research", id="research", variant="primary"),
                    Button("Database", id="database", variant="primary"),
                    Button("Engines", id="engines", variant="primary"),
                    id="row1",
                ),
                Horizontal(
                    Button("Data Upload", id="data-upload", variant="primary"),
                    Button("CRM", id="crm", variant="primary"),
                    Button("Bookkeeping", id="bookkeeping", variant="primary"),
                    id="row2",
                ),
                Horizontal(
                    Button("Automation", id="automation", variant="primary"),
                    Button("Sync", id="sync", variant="primary"),
                    Button("Config", id="config", variant="primary"),
                    id="row3",
                ),
                Label("[bold]LLM Components[/bold]", id="llm-title"),
                Horizontal(
                    Button("LLM Agents", id="llm-agents", variant="warning"),
                    id="llm-row",
                ),
                Label("[bold]Tools & Utilities[/bold]", id="tools-title"),
                Horizontal(
                    Button(
                        "Feedback Manager", id="feedback-manager", variant="success"
                    ),
                    Button("Port5 Research", id="port5", variant="success"),
                    id="tools-row",
                ),
                id="menu",
            )
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button press event.

        """
        button_id = event.button.id
        screen_map = {
            "research": ResearchScreen("Research"),
            "database": DatabaseScreen("Database"),
            "engines": EnginesScreen("Engines"),
            "llm-agents": LLMAgentsScreen("LLM Agents"),
            "feedback-manager": "feedback-manager",
            "port5": "port5",
        }

        if button_id in screen_map:
            screen = screen_map[button_id]
            if isinstance(screen, str):
                self.app.push_screen(screen)
            else:
                self.app.push_screen(screen)


class DeweyTUI(App):
    """Main TUI application."""

    TITLE = "Dewey TUI"
    CSS = """
    Screen {
        align: center middle;
    }

    #menu {
        width: 80%;
        height: auto;
        border: solid green;
        padding: 1;
    }

    #title, #llm-title, #tools-title {
        text-align: center;
        padding: 1;
    }

    Button {
        width: 20;
        margin: 1 2;
    }

    #row1, #row2, #row3, #llm-row, #tools-row {
        height: auto;
        align: center middle;
        padding: 1;
    }

    #module-title {
        text-align: center;
        padding: 1;
    }

    #main-content {
        width: 80%;
        height: auto;
        border: solid green;
        padding: 1;
    }

    #content {
        padding: 1;
    }
    """

    SCREENS = {
        "main": MainMenu,
        "research": ResearchScreen,
        "database": DatabaseScreen,
        "engines": EnginesScreen,
        "llm-agents": LLMAgentsScreen,
        "feedback-manager": FeedbackManagerScreen,
        "port5": Port5Screen,
    }

    def __init__(self):
        """Initialize the Dewey TUI application."""
        super().__init__()
        # Load additional CSS files
        self.stylesheet_paths = [
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "../../../src/ui/assets/feedback_manager.tcss",
                )
            ),
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__), "../../../src/ui/assets/port5.tcss"
                )
            ),
        ]

    def on_mount(self) -> None:
        """Handle app mount event."""
        self.push_screen("main")

    def execute(self) -> None:
        """Execute the TUI application."""
        self.run()


class TUIApp(BaseScript):
    """TUI Application class that integrates with BaseScript."""

    def __init__(self) -> None:
        """Initialize the TUI application."""
        super().__init__(
            name="DeweyTUI",
            description="Textual User Interface for Dewey Core Modules",
            config_section="tui",
            requires_db=False,
            enable_llm=False,
        )
        self.tui_app = DeweyTUI()

    def run(self) -> None:
        """Run the TUI application."""
        self.logger.info("Starting Dewey TUI application")
        self.tui_app.run()

    def setup_argparse(self) -> argparse.ArgumentParser:
        """Set up command line arguments.

        Returns:
            An argument parser configured with common options.

        """
        parser = super().setup_argparse()
        # Add TUI-specific arguments here if needed
        return parser

    def _cleanup(self) -> None:
        """Clean up resources."""
        super()._cleanup()
        self.logger.info("TUI application cleanup complete")


def run() -> None:
    """Run the TUI application."""
    app = TUIApp()
    app.execute()


if __name__ == "__main__":
    run()
