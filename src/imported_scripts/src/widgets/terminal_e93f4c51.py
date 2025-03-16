"""Terminal widget for ECIC."""

from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Input, RichLog

from .base import BaseWidget


class TerminalWidget(BaseWidget):
    """A simple terminal widget that displays output and accepts commands."""

    BINDINGS = [
        Binding("ctrl+l", "clear", "Clear"),
    ]

    class CommandEntered(Message):
        """Message sent when a command is entered."""

        def __init__(self, command: str) -> None:
            """Initializes the CommandEntered message.

            Args:
                command: The command that was entered.

            """
            self.command = command
            super().__init__()

    def __init__(self) -> None:
        """Initializes the terminal widget."""
        super().__init__()
        self._log: RichLog | None = None
        self._input: Input | None = None

    def compose(self):
        """Composes the terminal widget."""
        self._log = RichLog()
        self._log.markup = True
        self._input = Input(placeholder="Enter command...", id="terminal-input")

        with Vertical():
            yield self._log
            yield self._input

    async def on_mount(self) -> None:
        """Handles widget mount."""
        await super().on_mount()
        self._focus_input()

    def write(self, text: str) -> None:
        """Writes text to the terminal.

        Args:
            text: The text to write.

        """
        if self._log:
            self._log.write(text)

    def action_clear(self) -> None:
        """Clears the terminal."""
        self._clear_terminal()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handles command input.

        Args:
            event: The Input.Submitted event.

        """
        await self._handle_command_submission(event.value)

    def _clear_terminal(self) -> None:
        """Clears the terminal."""
        if self._log:
            self._log.clear()

    async def _handle_command_submission(self, command_text: str) -> None:
        """Handles the submission of a command.

        Args:
            command_text: The text of the command submitted.

        """
        command = command_text.strip()
        if command:
            self.write(f"\n[bold]> {command}[/]")
            self._clear_input()
            msg = self.CommandEntered(command)
            self.post_message(msg)

    def _clear_input(self) -> None:
        """Clears the input field."""
        if self._input:
            self._input.value = ""

    def _focus_input(self) -> None:
        """Focuses the input field."""
        if self._input:
            self._input.focus()
