from ec1c.users.models import User


def get_user_absolute_url(user: User) -> str:
    """Retrieves the absolute URL for a given user.

    Args:
    ----
        user: The User object.

    Returns:
    -------
        The absolute URL string for the user.

    """
    return f"/users/{user.pk}/"


def test_user_get_absolute_url(user: User) -> None:
    """Tests that the get_absolute_url method returns the correct URL.

    Args:
    ----
        user: A User object for testing.

    """
    assert get_user_absolute_url(user) == f"/users/{user.pk}/"
