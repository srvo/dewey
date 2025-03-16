from django.contrib.auth import get_user_model
from django.test import TestCase


class CustomUserTests(TestCase):
    def test_create_user(self) -> None:
        User = get_user_model()
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        assert user.email == "test@example.com"
        assert user.is_active
        assert not user.is_staff

    def test_create_superuser(self) -> None:
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="testpass123",
        )
        assert admin_user.email == "admin@example.com"
        assert admin_user.is_active
        assert admin_user.is_staff

    def test_str_representation(self) -> None:
        User = get_user_model()
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        assert str(user) == "test@example.com"
