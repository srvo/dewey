from api_manager import api_config, add_new_api, reset_query_counts, query_api
from database_manager import DatabaseManager
import logging
from typing import Dict, Any, Optional
import asyncio
import aiohttp

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepAnalysis:
    def __init__(self, db_path="api_logs.db"):
        """Initialize the DeepAnalysis class."""
        self.session = None
        self.db_manager = DatabaseManager(db_path)

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Async context manager exit."""
        await self.session.close()

    async def query_api(self, api_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Query an API from the api_config.

        Args:
            api_name: Name of the API to query
            params: Dictionary of parameters for the API request

        Returns:
            JSON response from the API or None if request fails
        """
        config = api_config.get(api_name)
        if not config:
            return {"error": f"API {api_name} not found in configuration."}

        # Check rate limit
        if config["queries_made"] >= config["rate_limit"]:
            return {"error": f"Rate limit exceeded for {api_name}. Please wait until the next reset."}

        try:
            headers = {"Authorization": f"Bearer {config['api_key']}"}
            async with self.session.get(config["endpoint"], params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    config["queries_made"] += 1
                
                    # Log the API call if db_manager is provided
                    if db_manager:
                        try:
                            db_manager.log_api_call(
                                api_name=api_name,
                                endpoint=config["endpoint"],
                                parameters=params,
                                response_status=response.status,
                                response_data=data
                            )
                        except Exception as e:
                            logger.error(f"Error logging API call: {str(e)}")
                
                    return data
                return {"error": f"API returned status {response.status}"}
        except Exception as e:
            return {"error": f"Error querying {api_name}: {str(e)}"}

    async def analyze_company(self, company_name: str) -> Dict[str, Any]:
        """
        Perform deep analysis of a company using multiple APIs.

        Args:
            company_name: Name of the company to analyze

        Returns:
            Dictionary containing analysis results from various sources
        """
        analysis_results = {}

        # Gather news data
        news_data = await query_api(
            "NewsAPI",
            {"q": company_name, "language": "en", "sortBy": "publishedAt"}
        )
        if news_data:
            articles = news_data.get("articles", [])
            if articles:
                analysis_results.append(
                    self.ui.accordion(
                        title=f"📰 News Articles ({len(articles)})",
                        content=[
                            self.ui.card(
                                self.ui.markdown(f"### {a['title']}\n\n{a['description']}\n\n[Read more]({a['url']})"),
                                style={"margin": "10px"}
                            ) for a in articles
                        ]
                    )
                )
            else:
                analysis_results.append(
                    self.ui.callout("No news articles found", kind="warn")
                )

        # Gather social media data
        twitter_data = await query_api(
            "TwitterAPI",
            {"query": company_name, "max_results": 10}
        )
        if twitter_data:
            analysis_results["tweets"] = twitter_data.get("data", [])

        # Gather financial data
        financial_data = await query_api(
            "AlphaVantageAPI",
            {"function": "OVERVIEW", "symbol": company_name}
        )
        if financial_data:
            analysis_results["financials"] = financial_data

        return analysis_results

    async def analyze_controversy(self, topic: str) -> Dict[str, Any]:
        """
        Analyze controversies related to a specific topic.

        Args:
            topic: Topic or company name to analyze controversies for

        Returns:
            Dictionary containing controversy analysis results
        """
        controversy_data = await query_api(
            "ControversyAPI",
            {"query": topic}
        )
        return controversy_data or {}

async def main():
    """Main function to demonstrate deep analysis capabilities."""
    async with DeepAnalysis() as analyzer:
        # Example: Analyze a company
        company_analysis = await analyzer.analyze_company("Apple")
        logger.info(f"Company Analysis Results: {company_analysis}")

        # Example: Analyze a controversy
        controversy_analysis = await analyzer.analyze_controversy("data privacy")
        logger.info(f"Controversy Analysis Results: {controversy_analysis}")

if __name__ == "__main__":
    asyncio.run(main())
