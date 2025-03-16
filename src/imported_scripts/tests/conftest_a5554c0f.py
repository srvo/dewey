"""Test configuration and fixtures."""

import logging
import os
import sys
from unittest.mock import AsyncMock, patch

import aiohttp
import httpx
import pytest
from prefect.testing.utilities import prefect_test_harness

# Add the parent directory to the Python path
parent_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)
sys.path.insert(0, parent_dir)

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@pytest.fixture(scope="session", autouse=True)
def prefect_test_mode():
    """Enable test mode for all tests."""
    with prefect_test_harness():
        yield


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, status_code: int, json_data: dict) -> None:
        self.status_code = status_code
        self._json_data = json_data

    async def json(self):
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            msg = "Mock API error"
            raise httpx.HTTPStatusError(
                msg,
                request=httpx.Request("GET", "http://mock"),
                response=self,
            )


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for testing."""
    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.get = AsyncMock()
        client_instance.post = AsyncMock()
        mock_client.return_value.__aenter__.return_value = client_instance
        yield {"get": client_instance.get, "post": client_instance.post}


class MockAioHTTPResponse:
    """Mock aiohttp response for testing."""

    def __init__(self, status: int, json_data: dict) -> None:
        self.status = status
        self._json_data = json_data

    async def json(self):
        return self._json_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockAioHTTPSession:
    """Mock aiohttp session for testing."""

    def __init__(self) -> None:
        self.responses = {}
        self.calls = []

    def set_response(self, url: str, json_data: dict, status: int = 200) -> None:
        """Set mock response for a URL."""
        self.responses[url] = (json_data, status)

    async def get(self, url: str, **kwargs):
        """Mock GET request."""
        self.calls.append(("GET", url, kwargs))
        if url in self.responses:
            json_data, status = self.responses[url]
            return MockAioHTTPResponse(status, json_data)
        msg = f"No mock response for {url}"
        raise aiohttp.ClientError(msg)

    async def post(self, url: str, **kwargs):
        """Mock POST request."""
        self.calls.append(("POST", url, kwargs))
        if url in self.responses:
            json_data, status = self.responses[url]
            return MockAioHTTPResponse(status, json_data)
        msg = f"No mock response for {url}"
        raise aiohttp.ClientError(msg)

    async def close(self) -> None:
        """Mock close session."""


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for testing."""
    with patch("aiohttp.ClientSession", return_value=MockAioHTTPSession()) as mock:
        session = mock.return_value
        yield session


class MockOpenAI:
    """Mock OpenAI client for testing."""

    def __init__(self) -> None:
        self.responses = {}
        self.calls = []

    def add_response(self, model: str, response: dict) -> None:
        """Add mock response for a model."""
        self.responses[model] = response

    async def create(self, model: str, messages: list, **kwargs):
        """Mock create completion."""
        self.calls.append((messages, model, kwargs))
        if model in self.responses:
            return self.responses[model]
        msg = f"No mock response for model {model}"
        raise ValueError(msg)


@pytest.fixture
def mock_openai():
    """Mock OpenAI client for testing."""
    return MockOpenAI()


class MockDatabase:
    """Mock database for testing."""

    def __init__(self) -> None:
        self.queries = []

    async def execute(self, query: str, *args, **kwargs) -> None:
        """Mock query execution."""
        self.queries.append((query, args, kwargs))


@pytest.fixture
def mock_database():
    """Mock database for testing."""
    return MockDatabase()


@pytest.fixture
def mock_searxng(mock_aiohttp_session):
    """Mock SearXNG API responses."""

    def setup_mock(query_results) -> None:
        base_url = "http://test-searxng.com/search"
        mock_aiohttp_session.set_response(
            base_url,
            {"query": "test", "results": query_results},
        )

    return setup_mock


@pytest.fixture
def mock_searxng_response():
    """Fixture to provide mock SearXNG response."""
    return {
        "results": [
            {
                "title": "Test Controversy",
                "url": "http://example.com",
                "snippet": "Test controversy details",
            },
        ],
    }


@pytest.fixture
def mock_farfalle_response():
    """Fixture to provide mock Farfalle API response."""
    return {
        "messages": [{"role": "assistant", "content": "Test analysis of controversy"}],
    }
