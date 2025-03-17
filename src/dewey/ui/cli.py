"""Command-line interface for Dewey TUI application."""

import typer
from textual.app import App
from .ui.app import DeweyApp

app = typer.Typer(help="Dewey - Terminal User Interface for Script Management")

@app.command()
def main():
    """Launch the Dewey TUI application."""
    app = DeweyApp()
    app.run()

if __name__ == "__main__":
    app() 