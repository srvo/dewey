"""Test account functionality."""

from django.contrib.auth import get_user_model
from django.test import TestCase


class TestAccounts(TestCase):
    def test_admin_creation(self) -> None:
        User = get_user_model()
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="testpass123",
        )
        assert admin.is_superuser
        assert admin.is_staff

    def test_user_creation(self) -> None:
        User = get_user_model()
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        assert not user.is_superuser
        assert not user.is_staff
