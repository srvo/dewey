"""Controversy Analyzer
==================

This script analyzes controversies related to entities using SearXNG and Farfalle API.
"""

import argparse
import asyncio
from datetime import datetime
from typing import Any, Optional

import httpx
from prefect import flow, task

from dewey.core.base_script import BaseScript


class ControversyAnalyzer(BaseScript):
    """Analyzes controversies related to entities."""

    def __init__(self) -> None:
        """Initializes the ControversyAnalyzer."""
        super().__init__(
            name="ControversyAnalyzer",
            description="Analyzes controversies related to entities using SearXNG.",
            config_section="controversy_analyzer",
        )
        self.searxng_url = self.get_config_value("searxng_url")
        self.logger.info("ControversyAnalyzer initialized")

    @task(retries=3, retry_delay_seconds=5)
    async def search_controversies(self, entity: str) -> list[dict]:
        """Search for controversies related to an entity using SearXNG.

        Args:
            entity: Name of the entity to analyze.

        Returns:
            A list of dictionaries containing search results.

        """
        async with httpx.AsyncClient() as client:
            # Search with specific controversy-related terms
            queries = [
                f"{entity} controversy",
                f"{entity} scandal",
                f"{entity} criticism",
                f"{entity} investigation",
            ]
            results = []

            for query in queries:
                try:
                    response = await client.get(
                        f"{self.searxng_url}/search",
                        params={"q": query, "format": "json"},
                        headers={"Accept": "application/json"},
                    )
                    if response.status_code == 200:
                        data = response.json()
                        results.extend(data.get("results", []))
                    else:
                        self.logger.warning(
                            f"Failed to search for {query}: {response.status_code}"
                        )
                except Exception as e:
                    self.logger.error(f"Error searching for {query}: {e}")

            return results

    @task(retries=3, retry_delay_seconds=5)
    async def analyze_sources(self, results: list[dict]) -> dict[str, list[dict]]:
        """Analyze and categorize sources of controversy information.

        Args:
            results: A list of dictionaries containing search results.

        Returns:
            A dictionary containing categorized sources.

        """
        sources: dict[str, list[dict]] = {
            "news": [],
            "social_media": [],
            "regulatory": [],
            "academic": [],
            "other": [],
        }

        for result in results:
            try:
                category = await self.categorize_source(result.get("url", ""))
                if category:
                    sources[category].append(result)
            except Exception as e:
                self.logger.error(f"Error analyzing source {result.get('url')}: {e}")

        return sources

    @task
    async def categorize_source(self, url: str) -> Optional[str]:
        """Categorize a source based on its URL.

        Args:
            url: The URL of the source.

        Returns:
            The category of the source, or None if it cannot be categorized.

        """
        try:
            if not url:
                return None

            # News sites
            if any(
                domain in url.lower()
                for domain in ["news", "reuters", "bloomberg", "wsj", "ft.com"]
            ):
                return "news"

            # Social media
            if any(
                domain in url.lower() for domain in ["twitter", "linkedin", "facebook"]
            ):
                return "social_media"

            # Regulatory
            if any(domain in url.lower() for domain in ["gov", "sec.gov", "europa.eu"]):
                return "regulatory"

            # Academic
            if any(domain in url.lower() for domain in ["edu", "academia", "research"]):
                return "academic"

            return "other"
        except Exception as e:
            self.logger.error(f"Error categorizing URL {url}: {e}")
            return None

    @task
    async def summarize_findings(
        self, entity: str, sources: dict[str, list[dict]]
    ) -> dict[str, Any]:
        """Summarize findings about controversies.

        Args:
            entity: The entity being analyzed.
            sources: A dictionary containing categorized sources.

        Returns:
            A dictionary containing the summary of findings.

        """
        try:
            total_sources = sum(len(items) for items in sources.values())
            summary: dict[str, Any] = {
                "entity": entity,
                "analysis_date": datetime.now().isoformat(),
                "total_sources": total_sources,
                "source_breakdown": {
                    category: len(items) for category, items in sources.items()
                },
                "recent_controversies": [],
                "historical_controversies": [],
            }

            # Process each source category
            for category, items in sources.items():
                for item in items:
                    controversy = {
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "source_type": category,
                        "date": item.get("published_date"),
                        "snippet": item.get("content"),
                    }

                    # Categorize as recent or historical
                    if item.get("published_date", "").startswith(
                        str(datetime.now().year)
                    ):
                        summary["recent_controversies"].append(controversy)
                    else:
                        summary["historical_controversies"].append(controversy)

            return summary
        except Exception as e:
            self.logger.error(f"Error summarizing findings for {entity}: {e}")
            return {
                "entity": entity,
                "error": str(e),
                "analysis_date": datetime.now().isoformat(),
            }

    @flow(name="controversy-analysis")
    async def analyze_entity_controversies(
        self, entity: str, lookback_days: int = 365
    ) -> dict[str, Any]:
        """Analyze controversies for a given entity.

        Args:
            entity: Name of the entity to analyze.
            lookback_days: Number of days to look back for controversies.

        Returns:
            Dictionary containing analysis results.

        """
        try:
            self.logger.info(f"Starting controversy analysis for {entity}")

            # Search for controversies
            results = await self.search_controversies(entity)
            self.logger.info(f"Found {len(results)} potential controversy sources")

            # Analyze and categorize sources
            sources = await self.analyze_sources(results)
            self.logger.info(
                f"Categorized sources: {', '.join(f'{k}: {len(v)}' for k, v in sources.items())}"
            )

            # Summarize findings
            summary = await self.summarize_findings(entity, sources)
            self.logger.info(f"Analysis complete for {entity}")

            return summary
        except Exception as e:
            self.logger.error(f"Error analyzing controversies for {entity}: {e}")
            return {
                "entity": entity,
                "error": str(e),
                "analysis_date": datetime.now().isoformat(),
            }

    def run(self, args: argparse.Namespace) -> dict[str, Any]:
        """Main execution method.

        Args:
            args: Parsed command-line arguments.

        Returns:
            A dictionary containing the analysis results.

        """
        entity = args.entity
        lookback_days = args.lookback_days or 365

        self.logger.info(f"Running controversy analysis for {entity}")
        result = asyncio.run(self.analyze_entity_controversies(entity, lookback_days))
        self.logger.info(
            f"Analysis complete: found {len(result.get('recent_controversies', []))} recent controversies"
        )
        return result

    def execute(self) -> None:
        """Execute the controversy analysis."""
        parser = argparse.ArgumentParser(description="Analyze controversies for an entity")
        parser.add_argument("entity", help="Name of the entity to analyze")
        parser.add_argument("--lookback-days", type=int, help="Number of days to look back")

        args = parser.parse_args()
        entity = args.entity
        lookback_days = args.lookback_days or 365

        self.logger.info(f"Running controversy analysis for {entity}")
        result = asyncio.run(self.analyze_entity_controversies(entity, lookback_days))
        self.logger.info(
            f"Analysis complete: found {len(result.get('recent_controversies', []))} recent controversies"
        )


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze controversies for an entity")
    parser.add_argument("entity", help="Name of the entity to analyze")
    parser.add_argument("--lookback-days", type=int, help="Number of days to look back")

    args = parser.parse_args()
    analyzer = ControversyAnalyzer()
    analyzer.run(args)


if __name__ == "__main__":
    main()
