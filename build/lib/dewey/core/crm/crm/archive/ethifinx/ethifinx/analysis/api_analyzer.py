import asyncio

from ethifinx.research.engines.api_docs import APIDocEngine


class APIAnalyzer:
    """Analyzer for API documentation and capabilities."""

    def __init__(self):
        self.engine = APIDocEngine()

    async def analyze_api(self, api_name: str) -> dict:
        """Analyze a specific API's documentation and capabilities."""
        await self.engine.fetch_all_documentation()
        return await self.engine.get_commercial_usage_status(api_name)

    async def analyze_all_apis(self) -> dict:
        """Analyze all configured APIs."""
        results = {}
        await self.engine.fetch_all_documentation()

        for api_name in self.engine.api_configs:
            status = await self.engine.get_commercial_usage_status(api_name)
            results[api_name] = {
                "data_types": status["data_types"],
                "commercial_usage": status["commercial_usage"],
                "tier": status["tier"],
            }

        return results


async def main():
    analyzer = APIAnalyzer()
    print("Analyzing API documentation and available data types...\n")

    results = await analyzer.analyze_all_apis()

    # Print data types and usage status for each API
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


if __name__ == "__main__":
    asyncio.run(main())
