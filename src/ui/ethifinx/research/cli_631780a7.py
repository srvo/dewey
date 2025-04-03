import asyncio
import logging
import os
from typing import List, Optional

import click

from ethifinx.research.engines.deepseek import DeepSeekEngine
from ethifinx.research.search_flow import (
    ResearchWorkflow,
    get_research_status,
    get_top_companies,
)
from ethifinx.research.workflows.analysis_tagger import AnalysisTaggingWorkflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("research_workflow.log"), logging.StreamHandler()],
)


def print_analysis_result(result: dict) -> None:
    """Print analysis result in a readable format.

    Args:
        result (dict): The analysis result dictionary.

    """
    if "error" in result:
        logging.error(f"❌ Error processing {result['ticker']}: {result['error']}")
    else:
        logging.info(f"✅ {result['ticker']}:")
        logging.info(f"  Risk: {result['tags']['concern_level']}/5")
        logging.info(f"  Confidence: {result['tags']['confidence_score']:.2f}")
        logging.info(f"  Themes: {', '.join(result['tags']['primary_themes'][:3])}")
        logging.info(f"  Recommendation: {result['summary']['recommendation']}\n")


@click.group()
def research():
    """Research commands for analyzing companies."""
    pass


@research.command()
@click.option("--limit", default=150, help="Number of companies to research")
@click.option("--timeout", default=30, help="Timeout for API calls")
def run(limit: int, timeout: int):
    """Run research workflow on top companies.

    Args:
        limit (int): Number of companies to research.
        timeout (int): Timeout for API calls.

    """
    logging.info("Starting research workflow")

    companies = get_top_companies(limit=limit)
    logging.info(f"Retrieved {len(companies)} companies to research")

    workflow = ResearchWorkflow(timeout=timeout)

    for company in companies:
        logging.info(f"Processing {company['name']} ({company['ticker']})")
        result = workflow.research_company(company)
        if result:
            logging.info(f"Successfully processed {company['name']}")
            logging.info(f"Risk score: {result['structured_data'].get('risk_score')}")
            logging.info(
                f"Recommendation: {result['structured_data'].get('recommendation')}"
            )
        else:
            logging.error(f"Failed to process {company['name']}")

    status = get_research_status()
    logging.info("Research workflow status:")
    logging.info(f"Total companies: {status['total']}")
    logging.info(f"Completed: {status['completed']}")
    logging.info(f"In progress: {status['in_progress']}")
    logging.info(f"Failed: {status['failed']}")
    logging.info(f"Not started: {status['not_started']}")
    logging.info(f"Completion percentage: {status['completion_percentage']:.2f}%")


@research.command()
@click.option("--tickers", help="Comma-separated list of tickers to analyze")
@click.option("--tick-range", help="Tick range to analyze (min-max)")
@click.option("--limit", type=int, help="Limit number of companies to process")
def analyze(tickers: str | None, tick_range: str | None, limit: int | None):
    """Run analysis tagger on specified companies.

    Args:
        tickers (Optional[str]): Comma-separated list of tickers.
        tick_range (Optional[str]): Tick range to analyze (min-max).
        limit (Optional[int]): Limit number of companies to process.

    """

    async def run_analysis():
        """Asynchronous function to run the analysis."""
        engine = DeepSeekEngine(os.getenv("DEEPSEEK_API_KEY"))
        workflow = AnalysisTaggingWorkflow(engine)

        if tickers:
            ticker_list = [t.strip() for t in tickers.split(",")]
            logging.info(f"Analyzing companies: {', '.join(ticker_list)}")
            async for result in workflow.process_companies_by_tickers(
                ticker_list, callback=print_analysis_result
            ):
                pass
        elif tick_range:
            min_tick, max_tick = map(int, tick_range.split("-"))
            logging.info(f"Analyzing companies with tick range {min_tick}-{max_tick}")
            async for result in workflow.process_companies_by_tick_range(
                min_tick, max_tick, limit, callback=print_analysis_result
            ):
                pass
        else:
            logging.error("Either --tickers or --tick-range must be specified")

    if os.name == "nt":  # Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_analysis())


if __name__ == "__main__":
    research()
