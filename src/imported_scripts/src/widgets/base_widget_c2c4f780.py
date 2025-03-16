"""Base widget for ECIC application."""

import logging

from textual.reactive import reactive
from textual.widget import Widget

logger = logging.getLogger(__name__)


class BaseWidget(Widget):
    """Base widget with common functionality."""

    # Reactive properties
    is_loading = reactive(False)
    has_error = reactive(False)
    error_message = reactive("")

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the base widget."""
        super().__init__(*args, **kwargs)
        self.initialize()

    def initialize(self) -> None:
        """Initialize widget-specific functionality."""

    async def on_mount(self) -> None:
        """Handle widget mounting."""
        try:
            await self.refresh_content()
        except Exception as e:
            self.handle_error(f"Error mounting widget: {e!s}")

    async def refresh_content(self) -> None:
        """Refresh widget content."""
        try:
            self.is_loading = True
            await self.update_content()
        except Exception as e:
            self.handle_error(f"Error refreshing content: {e!s}")
        finally:
            self.is_loading = False

    async def update_content(self) -> None:
        """Update widget content. Override in subclasses."""

    def handle_error(self, message: str) -> None:
        """Handle and display errors."""
        logger.error(message)
        self.has_error = True
        self.error_message = message

    def clear_error(self) -> None:
        """Clear any error state."""
        self.has_error = False
        self.error_message = ""
