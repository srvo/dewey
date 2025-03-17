#!/usr/bin/env python3

import asyncio
import os
from dotenv import load_dotenv
from workflows.analysis_tagger import AnalysisTaggingWorkflow
from engines.deepseek import DeepSeekEngine
from loaders.duckdb_loader import DuckDBLoader

async def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize components
    engine = DeepSeekEngine(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    )
    loader = DuckDBLoader()
    workflow = AnalysisTaggingWorkflow(engine=engine, loader=loader)
    
    # Process companies in tick range 1-5 as an example
    async for result in workflow.process_companies_by_tick_range(1, 5):
        if "error" in result:
            print(f"Error processing {result['ticker']}: {result['error']}")
        else:
            print(f"Successfully processed {result['ticker']}")
            print(f"Tags: {result['tags']}")
            print(f"Summary: {result['summary']['key_findings']}\n")

if __name__ == "__main__":
    asyncio.run(main()) 