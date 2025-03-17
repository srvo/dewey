"""Basic test to verify test environment."""

import pytest


@pytest.mark.django_db
def test_minimal_setup():
    """Verify test environment is working."""
    from accounts.models import CustomUser

    assert CustomUser.objects.count() == 0
