"""Base fixtures for all tests."""

import pytest
from django.test import Client


@pytest.fixture
def client():
    """Provide a Django test client."""
    return Client()
