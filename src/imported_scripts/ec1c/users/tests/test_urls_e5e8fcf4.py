from django.urls import resolve, reverse
from ec1c.users.models import User


def reverse_url(view_name: str) -> str:
    """Reverses a URL given its view name.

    Args:
        view_name: The name of the view to reverse.

    Returns:
        The reversed URL as a string.

    """
    return reverse(view_name)


def resolve_url(url: str) -> str:
    """Resolves a URL to its view name.

    Args:
        url: The URL to resolve.

    Returns:
        The view name as a string.

    """
    return resolve(url).view_name


def test_detail(user: User) -> None:
    """Tests the user detail view.

    Args:
        user: The user object to test with.

    """
    expected_url = f"/users/{user.pk}/"
    assert reverse("users:detail", kwargs={"pk": user.pk}) == expected_url
    assert resolve(expected_url).view_name == "users:detail"


def test_update() -> None:
    """Tests the user update view."""
    expected_url = "/users/~update/"
    assert reverse("users:update") == expected_url
    assert resolve(expected_url).view_name == "users:update"


def test_redirect() -> None:
    """Tests the user redirect view."""
    expected_url = "/users/~redirect/"
    assert reverse("users:redirect") == expected_url
    assert resolve(expected_url).view_name == "users:redirect"
