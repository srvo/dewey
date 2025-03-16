```python
#!/usr/bin/env python3

import asyncio
import os

from dotenv import load_dotenv

from engines.deepseek import DeepSeekEngine
from loaders.duckdb_loader import DuckDBLoader
from workflows.analysis_tagger import AnalysisTaggingWorkflow


def initialize_components() -> tuple[DeepSeekEngine, DuckDBLoader, AnalysisTaggingWorkflow]:
    """Initializes the DeepSeek engine, DuckDB loader, and analysis tagging workflow.

    Returns:
        A tuple containing the initialized engine, loader, and workflow.
    """
    engine = DeepSeekEngine(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    )
    loader = DuckDBLoader()
    workflow = AnalysisTaggingWorkflow(engine=engine, loader=loader)
    return engine, loader, workflow


async def process_results(workflow: AnalysisTaggingWorkflow, start_tick: int, end_tick: int) -> None:
    """Processes company data within a specified tick range and prints the results.

    Args:
        workflow: The AnalysisTaggingWorkflow instance.
        start_tick: The starting tick value.
        end_tick: The ending tick value.
    """
    async for result in workflow.process_companies_by_tick_range(start_tick, end_tick):
        if "error" in result:
            print(f"Error processing {result['ticker']}: {result['error']}")
        else:
            print(f"Successfully processed {result['ticker']}")
            print(f"Tags: {result['tags']}")
            print(f"Summary: {result['summary']['key_findings']}\n")


async def main() -> None:
    """Main function to load environment variables, initialize components, and process data."""
    load_dotenv()

    engine, loader, workflow = initialize_components()

    # Process companies in tick range 1-5 as an example
    await process_results(workflow, 1, 5)


if __name__ == "__main__":
    asyncio.run(main())
```
