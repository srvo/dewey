```python
import pytest
import pytest_asyncio

class TickManagerApp:  # Placeholder for the actual app class
    async def run_test(self):
        """Placeholder for running the app in test mode."""
        pass

    def query_one(self, selector: str):
        """Placeholder for querying UI elements."""
        class MockElement:
            def __init__(self, text: str):
                self.text = text

        if selector == "#title":
            return MockElement("Tick Manager")
        return MockElement("")


@pytest_asyncio.fixture
async def app() -> TickManagerApp:
    """Fixture to provide a running TickManagerApp instance."""
    app = TickManagerApp()
    await app.run_test()
    return app


@pytest.mark.asyncio
async def test_ui_initialization(app: TickManagerApp) -> None:
    """Tests that the UI initializes with the correct title."""
    title = app.query_one("#title")
    assert title.text == "Tick Manager"
```
