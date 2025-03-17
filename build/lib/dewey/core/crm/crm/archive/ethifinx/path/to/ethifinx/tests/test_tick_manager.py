import pytest_asyncio

@pytest_asyncio.fixture
async def app():
    app = TickManagerApp()
    await app.run_test()
    yield app

@pytest_asyncio.fixture
async def mock_api():
    mock_api = MockApi()
    yield mock_api 