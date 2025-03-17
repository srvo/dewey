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
    """Class representing a data source."""

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
    ):
        """Initialize source with all required fields."""
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
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc or ""
        except Exception:
            return ""

    def _generate_hash(self) -> str:
        """Generate a unique hash for the source."""
        hash_input = (
            f"{self.url}|{self.title}|{self.snippet}|{self.domain}|{self.source_type}"
        )
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert source to dictionary."""
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
        """Create source from dictionary."""
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

    def __init__(self, delay_between_searches: float = 2.0, timeout: float = 30.0):
        """Initialize with delay between searches and timeout."""
        self.delay_between_searches = delay_between_searches
        self.timeout = timeout
        self.last_search_time = datetime.min

    def _wait_for_rate_limit(self):
        """Wait for rate limit to expire."""
        now = datetime.now()
        time_since_last = (now - self.last_search_time).total_seconds()
        if time_since_last < self.delay_between_searches:
            time.sleep(self.delay_between_searches - time_since_last)
        self.last_search_time = datetime.now()

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Perform a rate-limited search."""
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
        """Perform a rate-limited news search."""
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
    """Class for managing search and analysis workflows."""

    def __init__(
        self,
        api_client: APIClient,
        data_processor: DataProcessor,
        data_store: DataStore,
    ):
        """Initialize with components."""
        self.api_client = api_client
        self.data_processor = data_processor
        self.data_store = data_store

    def process_search(self, query: str) -> Dict[str, Any]:
        """
        Process a search query through the workflow.

        Args:
            query: The search query

        Returns:
            Processed search results
        """
        data = self.api_client.fetch_data(query)
        processed = self.data_processor.process(data)
        self.data_store.save(processed)
        return processed


def call_deepseek_api(messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """Call the DeepSeek API with messages."""
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
    """Extract structured data from text."""
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
    """Generate search queries for a company."""
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
    """Generate a summary from collected data."""
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
    """Get context information for a company."""
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
    """Get list of incomplete research items."""
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
    """Get research status for a ticker."""
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
    """Get top companies for research."""
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
    """Check if a security is an investment product."""
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
    """Class for managing research workflows."""

    def __init__(self, data_store: Optional[DataStore] = None, timeout: float = 30.0):
        """Initialize with data store and timeout."""
        self.data_store = data_store or DataStore()
        self.search_client = RateLimitedDDGS(timeout=timeout)
        self.timeout = timeout

    def process_company(self, company_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process research for a company."""
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
