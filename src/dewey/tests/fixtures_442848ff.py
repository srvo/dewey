```python
import pytest_asyncio


class TickManagerApp:  # Placeholder for actual class
    async def run_test(self):
        pass


class MockApi:  # Placeholder for actual class
    pass


@pytest_asyncio.fixture
async def app() -> TickManagerApp:
    """Fixture to provide a TickManagerApp instance for testing.

    Yields:
        TickManagerApp: An instance of the TickManagerApp.
    """
    app_instance = TickManagerApp()
    await app_instance.run_test()
    yield app_instance


@pytest_asyncio.fixture
async def mock_api() -> MockApi:
    """Fixture to provide a MockApi instance for testing.

    Yields:
        MockApi: An instance of the MockApi.
    """
    mock_api_instance = MockApi()
    yield mock_api_instance
```
