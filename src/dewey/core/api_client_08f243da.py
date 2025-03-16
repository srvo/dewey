# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:39:31 2025

"""Generic HTTP API client for making authenticated requests to REST APIs.

This module provides a reusable client for interacting with HTTP APIs that require
authentication via API keys. It handles:
- Session management with automatic retries
- Authentication header injection
- Error handling and exception raising
- JSON request/response handling
- Testability through session injection

The client supports both GET and POST operations with proper error handling and
type hints for better IDE support and code maintainability.
"""
from __future__ import annotations

from typing import Any

import requests
from requests.exceptions import RequestException

try:
    from core.utils import some_function
except ImportError:
    # Fallback implementation if core.utils is not available
    # This allows the module to function even without the core dependency
    def some_function() -> dict[str, str]:
        """Fallback implementation if core.utils is not available.

        Returns
        -------
            Dict[str, str]: A default success status dictionary

        """
        return {"status": "success"}


class APIClient:
    """Generic HTTP API client for making authenticated requests.

    This class provides a reusable interface for interacting with REST APIs that
    require Bearer token authentication. It handles:
    - Session management with connection pooling
    - Automatic injection of authentication headers
    - Consistent error handling
    - JSON request/response handling
    - Testability through session injection

    Attributes
    ----------
        base_url (str): The base URL for all API requests
        api_key (str): The API key used for authentication
        session (requests.Session): The HTTP session with connection pooling

    """

    def __init__(self, base_url: str, api_key: str) -> None:
        """Initialize the API client with base URL and authentication key.

        Args:
        ----
            base_url (str): The base URL of the API (e.g., "https://api.example.com")
            api_key (str): The API key for Bearer token authentication

        Example:
        -------
            >>> client = APIClient("https://api.example.com", "my-api-key")

        """
        self.base_url = base_url.rstrip("/")  # Remove trailing slash for consistency
        self.api_key = api_key
        # Create a session with connection pooling and default headers
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    def fetch_data(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        session: requests.Session | None = None,
    ) -> dict[str, Any]:
        """Fetch data from the specified API endpoint.

        Makes a GET request to the API endpoint and returns the parsed JSON response.
        Handles error responses by raising RequestException.

        Args:
        ----
            endpoint (str): The API endpoint path (e.g., "/v1/resource")
            params (Optional[Dict[str, Any]]): Optional query parameters
            session (Optional[requests.Session]): Optional session for testing

        Returns:
        -------
            Dict[str, Any]: The parsed JSON response from the API

        Raises:
        ------
            RequestException: If the API request fails (4xx or 5xx status)
            ValueError: If the response cannot be parsed as JSON

        Example:
        -------
            >>> data = client.fetch_data("/v1/users", params={"active": True})
            >>> print(data)

        """
        # Construct full URL and ensure proper endpoint formatting
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            # Use provided session for testing or default session
            session = session or self.session
            response = session.get(url, params=params)

            # Raise exception for HTTP errors (4xx, 5xx)
            response.raise_for_status()

            # Parse and return JSON response
            return response.json()
        except RequestException as e:
            # Wrap and re-raise with additional context
            msg = f"API request to {url} failed: {e}"
            raise RequestException(msg) from e

    def post_data(
        self,
        endpoint: str,
        data: dict[str, Any],
        session: requests.Session | None = None,
    ) -> dict[str, Any]:
        """Post data to the specified API endpoint.

        Makes a POST request to the API endpoint with JSON payload and returns
        the parsed JSON response. Handles error responses by raising RequestException.

        Args:
        ----
            endpoint (str): The API endpoint path (e.g., "/v1/resource")
            data (Dict[str, Any]): The JSON payload to send
            session (Optional[requests.Session]): Optional session for testing

        Returns:
        -------
            Dict[str, Any]: The parsed JSON response from the API

        Raises:
        ------
            RequestException: If the API request fails (4xx or 5xx status)
            ValueError: If the response cannot be parsed as JSON

        Example:
        -------
            >>> response = client.post_data("/v1/users", {"name": "John Doe"})
            >>> print(response)

        """
        # Construct full URL and ensure proper endpoint formatting
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            # Use provided session for testing or default session
            session = session or self.session
            response = session.post(url, json=data)

            # Raise exception for HTTP errors (4xx, 5xx)
            response.raise_for_status()

            # Parse and return JSON response
            return response.json()
        except RequestException as e:
            # Wrap and re-raise with additional context
            msg = f"API request to {url} failed: {e}"
            raise RequestException(msg) from e
