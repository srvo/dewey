"""API client module."""

from typing import Any, Dict, Optional

import requests

from ethifinx.core.config import Config, config


class APIClient:
    """API client for making HTTP requests."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize API client.

        Args:
            config: Optional configuration instance. If not provided, uses global config.
        """
        self.config = config or config
        self.base_url = self.config.API_BASE_URL
        self.api_key = self.config.API_KEY

    def fetch_data(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fetch data from API endpoint.

        Args:
            endpoint: API endpoint path
            params: Optional query parameters

        Returns:
            API response data
        """
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"API request failed: {str(e)}")
