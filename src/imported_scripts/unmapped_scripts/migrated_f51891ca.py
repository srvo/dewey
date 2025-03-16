from django.test import SimpleTestCase
from django.urls import reverse


class PagesTests(SimpleTestCase):
    """Test suite for pages application views and functionality."""

    def test_about_page_status_code(self) -> None:
        """Verify the about page returns HTTP 200 status code."""
        response = self.client.get(reverse("pages:about"))
        assert response.status_code == 200

    def test_home_page_status_code(self) -> None:
        """Verify the home page returns HTTP 200 status code."""
        response = self.client.get(reverse("pages:home"))
        assert response.status_code == 200

    def test_about_template(self) -> None:
        """Verify the about page uses the correct template."""
        response = self.client.get(reverse("pages:about"))
        self.assertTemplateUsed(response, "pages/about.html")

    def test_invalid_url_returns_404(self) -> None:
        """Verify invalid URLs return HTTP 404 status code."""
        response = self.client.get("/invalid-url/")
        assert response.status_code == 404

    def test_csrf_protected_endpoints(self) -> None:
        """Verify CSRF protection is enabled for POST requests.

        Tests that POST requests without CSRF tokens are rejected with 403.
        """
        response = self.client.post(reverse("pages:home"))
        assert response.status_code == 403

    def test_malformed_requests(self) -> None:
        """Verify the application handles malformed requests gracefully.

        Tests that requests with invalid headers still return valid responses.
        """
        response = self.client.get(
            reverse("pages:home"),
            HTTP_USER_AGENT="",
            HTTP_ACCEPT="invalid",
        )
        assert response.status_code == 200
