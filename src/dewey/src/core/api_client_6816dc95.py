# Formatting failed: LLM generation failed: Gemini API error: Could not acquire rate limit slot for gemini-2.0-flash after 3 attempts

"""TUI API client with retry logic and connection pooling."""

import asyncio
from typing import Any

import httpx

from ..core.config import get_settings


class APIClient:
    """Robust API client with automatic retries and rate limiting."""

    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    POOL_LIMITS = httpx.PoolLimits(soft=10, hard=100, max_keepalive=30)

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = (
            f"http://{self.settings.api_host}:{self.settings.api_port}/api/v1"
        )
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=self.POOL_LIMITS,
            transport=httpx.AsyncHTTPTransport(retries=self.MAX_RETRIES),
        )

    async def close(self) -> None:
        """Graceful shutdown with connection cleanup."""
        await self.client.aclose()

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """Retryable request handler with exponential backoff."""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self.client.request(
                    method,
                    f"{self.base_url}{path}",
                    **kwargs,
                )
                response.raise_for_status()
                return response
            except (httpx.RequestError, httpx.HTTPStatusError):
                if attempt == self.MAX_RETRIES - 1:
                    raise

                delay = self.RETRY_DELAY * (2**attempt)
                logger.warning(
                    f"Retrying {method} {path} in {delay}s... (attempt {attempt+1})",
                )
                await asyncio.sleep(delay)

        msg = f"Request failed after {self.MAX_RETRIES} retries"
        raise httpx.HTTPError(msg)

    # API methods using retryable request handler
    async def get_companies(
        self,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "ticker",
        sort_order: str = "asc",
    ) -> dict[str, Any]:
        params = {
            "page": page,
            "per_page": per_page,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }
        response = await self._request_with_retry("GET", "/companies", params=params)
        return response.json()

    # Remaining API methods follow same pattern with retry support

    async def validate_connection(self) -> bool:
        """Check API availability with health check."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except httpx.RequestError:
            return False
