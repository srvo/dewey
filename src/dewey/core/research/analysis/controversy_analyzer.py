"""
Controversy Analyzer
==================

This script analyzes controversies related to entities using SearXNG and Farfalle API.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import httpx
from prefect import flow, task

from dewey.core.base_script import BaseScript


class ControversyAnalyzer(BaseScript):
    """Analyzes controversies related to entities."""

    def __init__(self):
        super().__init__()
        self.logger = self.get_logger()
        self.config = self.get_config()
        self.farfalle_api_url = self.config.settings.farfalle_api_url
        self.searxng_url = self.config.settings.searxng_url

    @task(retries=3, retry_delay_seconds=5)
    async def search_controversies(self, entity: str) -> list[dict]:
        """Search for controversies related to an entity using SearXNG."""
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
                        self.logger.warning(f"Failed to search for {query}: {response.status_code}")
                except Exception as e:
                    self.logger.error(f"Error searching for {query}: {e}")

            return results

    @task(retries=2)
    async def analyze_sources(self, results: list[dict]) -> dict:
        """Analyze and categorize sources of controversy information."""
        sources = {
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
        """Categorize a source based on its URL."""
        try:
            if not url:
                return None

            # News sites
            if any(domain in url.lower() for domain in ["news", "reuters", "bloomberg", "wsj", "ft.com"]):
                return "news"

            # Social media
            if any(domain in url.lower() for domain in ["twitter", "linkedin", "facebook"]):
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
    async def summarize_findings(self, entity: str, sources: dict) -> dict:
        """Summarize findings about controversies."""
        try:
            total_sources = sum(len(items) for items in sources.values())
            summary = {
                "entity": entity,
                "analysis_date": datetime.now().isoformat(),
                "total_sources": total_sources,
                "source_breakdown": {
                    category: len(items)
                    for category, items in sources.items()
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
                    if item.get("published_date", "").startswith(str(datetime.now().year)):
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
    async def analyze_entity_controversies(self, entity: str, lookback_days: int = 365) -> dict:
        """Analyze controversies for a given entity.

        Args:
            entity: Name of the entity to analyze
            lookback_days: Number of days to look back for controversies

        Returns:
            Dictionary containing analysis results
        """
        try:
            self.logger.info(f"Starting controversy analysis for {entity}")
            
            # Search for controversies
            results = await self.search_controversies(entity)
            self.logger.info(f"Found {len(results)} potential controversy sources")

            # Analyze and categorize sources
            sources = await self.analyze_sources(results)
            self.logger.info(f"Categorized sources: {', '.join(f'{k}: {len(v)}' for k, v in sources.items())}")

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

    def run(self, args):
        """Main execution method."""
        import asyncio
        
        entity = args.entity
        lookback_days = args.lookback_days or 365
        
        self.logger.info(f"Running controversy analysis for {entity}")
        result = asyncio.run(self.analyze_entity_controversies(entity, lookback_days))
        self.logger.info(f"Analysis complete: found {len(result.get('recent_controversies', []))} recent controversies")
        return result


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze controversies for an entity")
    parser.add_argument("entity", help="Name of the entity to analyze")
    parser.add_argument("--lookback-days", type=int, help="Number of days to look back")
    
    args = parser.parse_args()
    analyzer = ControversyAnalyzer()
    analyzer.run(args)


if __name__ == "__main__":
    main()
