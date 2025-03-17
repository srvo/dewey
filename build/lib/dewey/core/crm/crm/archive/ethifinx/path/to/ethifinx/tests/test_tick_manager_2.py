import pytest_asyncio

@pytest_asyncio.fixture
async def app():
    app = TickManagerApp()
    await app.run_test()
    return app

@pytest.mark.asyncio
async def test_ui_initialization(app):
    # existing test code...
    title = app.query_one("#title")
    assert title.text == "Tick Manager" 