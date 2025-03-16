import asyncio
from unittest.mock import AsyncMock

import pytest
from port5.tick_manager import MockAPIServer, TickManagerApp
from textual.widgets import DataTable


@pytest.fixture
async def mock_api():
    """Create a mock API server for testing."""
    api = MockAPIServer()
    api.companies = [
        {"ticker": "AAPL", "company": "Apple Inc.", "tick": 1},
        {"ticker": "MSFT", "company": "Microsoft Corp.", "tick": 2},
        {"ticker": "GOOGL", "company": "Alphabet Inc.", "tick": 3},
    ]
    return api


@pytest.fixture
async def app(mock_api):
    """Create a TickManagerApp instance for testing."""
    app = TickManagerApp()
    app.api_client = await mock_api
    app = await app.run_test()  # Get the app instance
    await app.load_companies()  # Load initial data
    return app


@pytest.mark.asyncio
async def test_connection_status(app) -> None:
    app = await app  # Await the app fixture
    # Test initial connection
    assert app.connection_status == "connected"

    # Simulate connection loss
    app.api_client.ping = AsyncMock(return_value=False)
    await asyncio.sleep(11)  # Wait for next check
    assert app.connection_status == "disconnected"


@pytest.mark.asyncio
async def test_api_failure_handling(app) -> None:
    app = await app  # Await the app fixture
    # Simulate API failure
    app.api_client.get_companies = AsyncMock(side_effect=Exception("API Error"))

    # Trigger refresh
    await app.press("r")

    # Verify error handling
    assert "Failed to refresh" in app.notifications[-1].message
    assert app.connection_state.failure_count > 0


@pytest.mark.asyncio
async def test_ui_state_persistence(app) -> None:
    app = await app  # Await the app fixture
    # Add test data
    app.api_client.companies = [
        {"ticker": "TEST", "company": "Test Company", "tick": 0},
    ]

    # Select a company
    await app.click(DataTable)
    await app.press("down")

    # Verify selection state
    assert app.current_company is not None
    assert app.query_one("#current_tick_display").renderable != "0"
    assert app.performance_metrics.get_stats()["api_response"]["count"] > 0
