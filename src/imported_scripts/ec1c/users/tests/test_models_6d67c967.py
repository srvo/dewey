from io import StringIO

import pytest
from django.core.management import call_command
from ec1c.users.models import User


@pytest.mark.django_db
class TestUserManager:
    """Tests for the custom user manager."""

    def test_create_user(self) -> None:
        """Test creating a regular user."""
        user: User = User.objects.create_user(
            email="john@example.com",
            password="something-r@nd0m!",  # noqa: S106
        )
        self._assert_user_properties(user, "john@example.com", False, False)
        assert user.check_password("something-r@nd0m!")
        assert user.username is None

    def test_create_superuser(self) -> None:
        """Test creating a superuser."""
        user: User = User.objects.create_superuser(
            email="admin@example.com",
            password="something-r@nd0m!",  # noqa: S106
        )
        self._assert_user_properties(user, "admin@example.com", True, True)
        assert user.username is None

    def test_create_superuser_username_ignored(self) -> None:
        """Test that username is ignored when creating a superuser."""
        user: User = User.objects.create_superuser(
            email="test@example.com",
            password="something-r@nd0m!",  # noqa: S106
        )
        assert user.username is None

    def _assert_user_properties(
        self,
        user: User,
        email: str,
        is_staff: bool,
        is_superuser: bool,
    ) -> None:
        """Helper function to assert common user properties."""
        assert user.email == email
        assert user.is_staff == is_staff
        assert user.is_superuser == is_superuser


@pytest.mark.django_db
def test_createsuperuser_command() -> None:
    """Ensure createsuperuser command works with our custom manager."""
    out: StringIO = StringIO()
    command_result: None = call_command(
        "createsuperuser",
        "--email",
        "henry@example.com",
        interactive=False,
        stdout=out,
    )

    assert command_result is None
    assert out.getvalue() == "Superuser created successfully.\n"
    user: User = User.objects.get(email="henry@example.com")
    assert not user.has_usable_password()
