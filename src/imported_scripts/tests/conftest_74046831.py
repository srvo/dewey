"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import Generator

import pytest


# Session-scoped fixtures
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Global test settings
@pytest.fixture(autouse=True)
def mock_settings(monkeypatch) -> None:
    """Mock settings for tests."""
    monkeypatch.setenv("LLAMA_INDEX_TESTING", "true")
    monkeypatch.setenv("TESTING", "true")


# Database fixtures
@pytest.fixture
def db_loader_config() -> dict:
    """Fixture for database loader configuration."""
    return {"uri": "sqlite:///:memory:", "queries": ["SELECT 1"]}


# HTTP fixtures
@pytest.fixture
def mock_http_client():
    """Fixture for mocking HTTP requests."""
    from respx import MockRouter

    with MockRouter() as respx_mock:
        yield respx_mock
