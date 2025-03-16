"""Configure pytest for Django testing."""

import os

import django
from django.conf import settings

# Configure Django settings before running tests
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings_test")


def pytest_configure() -> None:
    """Configure Django settings for pytest."""
    if not settings.configured:
        django.setup()
