"""Unit tests for Pydantic models."""

from pydantic import BaseModel, ValidationError
import pytest


class TestUserModel:
    """Test suite for User model validation."""

    def test_valid_user(self):
        """Test that valid user data passes validation."""

        class User(BaseModel):
            """User model for authentication."""

            username: str
            email: str
            is_active: bool = True

        user = User(username="testuser", email="test@example.com")
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True

    def test_invalid_email(self):
        """Test that invalid email raises validation error."""

        class User(BaseModel):
            """User model for authentication."""

            username: str
            email: str
            is_active: bool = True

        with pytest.raises(ValidationError):
            User(username="testuser", email="not-an-email")
