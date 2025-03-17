"""Base test class for all unit tests in the application.

This module provides the foundational test class that all unit tests should inherit from.
It handles common setup and teardown operations, and provides access to essential
testing utilities like the Django test client and API instance.

Key Features:
- Inherits from Django's TestCase for database transaction management
- Automatic setup of test client and API instance
- Clean API state between tests
- Integration with pytest fixtures
- Consistent test environment configuration

Usage:
    All unit tests should inherit from BaseTestCase:

    class MyTests(BaseTestCase):
        def test_example(self):
            response = self.client.get('/some/url/')
            self.assertEqual(response.status_code, 200)

Design Principles:
1. Consistency: Provides a uniform test environment
2. Isolation: Ensures clean state between tests
3. Extensibility: Easy to add common functionality
4. Maintainability: Clear structure and documentation
"""

import pytest
from django.test import TestCase
from core.api import api


class BaseTestCase(TestCase):
    """Base class providing common test functionality for all unit tests.

    This class extends Django's TestCase to provide additional features:
    - Automatic test client setup
    - API instance access
    - Common test utilities
    - Clean state between tests

    Attributes:
        client: Django test client for making HTTP requests
        api: Shared API instance for making API calls
    """

    @pytest.fixture(autouse=True)
    def _setup(self, db, client, ninja_api):
        """Automatically configure test environment for each test.

        This fixture runs before each test to:
        - Initialize the test client
        - Set up the API instance
        - Ensure database access

        Args:
            db: Pytest fixture providing database access
            client: Django test client fixture
            ninja_api: Shared API instance fixture
        """
        self.client = client  # Django test client for HTTP requests
        self.api = ninja_api  # Shared API instance for making API calls

    def setUp(self):
        """Perform additional setup before each test.

        This method:
        - Calls parent class setup
        - Can be extended by subclasses for custom setup
        """
        super().setUp()
