"""Tests for account and page functionality."""

import pytest
from django.urls import reverse
from tests.unit.base import BaseTestCase
from accounts.models import CustomUser as User
from core.pages.models import Page


@pytest.mark.django_db
class TestAccounts(BaseTestCase):
    @pytest.fixture(autouse=True)
    def setup_test(self, django_db_setup):
        """Set up test environment."""
        pass

    def test_user_creation(self):
        """Test user creation and authentication"""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        assert user.email == "test@example.com"
        assert user.check_password("testpass123")
        assert not user.is_staff
        assert not user.is_superuser

    def test_superuser_creation(self):
        """Test superuser creation"""
        user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )
        assert user.is_staff
        assert user.is_superuser


@pytest.mark.django_db
class TestPages(BaseTestCase):
    @pytest.fixture(autouse=True)
    def setup_test(self, django_db_setup):
        """Set up test environment."""
        pass

    def test_page_creation(self):
        """Test basic page creation"""
        page = Page.objects.create(
            title="Test Page", slug="test-page", content="Test content"
        )
        assert page.title == "Test Page"
        assert page.slug == "test-page"
        assert page.content == "Test content"

    def test_page_url(self):
        """Test page URL resolution"""
        page = Page.objects.create(
            title="Test Page", slug="test-page", content="Test content"
        )
        url = reverse("pages:page", kwargs={"slug": page.slug})
        assert url == f"/pages/{page.slug}/"
