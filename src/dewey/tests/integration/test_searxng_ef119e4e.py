#!/usr/bin/env python3

import os

import pytest
import requests


class TestSearXNG:
    """Test suite for SearXNG service."""

    @pytest.fixture(autouse=True)
    def setup(self, service_urls: dict[str, str], auth_headers: dict[str, str]) -> None:
        """Set up test fixtures."""
        self.base_url = service_urls["searxng"]
        self.auth_headers = auth_headers

    def test_health_endpoint(self) -> None:
        """Test health endpoint."""
        response = requests.get(f"{self.base_url}/healthz")
        assert response.status_code == 200

    def test_search_functionality(self) -> None:
        """Test basic search functionality."""
        params = {"q": "test query", "format": "json"}
        response = requests.get(
            f"{self.base_url}/search",
            params=params,
            headers=self.auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_search_engines(self) -> None:
        """Test available search engines."""
        response = requests.get(f"{self.base_url}/config", headers=self.auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "engines" in data
        assert len(data["engines"]) > 0

    def test_authentication(self) -> None:
        """Test authentication requirements."""
        # Test without auth
        response = requests.get(f"{self.base_url}/search?q=test")
        assert response.status_code == 401

        # Test with auth
        response = requests.get(
            f"{self.base_url}/search?q=test",
            headers=self.auth_headers,
        )
        assert response.status_code == 200

    def test_image_proxy(self) -> None:
        """Test image proxy functionality."""
        response = requests.get(
            f"{self.base_url}/image_proxy",
            headers=self.auth_headers,
        )
        # Should return 400 as no image URL is provided
        assert response.status_code == 400

    def test_opensearch_support(self) -> None:
        """Test OpenSearch configuration."""
        response = requests.get(f"{self.base_url}/opensearch.xml")
        assert response.status_code == 200
        assert "text/xml" in response.headers["Content-Type"]

    def test_preferences(self) -> None:
        """Test preferences functionality."""
        response = requests.get(
            f"{self.base_url}/preferences",
            headers=self.auth_headers,
        )
        assert response.status_code == 200

    def test_categories(self) -> None:
        """Test search categories."""
        params = {"q": "test", "category": "images", "format": "json"}
        response = requests.get(
            f"{self.base_url}/search",
            params=params,
            headers=self.auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_error_handling(self) -> None:
        """Test error handling."""
        # Test invalid format
        params = {"q": "test", "format": "invalid"}
        response = requests.get(
            f"{self.base_url}/search",
            params=params,
            headers=self.auth_headers,
        )
        assert response.status_code == 400

    def test_rate_limiting(self) -> None:
        """Test rate limiting functionality."""
        responses = []
        for _ in range(30):  # Make multiple rapid requests
            response = requests.get(
                f"{self.base_url}/search?q=test",
                headers=self.auth_headers,
            )
            responses.append(response)

        # Check if rate limiting kicks in
        assert any(r.status_code == 429 for r in responses), "Rate limiting not working"

    @pytest.mark.integration
    def test_farfalle_integration(self) -> None:
        """Test Farfalle integration."""
        farfalle_url = os.getenv("FARFALLE_URL", "http://100.110.141.34:3000")
        response = requests.get(
            f"{farfalle_url}/api/search/providers",
            headers=self.auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "searxng" in [p["id"] for p in data["providers"]]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
