"""Analysis Tagging Workflow

A workflow for tagging and analyzing company information.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List
from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)


class AnalysisTaggingWorkflow:
    """Workflow for analyzing companies and generating tags."""

    def __init__(self, engine):
        """Initialize the analysis tagging workflow.

        Args:
            engine: The engine to use for analysis.

        """
        self.engine = engine

    async def process_companies_by_tickers(
        self, tickers: list[str]
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Process a list of company tickers.

        Args:
            tickers: List of company ticker symbols

        Yields:
            Analysis results for each company

        """
        for ticker in tickers:
            # Get basic company info (in a real implementation, this would fetch from a database)
            company_data = self._get_mock_company_data(ticker)

            try:
                # Analyze the company
                analysis_result = await self.engine.analyze_company(company_data)

                # Extract the analysis data
                if analysis_result.get("success", False):
                    tags = analysis_result.get("analysis", {}).get("tags", {})
                    summary = analysis_result.get("analysis", {}).get("summary", {})

                    result = {
                        "ticker": ticker,
                        "name": company_data.get("name", "Unknown"),
                        "tags": tags,
                        "summary": summary,
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    # Error occurred during analysis
                    result = {
                        "ticker": ticker,
                        "name": company_data.get("name", "Unknown"),
                        "error": analysis_result.get("error", "Unknown error"),
                        "timestamp": datetime.now().isoformat(),
                    }

                yield result
            except Exception as e:
                logger.error(f"Error processing company {ticker}: {str(e)}")
                yield {
                    "ticker": ticker,
                    "name": company_data.get("name", "Unknown"),
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }

    def _get_mock_company_data(self, ticker: str) -> dict[str, Any]:
        """Get mock company data for the given ticker.

        In a real implementation, this would fetch from a database.

        Args:
            ticker: Company ticker symbol

        Returns:
            Dictionary containing company information

        """
        # Mock company data mapping
        companies = {
            "AAPL": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
            },
            "MSFT": {
                "ticker": "MSFT",
                "name": "Microsoft Corporation",
                "description": "Microsoft Corporation develops, licenses, and supports software, services, devices, and solutions worldwide.",
                "sector": "Technology",
                "industry": "Software—Infrastructure",
            },
            "GOOGL": {
                "ticker": "GOOGL",
                "name": "Alphabet Inc.",
                "description": "Alphabet Inc. provides various products and platforms in the United States, Europe, the Middle East, Africa, the Asia-Pacific, Canada, and Latin America.",
                "sector": "Technology",
                "industry": "Internet Content & Information",
            },
            "AMZN": {
                "ticker": "AMZN",
                "name": "Amazon.com, Inc.",
                "description": "Amazon.com, Inc. engages in the retail sale of consumer products and subscriptions in North America and internationally.",
                "sector": "Consumer Cyclical",
                "industry": "Internet Retail",
            },
            "TSLA": {
                "ticker": "TSLA",
                "name": "Tesla, Inc.",
                "description": "Tesla, Inc. designs, develops, manufactures, leases, and sells electric vehicles, and energy generation and storage systems in the United States, China, and internationally.",
                "sector": "Consumer Cyclical",
                "industry": "Auto Manufacturers",
            },
        }

        # Return the company data if it exists, otherwise create a generic entry
        return companies.get(
            ticker,
            {
                "ticker": ticker,
                "name": f"{ticker} Corporation",
                "description": f"A company with the ticker symbol {ticker}.",
                "sector": "Unknown",
                "industry": "Unknown",
            },
        )
