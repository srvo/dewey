```python
#!/usr/bin/env python3

import asyncio
import os

from dotenv import load_dotenv

from ethifinx.research.engines.deepseek import DeepSeekEngine
from ethifinx.research.loaders.duckdb_loader import DuckDBLoader
from ethifinx.research.workflows.analysis_tagger import AnalysisTaggingWorkflow


def initialize_components() -> tuple[DeepSeekEngine, DuckDBLoader, AnalysisTaggingWorkflow]:
    """Initializes the DeepSeek engine, DuckDB loader, and AnalysisTagging workflow.

    Returns:
        A tuple containing the initialized DeepSeekEngine, DuckDBLoader, and AnalysisTaggingWorkflow.
    """
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    engine = DeepSeekEngine(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    loader = DuckDBLoader()
    workflow = AnalysisTaggingWorkflow(engine=engine, loader=loader)
    return engine, loader, workflow


async def process_companies(workflow: AnalysisTaggingWorkflow, start_tick: int, end_tick: int) -> None:
    """Processes companies by tick range and prints the results.

    Args:
        workflow: The AnalysisTaggingWorkflow to use for processing.
        start_tick: The starting tick.
        end_tick: The ending tick.
    """
    async for result in workflow.process_companies_by_tick_range(start_tick, end_tick):
        if "error" in result:
            print(f"Error processing {result['ticker']}: {result['error']}")
        else:
            print(f"Successfully processed {result['ticker']}")
            print(f"Tags: {result['tags']}")
            print(f"Summary: {result['summary']['key_findings']}\n")


async def main() -> None:
    """Main function to initialize components and process companies."""
    _, _, workflow = initialize_components()
    await process_companies(workflow, 1, 2)


if __name__ == "__main__":
    asyncio.run(main())
```
