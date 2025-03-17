"""Authentication fixtures."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a regular test user."""
    return User.objects.create_user(email="test@example.com", password="testpass123")


@pytest.fixture
def admin_user(db):
    """Create an admin test user."""
    return User.objects.create_superuser(
        email="admin@example.com", password="adminpass123"
    )
