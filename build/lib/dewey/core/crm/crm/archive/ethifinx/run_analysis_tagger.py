#!/usr/bin/env python3

import asyncio
import os
from dotenv import load_dotenv
from ethifinx.research.workflows.analysis_tagger import AnalysisTaggingWorkflow
from ethifinx.research.engines.deepseek import DeepSeekEngine
from ethifinx.research.loaders.duckdb_loader import DuckDBLoader

async def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize components
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    
    engine = DeepSeekEngine(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    loader = DuckDBLoader()
    workflow = AnalysisTaggingWorkflow(engine=engine, loader=loader)
    
    # Process just 2 companies as a test
    async for result in workflow.process_companies_by_tick_range(1, 2):
        if "error" in result:
            print(f"Error processing {result['ticker']}: {result['error']}")
        else:
            print(f"Successfully processed {result['ticker']}")
            print(f"Tags: {result['tags']}")
            print(f"Summary: {result['summary']['key_findings']}\n")

if __name__ == "__main__":
    asyncio.run(main()) 