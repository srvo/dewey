from backend.schemas import SearchResponse, SearchResult
from backend.search.providers.base import SearchProvider
from tavily import TavilyClient


class TavilySearchProvider(SearchProvider):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.tavily = TavilyClient(api_key=self.api_key)

    async def search(self, query: str) -> SearchResponse:
        response = self.tavily.search(
            query=query,
            search_depth="basic",
            max_results=6,
            include_images=True,
        )

        if response is None:
            msg = "No response from Tavily"
            raise ValueError(msg)

        results = [
            SearchResult(
                title=result["title"],
                url=result["url"],
                content=result["content"],
            )
            for result in response["results"]
        ]
        return SearchResponse(results=results, images=response["images"])
