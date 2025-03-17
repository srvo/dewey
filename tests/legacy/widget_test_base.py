
# Refactored from: widget_test_base
# Date: 2025-03-16T16:19:10.982317
# Refactor Version: 1.0
"""Base class for widget tests."""

from typing import Generic, TypeVar

import pytest
from textual.app import App
from textual.pilot import Pilot
from textual.widget import Widget

T = TypeVar("T", bound=Widget)


class WidgetTestBase(Generic[T]):
    """Base class for widget tests."""

    class TestApp(App):
        """Test app for widget testing."""

        def __init__(self, widget_class: type[Widget], **kwargs) -> None:
            super().__init__()
            self.widget_class = widget_class
            self.widget_kwargs = kwargs
            self.widget = None

        async def on_mount(self) -> None:
            """Create widget when app mounts."""
            self.widget = self.widget_class(**self.widget_kwargs)
            await self.view.mount(self.widget)

    @pytest.fixture
    async def app(self, widget_class: type[T], **kwargs):
        """Create test app with widget."""
        app = self.TestApp(widget_class, **kwargs)
        async with app.run_test() as pilot:
            await pilot.pause()  # Wait for widget to mount
            yield pilot

    @pytest.fixture
    async def widget(self, app: Pilot) -> T:
        """Get the widget being tested."""
        return app.app.widget

    async def click_button(self, app: Pilot, button_id: str) -> None:
        """Click a button in the widget."""
        await app.click(f"#{button_id}")

    async def press_key(self, app: Pilot, key: str) -> None:
        """Press a key."""
        await app.press(key)

    async def check_text(self, app: Pilot, selector: str, expected: str) -> None:
        """Check text content of an element."""
        element = app.app.query_one(selector)
        assert element.text == expected

    async def check_visible(
        self,
        app: Pilot,
        selector: str,
        visible: bool = True,
    ) -> None:
        """Check if an element is visible."""
        element = app.app.query_one(selector)
        assert element.visible == visible

    async def check_style(self, app: Pilot, selector: str, **styles) -> None:
        """Check element styles."""
        element = app.app.query_one(selector)
        for prop, value in styles.items():
            assert getattr(element.styles, prop) == value
