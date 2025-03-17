"""Test account functionality."""

from django.test import TestCase
from django.contrib.auth import get_user_model


class TestAccounts(TestCase):
    def test_admin_creation(self):
        User = get_user_model()
        admin = User.objects.create_superuser(
            email="admin@example.com", password="testpass123"
        )
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)

    def test_user_creation(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
