```python
import hashlib
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from sqlalchemy import text

from ..analysis.data_processor import DataProcessor
from ..core.api_client import APIClient
from ..core.config import Config
from ..db.data_store import DataStore, get_connection

logger = logging.getLogger(__name__)
config = Config()

CHECKPOINT_STAGES = {
    "INIT": 0,
    "SEARCH": 1,
    "ANALYSIS": 2,
    "COMPLETE": 3,
}


class Source:
    """Represents a data source."""

    def __init__(
        self,
        url: str,
        title: str = "",
        snippet: str = "",
        domain: str = "",
        source_type: str = "web",
        category: str = "",
        query_context: str = "",
        retrieved_at: str = "",
        reliability: float = 1.0,
    ) -> None:
        """Initializes a Source object.

        Args:
            url: The URL of the source.
            title: The title of the source.
            snippet: A snippet of text from the source.
            domain: The domain of the source.
            source_type: The type of source (default: "web").
            category: The category of the source.
            query_context: The context of the query that retrieved the source.
            retrieved_at: The timestamp when the source was retrieved.
            reliability: A measure of the source's reliability (default: 1.0).
        """
        self.url = url
        self.title = title
        self.snippet = snippet
        self.domain = domain or self._extract_domain(url)
        self.source_type = source_type
        self.category = category
        self.query_context = query_context
        self.retrieved_at = retrieved_at
        self.reliability = min(max(reliability, 0.0), 1.0)
        self.source_hash = self._generate_hash()

    def _extract_domain(self, url: str) -> str:
        """Extracts the domain from a URL.

        Args:
            url: The URL to extract the domain from.

        Returns:
            The domain of the URL, or an empty string if extraction fails.
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc or ""
        except Exception:
            return ""

    def _generate_hash(self) -> str:
        """Generates a unique hash for the source.

        Returns:
            A SHA256 hash of the source's key attributes.
        """
        hash_input = (
            f"{self.url}|{self.title}|{self.snippet}|{self.domain}|{self.source_type}"
        )
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Converts the source to a dictionary.

        Returns:
            A dictionary representation of the source.
        """
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "domain": self.domain,
            "source_type": self.source_type,
            "category": self.category,
            "query_context": self.query_context,
            "retrieved_at": self.retrieved_at,
            "reliability": self.reliability,
            "source_hash": self.source_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Source":
        """Creates a Source object from a dictionary.

        Args:
            data: A dictionary containing the source's attributes.

        Returns:
            A Source object created from the dictionary.
        """
        return cls(
            url=data["url"],
            title=data.get("title", ""),
            snippet=data.get("snippet", ""),
            domain=data.get("domain", ""),
            source_type=data.get("source_type", "web"),
            category=data.get("category", ""),
            query_context=data.get("query_context", ""),
            retrieved_at=data.get("retrieved_at", ""),
            reliability=data.get("reliability", 1.0),
        )


class RateLimitedDDGS:
    """Rate-limited DuckDuckGo search client."""

    def __init__(self, delay_between_searches: float = 2.0, timeout: float = 30.0) -> None:
        """Initializes the RateLimitedDDGS client.

        Args:
            delay_between_searches: The delay in seconds between searches (default: 2.0).
            timeout: The timeout in seconds for each search request (default: 30.0).
        """
        self.delay_between_searches = delay_between_searches
        self.timeout = timeout
        self.last_search_time = datetime.min

    def _wait_for_rate_limit(self) -> None:
        """Waits for the rate limit to expire before making a search request."""
        now = datetime.now()
        time_since_last = (now - self.last_search_time).total_seconds()
        if time_since_last < self.delay_between_searches:
            time.sleep(self.delay_between_searches - time_since_last)
        self.last_search_time = datetime.now()

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Performs a rate-limited search.

        Args:
            query: The search query.

        Returns:
            A list of dictionaries, where each dictionary represents a search result.
        """
        self._wait_for_rate_limit()
        try:
            # Mock search result for testing
            return [
                {
                    "title": "Test",
                    "link": "https://example.com",
                    "body": "Test body",
                }
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def news_search(self, query: str) -> List[Dict[str, Any]]:
        """Performs a rate-limited news search.

        Args:
            query: The search query.

        Returns:
            A list of dictionaries, where each dictionary represents a news search result.
        """
        self._wait_for_rate_limit()
        try:
            # Mock news search result for testing
            return [
                {
                    "title": "Test News",
                    "link": "https://example.com/news",
                    "body": "Test news body",
                    "date": datetime.now().isoformat(),
                }
            ]
        except Exception as e:
            logger.error(f"News search failed: {e}")
            return []


class SearchFlow:
    """Manages search and analysis workflows."""

    def __init__(
        self,
        api_client: APIClient,
        data_processor: DataProcessor,
        data_store: DataStore,
    ) -> None:
        """Initializes the SearchFlow object.

        Args:
            api_client: An APIClient object for fetching data.
            data_processor: A DataProcessor object for processing data.
            data_store: A DataStore object for saving data.
        """
        self.api_client = api_client
        self.data_processor = data_processor
        self.data_store = data_store

    def process_search(self, query: str) -> Dict[str, Any]:
        """Processes a search query through the workflow.

        Args:
            query: The search query.

        Returns:
            The processed search results.
        """
        data = self.api_client.fetch_data(query)
        processed = self.data_processor.process(data)
        self.data_store.save(processed)
        return processed


def call_deepseek_api(messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """Calls the DeepSeek API with a list of messages.

    Args:
        messages: A list of dictionaries, where each dictionary represents a message.

    Returns:
        The JSON response from the DeepSeek API, or None if the API call fails.
    """
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            json={"messages": messages},
            headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None


def extract_structured_data(text: str) -> Dict[str, Any]:
    """Extracts structured data from text using the DeepSeek API.

    Args:
        text: The text to extract structured data from.

    Returns:
        A dictionary containing the extracted structured data, or None if extraction fails.
    """
    try:
        # Call DeepSeek API to extract structured data
        messages = [
            {
                "role": "system",
                "content": "Extract structured data from the following text.",
            },
            {"role": "user", "content": text},
        ]
        response = call_deepseek_api(messages)
        if response and "choices" in response:
            return {"structured": response["choices"][0]["message"]["content"]}
    except Exception as e:
        logger.error(f"Failed to extract structured data: {e}")
    return {"structured": None}


def generate_search_queries(company_info: Dict[str, str]) -> List[Dict[str, Any]]:
    """Generates search queries for a company using the DeepSeek API.

    Args:
        company_info: A dictionary containing information about the company.

    Returns:
        A list of search queries generated for the company.
    """
    try:
        messages = [
            {
                "role": "system",
                "content": "Generate search queries for ESG research on a company.",
            },
            {"role": "user", "content": json.dumps(company_info)},
        ]
        response = call_deepseek_api(messages)
        if not response:
            raise ValueError("Empty API response")
        if "choices" not in response:
            raise KeyError("Missing 'choices' in API response")
        if not response["choices"]:
            raise ValueError("Empty choices in API response")
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to generate search queries: {str(e)}")
        raise


def generate_summary(data: List[Dict[str, Any]]) -> str:
    """Generates a summary from a list of data items using the DeepSeek API.

    Args:
        data: A list of dictionaries containing the data to summarize.

    Returns:
        A summary of the data.
    """
    try:
        # Call DeepSeek API to generate summary
        content = "\n".join(str(item) for item in data)
        messages = [
            {
                "role": "system",
                "content": "Generate a concise summary of the following data.",
            },
            {"role": "user", "content": content},
        ]
        response = call_deepseek_api(messages)
        if response and "choices" in response:
            return response["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
    return "Failed to generate summary"


def get_company_context(ticker: str) -> str:
    """Retrieves context information for a company from the database.

    Args:
        ticker: The ticker symbol of the company.

    Returns:
        The context information for the company.
    """
    try:
        with get_connection() as conn:
            result = conn.execute(
                text("SELECT context FROM company_context WHERE ticker = :ticker"),
                {"ticker": ticker},
            ).fetchone()
            return result[0] if result else ""
    except Exception as e:
        logger.error(f"Failed to get company context: {e}")
        raise


def get_incomplete_research() -> List[Dict[str, Any]]:
    """Retrieves a list of incomplete research items from the database.

    Returns:
        A list of dictionaries, where each dictionary represents an incomplete research item.
    """
    try:
        with get_connection() as conn:
            result = conn.execute(
                text("SELECT * FROM research WHERE status != 'COMPLETE'")
            ).fetchall()
            return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"Failed to get incomplete research: {e}")
        return []


def get_research_status(ticker: str) -> Dict[str, Any]:
    """Retrieves the research status for a given ticker symbol from the database.

    Args:
        ticker: The ticker symbol of the company.

    Returns:
        A dictionary containing the research status and stage for the ticker.
    """
    try:
        with get_connection() as conn:
            result = conn.execute(
                text("SELECT status, stage FROM research WHERE ticker = :ticker"),
                {"ticker": ticker},
            ).fetchone()
            return dict(result) if result else {"status": "NOT_FOUND", "stage": None}
    except Exception as e:
        logger.error(f"Failed to get research status: {e}")
        return {"status": "ERROR", "stage": None}


def get_top_companies(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves a list of the top companies from the database, ordered by market capitalization.

    Args:
        limit: The maximum number of companies to retrieve (default: 100).

    Returns:
        A list of dictionaries, where each dictionary represents a company.
    """
    try:
        with get_connection() as conn:
            result = conn.execute(
                text("SELECT * FROM companies ORDER BY market_cap DESC LIMIT :limit"),
                {"limit": limit},
            ).fetchall()
            return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"Failed to get top companies: {e}")
        raise


def is_investment_product(
    name: str, ticker: str, description: Optional[str] = None
) -> Dict[str, Any]:
    """Checks if a security is an investment product based on its name, ticker, and description.

    Args:
        name: The name of the security.
        ticker: The ticker symbol of the security.
        description: An optional description of the security.

    Returns:
        A dictionary containing a boolean indicating whether the security is an investment product,
        a confidence score, and a list of matches that contributed to the confidence score.
    """
    matches = []
    confidence = 0

    # Check name and ticker for common investment product indicators
    indicators = ["ETF", "Fund", "Trust", "Index", "Portfolio", "Preferred", "Series"]

    # Higher weight for name matches
    for indicator in indicators:
        if indicator.lower() in name.lower():
            matches.append(indicator)
            confidence += 25  # Increased from 15

    # Check description if available
    if description:
        for indicator in indicators:
            if indicator.lower() in description.lower():
                matches.append(f"{indicator} (desc)")
                confidence += 15  # Increased from 10

    # Check for preferred share pattern in ticker
    if "PR" in ticker and len(ticker) > 2:
        matches.append("PR[A-Z]")
        confidence += 25  # Increased from 20

    # Additional checks for specific patterns
    if "trust" in name.lower():
        matches.append("Trust (name)")
        confidence += 25

    if "fund" in name.lower():
        matches.append("Fund (name)")
        confidence += 25

    return {
        "is_investment_product": confidence >= 25,  # Lowered threshold
        "confidence": min(confidence, 100),
        "matches": matches,
    }


class ResearchWorkflow:
    """Manages research workflows for companies."""

    def __init__(self, data_store: Optional[DataStore] = None, timeout: float = 30.0) -> None:
        """Initializes the ResearchWorkflow object.

        Args:
            data_store: An optional DataStore object for saving data.
            timeout: The timeout in seconds for search requests.
        """
        self.data_store = data_store or DataStore()
        self.search_client = RateLimitedDDGS(timeout=timeout)
        self.timeout = timeout

    def process_company(self, company_info: Dict[str, Any]) -> Dict[str, Any]:
        """Processes research for a given company.

        Args:
            company_info: A dictionary containing information about the company.

        Returns:
            A dictionary containing the research results for the company.
        """
        try:
            # Get existing context
            context = get_company_context(company_info)

            # Generate and process search queries
            queries = generate_search_queries(company_info)
            search_results = []

            for query in queries:
                self.search_client._wait_for_rate_limit()
                result = extract_structured_data(query)
                if result.get("structured"):
                    search_results.append(result)

            # Generate summary
            summary = generate_summary(search_results)

            # Save results
            result = {
                "ticker": company_info["ticker"],
                "name": company_info["name"],
                "context": context,
                "search_results": search_results,
                "summary": summary,
                "status": "COMPLETE",
                "stage": CHECKPOINT_STAGES["COMPLETE"],
                "updated_at": datetime.now().isoformat(),
            }

            if self.data_store:
                self.data_store.save(result)
            return result

        except Exception as e:
            logger.error(f"Failed to process company {company_info['ticker']}: {e}")
            return {
                "ticker": company_info["ticker"],
                "status": "ERROR",
                "error": str(e),
                "stage": CHECKPOINT_STAGES["INIT"],
            }
```
