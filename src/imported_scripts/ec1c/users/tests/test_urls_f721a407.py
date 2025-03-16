from django.urls import resolve, reverse
from ec1c.users.models import User


def get_user_detail_url(user: User) -> str:
    """Generates the URL for the user detail view.

    Args:
        user: The User object.

    Returns:
        The URL string.

    """
    return reverse("api:user-detail", kwargs={"pk": user.pk})


def get_user_list_url() -> str:
    """Generates the URL for the user list view.

    Returns:
        The URL string.

    """
    return reverse("api:user-list")


def get_user_me_url() -> str:
    """Generates the URL for the user me view.

    Returns:
        The URL string.

    """
    return reverse("api:user-me")


def resolve_url(url: str) -> str:
    """Resolves a URL to its view name.

    Args:
        url: The URL string.

    Returns:
        The view name.

    """
    return resolve(url).view_name


def test_user_detail(user: User) -> None:
    """Tests the user detail URL and view name.

    Args:
        user: The User object.

    """
    expected_url = f"/api/users/{user.pk}/"
    assert get_user_detail_url(user) == expected_url
    assert resolve_url(expected_url) == "api:user-detail"


def test_user_list() -> None:
    """Tests the user list URL and view name."""
    expected_url = "/api/users/"
    assert get_user_list_url() == expected_url
    assert resolve_url(expected_url) == "api:user-list"


def test_user_me() -> None:
    """Tests the user me URL and view name."""
    expected_url = "/api/users/me/"
    assert get_user_me_url() == expected_url
    assert resolve_url(expected_url) == "api:user-me"
