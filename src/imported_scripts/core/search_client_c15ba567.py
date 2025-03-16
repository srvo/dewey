from __future__ import annotations

import aiohttp


class EnhancedSearchClient:
    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.session = aiohttp.ClientSession()

    async def search(self, query: str, provider: str = "searxng"):
        """Perform actual search using Farfalle API."""
        try:
            async with self.session.post(
                f"{self.base_url}/api/search",
                json={"query": query, "provider": provider, "mode": "expert"},
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {"error": f"Search failed with status {response.status}"}
        except Exception as e:
            return {"error": str(e)}

    async def close(self) -> None:
        await self.session.close()
