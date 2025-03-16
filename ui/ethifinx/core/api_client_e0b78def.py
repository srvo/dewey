# Formatting failed: LLM generation failed: Gemini API error: Could not acquire rate limit slot for gemini-2.0-flash after 3 attempts

"""API client module."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import requests

if TYPE_CHECKING:
    from ethifinx.core.config import Config


class APIClient:
    """API client for making HTTP requests."""

    def __init__(self, config: Config | None = None) -> None:
        """Initialize API client.

        Args:
        ----
            config: Optional configuration instance. If not provided, uses global config.

        """
        self.config = config or config
        self.base_url = self.config.API_BASE_URL
        self.api_key = self.config.API_KEY

    def fetch_data(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fetch data from API endpoint.

        Args:
        ----
            endpoint: API endpoint path
            params: Optional query parameters

        Returns:
        -------
            API response data

        """
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            msg = f"API request failed: {e!s}"
            raise Exception(msg)
