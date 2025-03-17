"""Database fixtures for testing."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext


@pytest.fixture
def db_queries():
    """Capture database queries."""
    with CaptureQueriesContext(connection) as context:
        yield context
