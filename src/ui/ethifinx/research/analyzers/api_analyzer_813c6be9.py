from dewey.core.base_script import BaseScript

import asyncio
from typing import Dict, Any

from ethifinx.research.engines.api_docs import APIDocEngine


class APIAnalyzer:
    """Analyzer for API documentation and capabilities."""

    def __init__(self) -> None:
        """Initializes the APIAnalyzer with an APIDocEngine."""
        self.engine = APIDocEngine()

    async def analyze_api(self, api_name: str) -> dict[str, Any]:
        """Analyzes a specific API's documentation and capabilities.

        Args:
            api_name: The name of the API to analyze.

        Returns:
            A dictionary containing the analysis results.

        """
        await self.engine.fetch_all_documentation()
        return await self.engine.get_commercial_usage_status(api_name)

    async def analyze_all_apis(self) -> dict[str, dict[str, Any]]:
        """Analyzes all configured APIs.

        Returns:
            A dictionary where keys are API names and values are dictionaries
            containing data types, commercial usage status, and tier information.

        """
        await self.engine.fetch_all_documentation()
        results: dict[str, dict[str, Any]] = {}

        for api_name in self.engine.api_configs:
            status = await self.engine.get_commercial_usage_status(api_name)
            results[api_name] = {
                "data_types": status["data_types"],
                "commercial_usage": status["commercial_usage"],
                "tier": status["tier"],
            }

        return results


async def print_api_analysis_results(results: dict[str, dict[str, Any]]) -> None:
    """Prints the analysis results for each API.

    Args:
        results: A dictionary containing the analysis results for each API.

    """
    for api_name, status in results.items():
        print(f"\n=== {api_name} ===")
        print("Data Types:")
        if status["data_types"]:
            print("  Categories:", ", ".join(status["data_types"]["categories"]))
            print("  Fields:", ", ".join(status["data_types"]["fields"]))
            print("  Formats:", ", ".join(status["data_types"]["formats"]))
            print(
                "  Special Features:",
                ", ".join(status["data_types"]["special_features"]),
            )
        else:
            print("  No data type information available")
        print(f"Commercial Usage: {status['commercial_usage']}")
        print(f"Tier: {status['tier']}")
        print("-" * 50)


async def main() -> None:
    """Main function to analyze APIs and print results."""
    analyzer = APIAnalyzer()
    print("Analyzing API documentation and available data types...\n")

    results = await analyzer.analyze_all_apis()
    await print_api_analysis_results(results)


if __name__ == "__main__":
    asyncio.run(main())
