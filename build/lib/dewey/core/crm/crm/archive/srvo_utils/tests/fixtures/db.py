"""Database fixtures for testing."""

import pytest
from django.test.utils import setup_databases, teardown_databases


@pytest.fixture(scope="session")
def django_db_setup():
    """Set up Django test databases for the test session."""
    # Setup test databases
    old_config = setup_databases(verbosity=1, interactive=False)
    yield
    # Teardown test databases
    teardown_databases(old_config, verbosity=1)


@pytest.fixture
def db(django_db_setup):
    """Provide a clean database for each test."""
    pass
